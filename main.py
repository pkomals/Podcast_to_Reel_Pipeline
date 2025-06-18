import argparse
import os
import json
import shutil # For temporary file management
import time # For delay

# Import core functions from modules
from load_media import extract_audio
from transcribe import transcribe_audio
from select_clip import select_best_window
from extract_clip import extract_clip
from caps import json_to_srt # Assuming your SRT export script is named caps.py
from download_youtube import download_video # New import
from llm_keyword_suggester import get_llm_suggestions # New import

from moviepy.editor import VideoFileClip # To get video dimensions

def run_pipeline(input_source, output_file, keywords, whisper_model, min_length, max_length, is_youtube_url=False):
    # Create a temporary directory for intermediate files
    temp_dir = "temp_pipeline_files"
    os.makedirs(temp_dir, exist_ok=True)

    actual_input_file = input_source # Default to input_source if it's a local file

    try:
        if is_youtube_url:
            print(f"\n--- Step 0: Downloading video from YouTube URL: {input_source} ---")
            downloaded_video_path = os.path.join(temp_dir, "downloaded_youtube_video.mp4")
            actual_input_file = download_video(input_source, downloaded_video_path)
            if not actual_input_file:
                print("Failed to download YouTube video. Exiting.")
                return

        # Step 1: Extract Audio
        audio_path = os.path.join(temp_dir, "extracted_audio.wav")
        print(f"\n--- Step 1: Extracting audio from {actual_input_file} ---")
        extract_audio(actual_input_file, audio_path)

        # Step 2: Transcribe Audio
        transcript_path = os.path.join(temp_dir, "transcript.json")
        print(f"\n--- Step 2: Transcribing audio to {transcript_path} ---")
        transcribe_audio(audio_path, transcript_path, whisper_model)

        # Load the full transcript text for the LLM
        with open(transcript_path, 'r', encoding='utf-8') as f:
            full_transcript_data = json.load(f)
        full_transcript_text = " ".join([seg['text'] for seg in full_transcript_data['segments']])

        # Step 3: Get LLM Keyword Suggestions (New Step)
        final_keywords = []
        if full_transcript_text:
            print(f"\n--- Step 3: Getting LLM keyword suggestions ---")
            llm_suggestions = get_llm_suggestions(full_transcript_text)
            
            if llm_suggestions:
                print("\n--- LLM Suggested Content ---")
                print("Summary:")
                print(f"  {llm_suggestions['summary']}")
                print("\nSuggested Topics & Keywords:")
                all_suggested_keywords = []
                for i, topic in enumerate(llm_suggestions['key_topics']):
                    print(f"  {i+1}. {topic['theme']}: {\
                        ', '.join(topic['keywords'])}")
                    all_suggested_keywords.extend(topic['keywords'])
                
                # Store all suggested topics with their keywords for easier selection
                suggested_topics_map = {str(i + 1): topic for i, topic in enumerate(llm_suggestions['key_topics'])}

                print("\n----------------------------------")
                user_choice = input("Use suggested keywords? (y/N/custom_enter): ").lower().strip()
                
                if user_choice == 'y':
                    topic_selection_input = input("Enter topic numbers (e.g., 1,3), 'all', or 'none' to skip: ").lower().strip()
                    if topic_selection_input == 'all':
                        final_keywords = list(set(all_suggested_keywords)) # Use all unique keywords
                        print(f"Using all suggested keywords: {', '.join(final_keywords)}")
                    elif topic_selection_input == 'none' or not topic_selection_input:
                        print(f"Skipping suggested keywords. Using default keywords for clip selection: {', '.join(keywords)}")
                        final_keywords = keywords # Fallback to CLI provided keywords
                    else:
                        selected_topic_numbers = [num.strip() for num in topic_selection_input.split(',') if num.strip()]
                        selected_keywords = []
                        for num in selected_topic_numbers:
                            if num in suggested_topics_map:
                                selected_keywords.extend(suggested_topics_map[num]['keywords'])
                            else:
                                print(f"Warning: Topic number '{num}' not found. Skipping.")
                        
                        final_keywords = list(set(selected_keywords)) # Remove duplicates
                        if final_keywords:
                            print(f"Using selected suggested keywords: {', '.join(final_keywords)}")
                        else:
                            print(f"No valid topics selected or selected topics have no keywords. Using default keywords for clip selection: {', '.join(keywords)}")
                            final_keywords = keywords # Fallback if selection results in empty list
                elif user_choice == 'n' or user_choice == 'custom_enter':
                    custom_input = input("Enter your keywords (comma-separated): ").strip()
                    final_keywords = [kw.strip() for kw in custom_input.split(',') if kw.strip()]
                    print(f"Using custom keywords: {', '.join(final_keywords)}")
                else:
                    print(f"Invalid choice. Using default keywords for clip selection: {', '.join(keywords)}")
                    final_keywords = keywords # Fallback to CLI provided keywords
            else:
                print("LLM suggestions failed or not available. Using default keywords from CLI.")
                final_keywords = keywords # Fallback to CLI provided keywords
        else:
            print("Transcript is empty. Using default keywords for clip selection.")
            final_keywords = keywords

        # Step 4: Select Clip (using final_keywords)
        print(f"\n--- Step 4: Selecting best clip ({min_length}-{max_length}s) ---")
        
        segments = full_transcript_data['segments'] # Re-using full_transcript_data from above
        selected_clip_info = select_best_window(segments, min_length, max_length, final_keywords)

        if not selected_clip_info:
            print("No suitable clip found for the given criteria. Exiting.")
            return

        clip_start = selected_clip_info['start']
        clip_end = selected_clip_info['end']
        print(f"Selected clip from {clip_start:.2f}s to {clip_end:.2f}s")
        
        # Save selected clip info (optional, but good for debugging/re-running)
        selected_clip_info_path = os.path.join(temp_dir, "selected_clip_info.json")
        with open(selected_clip_info_path, 'w', encoding='utf-8') as f:
            json.dump(selected_clip_info, f, indent=2)

        # Step 5: Extract the Selected Clip
        extracted_video_path = os.path.join(temp_dir, "extracted_clip.mp4")
        print(f"\n--- Step 5: Extracting video clip from {actual_input_file} ---")
        extract_clip(actual_input_file, clip_start, clip_end, extracted_video_path)

        # Step 6: Generate SRT for the Selected Clip
        srt_path = os.path.join(temp_dir, "clip_captions.srt")
        print(f"\n--- Step 6: Generating SRT captions for the clip ---")
        json_to_srt(transcript_path, srt_path, clip_start, clip_end)

        # Step 7: Format to 9:16 and Burn Captions using ffmpeg
        print(f"\n--- Step 7: Formatting to 9:16 and burning captions (using ffmpeg) ---")

        # Get original video dimensions of the extracted clip for calculation
        video_clip_info = VideoFileClip(extracted_video_path)
        original_width = video_clip_info.w
        original_height = video_clip_info.h
        video_clip_info.close()

        # Define target 9:16 resolution (e.g., 1080x1920) for consistent output
        target_width = 1080
        target_height = 1920

        # Calculate scaling to fit completely within 9:16 without cropping (Pillarbox)
        # We need the minimum of (target_width/original_width) and (target_height/original_height)
        # to ensure the entire video fits within the target frame.
        scale_ratio = min(target_width / original_width, target_height / original_height)
        
        scaled_width = int(original_width * scale_ratio)
        scaled_height = int(original_height * scale_ratio)
        
        # Ensure dimensions are even for FFmpeg
        scaled_width = scaled_width if scaled_width % 2 == 0 else scaled_width - 1
        scaled_height = scaled_height if scaled_height % 2 == 0 else scaled_height - 1

        # Calculate padding to center the scaled video
        x_pad = (target_width - scaled_width) // 2
        y_pad = (target_height - scaled_height) // 2
        
        # FFmpeg filter to scale (no cropping) and then pad to 9:16 (pillarbox)
        video_filters = (
            f"scale={scaled_width}:{scaled_height},"  # Scale to fit without cropping
            f"pad={target_width}:{target_height}:{x_pad}:{y_pad}:black" # Pad with black bars
        )

        # Add subtitles filter (using forward slashes for path for ffmpeg compatibility)
        # Fontsize is manually set by user to 12
        subtitles_filter = (
            f"subtitles='{srt_path.replace(os.sep, '/')}':"
            f"force_style='Fontname=Arial,Fontsize=12,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=0'"
        )

        # Combine all video filters
        vf_string = f"{video_filters},{subtitles_filter}"
        
        ffmpeg_cmd = (
            f"ffmpeg -i \"{extracted_video_path}\" " # Quote path to handle spaces
            f"-vf \"{vf_string}\" " # Quote filter string
            f"-c:a copy "
            f"-y " # Overwrite output file without asking
            f"\"{output_file}\"" # Quote output path to handle spaces
        )
        print("\n------------------------------------------------------------------------------------------------------------------------")
        print("\n--- FINAL STEP: Copy and paste this command into your terminal to generate the final video with captions and 9:16 format: ---")
        print(ffmpeg_cmd)
        print("\n------------------------------------------------------------------------------------------------------------------------")
        
    finally:
        # Clean up temporary files removed as per user request to keep them
        pass # No cleanup will be performed now

def main():
    parser = argparse.ArgumentParser(description="Full pipeline to create a CPU-friendly short video reel from a long-form podcast.")
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--input', help='Path to input long-form MP4 or MP3 file.')
    input_group.add_argument('--youtube-url', help='YouTube video URL to download.')

    parser.add_argument('--output', required=True, help='Path for the final output short MP4 video (e.g., output/reel.mp4).')
    # The --keywords argument will now be used as default/fallback if LLM suggestions are not chosen
    parser.add_argument('--keywords', default='highlights,interesting', help='Comma-separated keywords for automatic clip selection (used as default or fallback).')
    parser.add_argument('--whisper-model', default='base', choices=['tiny', 'base', 'small'], help='Whisper model size (default: base). For CPU, base or small recommended.')
    parser.add_argument('--min-length', type=float, default=30, help='Minimum clip length in seconds (default: 30).')
    parser.add_argument('--max-length', type=float, default=60, help='Maximum clip length in seconds (default: 60).')
    
    args = parser.parse_args()


    if args.youtube_url:
        run_pipeline(args.youtube_url, args.output, 
                     [kw.strip() for kw in args.keywords.split(',') if kw.strip()],
                     args.whisper_model, args.min_length, args.max_length, is_youtube_url=True)
    else:
        run_pipeline(args.input, args.output, 
                     [kw.strip() for kw in args.keywords.split(',') if kw.strip()],
                     args.whisper_model, args.min_length, args.max_length, is_youtube_url=False)

if __name__ == "__main__":
    main() 