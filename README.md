# Podcast_to_Reel_Pipeline

---

## 🚀 Overview

**Podcast to Reel** is LLM powered modular, CPU-friendly pipeline that transforms long podcast videos (MP4/MP3 or YouTube) into 30–60 second vertical reels, ready for Instagram Reels and YouTube Shorts. It features local Whisper transcription, LLM-powered keyword suggestion, a simple interactive web UI, and robust captioning—all optimized for easy use and high-quality output.

---

## ✨ Features

- **Modular, CPU-friendly pipeline** (no GPU required)
- **Local Whisper transcription** (no API cost)
- **LLM-powered keyword suggestion** (OpenAI GPT-3.5)
- **Interactive web interface** (Bootstrap, FastAPI)
- **YouTube video download support**
- **Burned-in captions** (ffmpeg, SRT)
- **9:16 vertical output** (pillarbox, no cropping)
- **Command-line and web UI modes**
- **Flexible, extensible, and production-ready**

---


## ⚡ Quickstart

### Prerequisites

- Python 3.8+
- [ffmpeg](https://ffmpeg.org/) installed and in your system PATH
- OpenAI API key (for LLM keyword suggestion)

### Installation

```bash
git clone https://github.com/yourusername/podcast-to-reel.git
cd podcast-to-reel
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root with your OpenAI API key:
```
OPENAI_API_KEY="YOUR API KEY HERE"
```

---

## 🌐 Run the Web App

```bash
uvicorn app:app --reload
```

Visit [http://localhost:8000](http://localhost:8000) in your browser.

---

## 🖥️ Run from the Command Line

For a local file:
```bash
python main.py --input path/to/yourfile.mp4 --output output/reel.mp4
```

For a YouTube video:
```bash
python main.py --youtube-url "https://youtube.com/..." --output output/reel.mp4
```

You will be prompted in the terminal for keyword/topic selection.

---

## 📝 Usage

### Web UI

1. **Paste a YouTube URL** (local file can be selected too, may be in later updates).
2. **Choose Whisper model and clip length.**
3. **Review LLM summary and suggested topics/keywords.**
4. **Select topics or enter custom keywords.**
5. **Download your ready-to-post vertical reel!**
6. **Create new reel by selecting different topics from the same podcast or Start with new podcast.**

### CLI

- Use the `--youtube-url` flag, and follow the prompts for keyword selection.

---

## ⚙️ Project Structure

| File/Folder              | Purpose                                                      |
|--------------------------|-------------------------------------------------------------|
| `app.py`                 | FastAPI web server (main entry for web UI)                  |
| `main.py`                | Command-line pipeline entry                                 |
| `load_media.py`          | Audio extraction from video                                 |
| `transcribe.py`          | Whisper transcription (local, CPU)                          |
| `llm_keyword_suggester.py` | LLM-powered keyword suggestion (OpenAI GPT-3.5)           |
| `select_clip.py`         | Clip selection logic (keywords, sentiment)                  |
| `extract_clip.py`        | Clip extraction from video/audio                            |
| `caps.py`                | SRT caption generation                                      |
| `download_youtube.py`    | YouTube video download support                              |
| `templates/`             | Bootstrap-styled HTML templates for web UI                  |
| `output/`                | Output reels and intermediate files (gitignored)            |
| `temp_pipeline_files/`   | Temporary pipeline files (gitignored)                       |

---

## 🛠️ Troubleshooting

- **Pydantic/FastAPI ImportError:**  
  Run `pip install 'pydantic<2.0.0'`
- **ffmpeg not found:**  
  Install [ffmpeg](https://ffmpeg.org/download.html) and add it to your system PATH.
- **OpenAI API key error:**  
  Make sure your `.env` file is present and correct.

---

## 📈 Example Output

- Example output reels are saved in the `output/` directory, e.g.:
  - `output/reel_1aa67737.mp4`
  - `output/final_reel.mp4`
- Each reel is a 9:16 vertical video with burned-in captions, ready for upload.

---

## 📋 License

MIT License

---

## Credits

- [OpenAI Whisper]: For accurate, local speech-to-text transcription of podcast audio (no API calls needed).
- [FastAPI]: To build the backend web server with high performance and minimal boilerplate.
- [MoviePy]: For programmatically editing videos, merging captions, and preparing clips.
- [yt-dlp]: A fast and reliable tool to download YouTube videos directly within the app.
- [Bootstrap]: For building a clean and responsive user interface with minimal effort.

---

## 🚧 In Progress

- [ ] Add support for open-source LLMs
- [ ] Multi-language support
- [ ] Suggest trending #tags
- [ ] Docker container for easy deployment

