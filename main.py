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

        # Step 3: Select Clip
        print(f"\n--- Step 3: Selecting best clip ({min_length}-{max_length}s) ---")
        with open(transcript_path, 'r', encoding='utf-8') as f:
            full_transcript_data = json.load(f)
        
        segments = full_transcript_data['segments']
        selected_clip_info = select_best_window(segments, min_length, max_length, keywords)

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

        # Step 4: Extract the Selected Clip
        extracted_video_path = os.path.join(temp_dir, "extracted_clip.mp4")
        print(f"\n--- Step 4: Extracting video clip from {actual_input_file} ---")
        extract_clip(actual_input_file, clip_start, clip_end, extracted_video_path)

        # Step 5: Generate SRT for the Selected Clip
        srt_path = os.path.join(temp_dir, "clip_captions.srt")
        print(f"\n--- Step 5: Generating SRT captions for the clip ---")
        json_to_srt(transcript_path, srt_path, clip_start, clip_end)

        # Step 6: Format to 9:16 and Burn Captions using ffmpeg
        print(f"\n--- Step 6: Formatting to 9:16 and burning captions (using ffmpeg) ---")

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
    parser.add_argument('--keywords', default='highlights,interesting', help='Comma-separated keywords for automatic clip selection.')
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