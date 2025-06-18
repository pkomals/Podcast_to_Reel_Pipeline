import yt_dlp
import argparse
import os

def download_video(youtube_url, output_path):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path, # Output template, will include .mp4 extension
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }

    print(f"Downloading video from {youtube_url} to {output_path}...")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(youtube_url, download=True)
        # yt-dlp automatically adds the extension based on format, so we need to get the final path
        final_downloaded_path = ydl.prepare_filename(info_dict)
        print(f"Download complete: {final_downloaded_path}")
        return final_downloaded_path

def main():
    parser = argparse.ArgumentParser(description="Download a YouTube video.")
    parser.add_argument('--url', required=True, help='YouTube video URL.')
    parser.add_argument('--output', required=True, help='Output path for the downloaded video (e.g., video.mp4).')
    args = parser.parse_args()

    download_video(args.url, args.output)

if __name__ == "__main__":
    main() 