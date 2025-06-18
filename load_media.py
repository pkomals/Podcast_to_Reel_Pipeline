import argparse
import os
from moviepy.editor import VideoFileClip, AudioFileClip


def extract_audio(input_path, output_path):
    ext = os.path.splitext(input_path)[1].lower()
    if ext == '.mp4':
        print(f"Extracting audio from video: {input_path}")
        video = VideoFileClip(input_path)
        audio = video.audio
        audio.write_audiofile(output_path, codec='pcm_s16le')
        audio.close()
        video.close()
    elif ext == '.mp3':
        print(f"Converting MP3 to WAV: {input_path}")
        audio = AudioFileClip(input_path)
        audio.write_audiofile(output_path, codec='pcm_s16le')
        audio.close()
    else:
        raise ValueError("Unsupported file type. Please provide an MP4 or MP3 file.")
    print(f"Audio saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Extract audio from MP4/MP3 and save as WAV.")
    parser.add_argument('--input', required=True, help='Path to input MP4 or MP3 file')
    parser.add_argument('--output', required=True, help='Path to output WAV file')
    args = parser.parse_args()
    extract_audio(args.input, args.output)

if __name__ == "__main__":
    main() 