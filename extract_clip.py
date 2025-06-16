import argparse
import os
from moviepy.editor import VideoFileClip, AudioFileClip

def extract_clip(input_path, start, end, output_path):
    ext = os.path.splitext(input_path)[1].lower()
    print(f"Extracting from {start}s to {end}s...")
    if ext == '.mp4':
        video = VideoFileClip(input_path)
        duration = video.duration
        if end > duration:
            print(f"Warning: end time {end}s exceeds video duration {duration}s. Adjusting end time.")
            end = duration - 0.1 if duration - 0.1 > start else duration
        subclip = video.subclip(start, end)
        subclip.write_videofile(output_path, codec='libx264', audio_codec='aac')
        subclip.close()
        video.close()
    elif ext == '.mp3':
        audio = AudioFileClip(input_path)
        duration = audio.duration
        if end > duration:
            print(f"Warning: end time {end}s exceeds audio duration {duration}s. Adjusting end time.")
            end = duration - 0.1 if duration - 0.1 > start else duration
        subclip = audio.subclip(start, end)
        subclip.write_audiofile(output_path)
        subclip.close()
        audio.close()
    else:
        raise ValueError("Unsupported file type. Please provide an MP4 or MP3 file.")
    print(f"Clip saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Extract a clip from MP4/MP3 using start/end times.")
    parser.add_argument('--input', required=True, help='Path to input MP4 or MP3 file')
    parser.add_argument('--start', type=float, required=True, help='Start time in seconds')
    parser.add_argument('--end', type=float, required=True, help='End time in seconds')
    parser.add_argument('--output', required=True, help='Path to output MP4 file')
    args = parser.parse_args()
    extract_clip(args.input, args.start, args.end, args.output)

if __name__ == "__main__":
    main() 