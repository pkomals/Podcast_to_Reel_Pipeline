import argparse
import json
from textblob import TextBlob
import re

def score_segment(text, keywords):
    # Convert text to lowercase for case-insensitive matching
    lower_text = text.lower()
    
    keyword_base_score = 0 # Will be a very large number if any keyword is found
    keyword_occurrence_count = 0 # Counts total occurrences of keywords

    if keywords:
        has_any_keyword = False
        for kw in keywords:
            if kw.lower() in lower_text:
                has_any_keyword = True
                keyword_occurrence_count += lower_text.count(kw.lower()) # Count occurrences
        if has_any_keyword:
            keyword_base_score = 1_000_000 # Give a huge advantage if any keyword is present
    
    # Sentiment score: use polarity (range -1 to 1)
    sentiment_polarity = TextBlob(text).sentiment.polarity
    
    # Combine scores: prioritize keywords heavily. If no keywords, rely solely on sentiment.
    if keywords and keyword_base_score > 0:
        # If keywords were provided and found, prioritize them with a massive base score
        return keyword_base_score + (keyword_occurrence_count * 100) + sentiment_polarity
    elif keywords and keyword_base_score == 0: # Keywords were provided but not found in this segment
        return sentiment_polarity # In this case, sentiment is a very minor factor (will be outscored by any keyword hit)
    else:
        # If no keywords were provided in the arguments, sentiment is the sole factor
        return sentiment_polarity

def select_best_window(segments, min_length, max_length, keywords):
    best_score = float('-inf')
    best_window = None
    n = len(segments)
    # Precompute segment scores
    seg_scores = [score_segment(seg['text'], keywords) for seg in segments]
    # Try all possible windows
    for i in range(n):
        start_time = segments[i]['start']
        window_score = 0
        window_text = []
        for j in range(i, n):
            end_time = segments[j]['end']
            duration = end_time - start_time
            if duration > max_length:
                break
            window_score += seg_scores[j]
            window_text.append(segments[j]['text'])
            if min_length <= duration <= max_length:
                if window_score > best_score:
                    best_score = window_score
                    best_window = {
                        'start': start_time,
                        'end': end_time,
                        'text': ' '.join(window_text)
                    }
    return best_window

def main():
    parser = argparse.ArgumentParser(description="Select best 30–60s clip from transcript based on keywords and sentiment.")
    parser.add_argument('--transcript', required=True, help='Path to transcript JSON')
    parser.add_argument('--output', required=True, help='Path to output JSON with selected clip info')
    parser.add_argument('--keywords', default='', help='Comma-separated keywords (e.g., "AI, future, technology")')
    parser.add_argument('--min-length', type=float, default=30, help='Minimum clip length in seconds (default: 30)')
    parser.add_argument('--max-length', type=float, default=60, help='Maximum clip length in seconds (default: 60)')
    args = parser.parse_args()

    keywords = [kw.strip() for kw in args.keywords.split(',') if kw.strip()]
    with open(args.transcript, 'r', encoding='utf-8') as f:
        data = json.load(f)
    segments = data['segments']
    best = select_best_window(segments, args.min_length, args.max_length, keywords)
    if best:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(best, f, ensure_ascii=False, indent=2)
        print(f"Best clip: {best['start']}s to {best['end']}s. Saved to {args.output}")
    else:
        print("No suitable clip found.")

if __name__ == "__main__":
    main() 