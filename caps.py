import json
import argparse

def json_to_srt(transcript_json, srt_path, start=0, end=None):
    with open(transcript_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    segments = data['segments']
    with open(srt_path, 'w', encoding='utf-8') as f:
        idx = 1
        for seg in segments:
            if seg['end'] < start or (end is not None and seg['start'] > end):
                continue
            s = max(seg['start'], start) - start
            e = min(seg['end'], end) - start if end else seg['end'] - start
            def to_srt_time(t):
                h = int(t // 3600)
                m = int((t % 3600) // 60)
                s_ = int(t % 60)
                ms = int((t - int(t)) * 1000)
                return f'{h:02}:{m:02}:{s_:02},{ms:03}'
            f.write(f"{idx}\n{to_srt_time(s)} --> {to_srt_time(e)}\n{seg['text'].strip()}\n\n")
            idx += 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Export SRT from transcript JSON.')
    parser.add_argument('--transcript', required=True, help='Path to transcript JSON')
    parser.add_argument('--srt', required=True, help='Output SRT file')
    parser.add_argument('--start', type=float, default=0, help='Clip start (seconds)')
    parser.add_argument('--end', type=float, help='Clip end (seconds)')
    args = parser.parse_args()
    json_to_srt(args.transcript, args.srt, args.start, args.end)
