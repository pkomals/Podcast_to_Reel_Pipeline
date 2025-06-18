import argparse
import whisper
import json
import os

def transcribe_audio(input_path, output_path, model_size='base', language='en'):
    print(f"Loading Whisper model: {model_size} (CPU mode)")
    model = whisper.load_model(model_size, device="cpu")
    print(f"Transcribing: {input_path} (Language: {language})")
    result = model.transcribe(input_path, verbose=True, language=language)
    # Save the full result (includes 'segments' with timestamps)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Transcript saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Transcribe WAV audio using OpenAI Whisper and output JSON.")
    parser.add_argument('--input', required=True, help='Path to input WAV file')
    parser.add_argument('--output', required=True, help='Path to output JSON file')
    parser.add_argument('--model', default='base', choices=['tiny', 'base', 'small'], help='Whisper model size (default: base)')
    parser.add_argument('--language', default='en', help='Language to transcribe in (e.g., "en" for English, "es" for Spanish). Defaults to "en".')
    args = parser.parse_args()
    transcribe_audio(args.input, args.output, args.model, args.language)

if __name__ == "__main__":
    main() 