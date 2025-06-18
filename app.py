from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import os
import shutil
import uuid
from typing import Optional
import json
import subprocess

# Import your pipeline function and LLM suggester
from main import run_pipeline
from llm_keyword_suggester import get_llm_suggestions

app = FastAPI()

# Allow CORS for local testing (optional, safe for dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/start", response_class=HTMLResponse)
async def start_process(
    request: Request,
    youtube_url: str = Form(...),
    whisper_model: str = Form("base"),
    min_length: float = Form(30),
    max_length: float = Form(60)
):
    # Validate input
    if not youtube_url:
        return templates.TemplateResponse("index.html", {"request": request, "error": "Provide a YouTube URL."})

    from load_media import extract_audio
    from transcribe import transcribe_audio
    from download_youtube import download_video
    import json
    from llm_keyword_suggester import get_llm_suggestions

    temp_dir = "temp_pipeline_files"
    os.makedirs(temp_dir, exist_ok=True)
    # Download the YouTube video
    downloaded_video_path = os.path.join(temp_dir, "downloaded_youtube_video.mp4")
    actual_input_file = download_video(youtube_url, downloaded_video_path)
    if not actual_input_file:
        return templates.TemplateResponse("index.html", {"request": request, "error": "Failed to download YouTube video."})
    audio_path = os.path.join(temp_dir, "extracted_audio.wav")
    transcript_path = os.path.join(temp_dir, "transcript.json")

    try:
        extract_audio(actual_input_file, audio_path)
        transcribe_audio(audio_path, transcript_path, whisper_model)
        with open(transcript_path, 'r', encoding='utf-8') as f:
            full_transcript_data = json.load(f)
        full_transcript_text = " ".join([seg['text'] for seg in full_transcript_data['segments']])
        llm_suggestions = get_llm_suggestions(full_transcript_text)
    except Exception as e:
        return templates.TemplateResponse("index.html", {"request": request, "error": f"Error: {str(e)}"})

    # Render a new template for topic/keyword selection
    return templates.TemplateResponse(
        "select_keywords.html",
        {
            "request": request,
            "llm_suggestions": llm_suggestions,
            "input_path": None,
            "youtube_url": youtube_url,
            "whisper_model": whisper_model,
            "min_length": min_length,
            "max_length": max_length
        }
    )

@app.post("/process")
async def process(
    file: Optional[UploadFile] = File(None),
    youtube_url: Optional[str] = Form(None),
    keywords: str = Form(""),
    whisper_model: str = Form("base"),
    min_length: float = Form(30),
    max_length: float = Form(60)
):
    # Validate input
    if not file and not youtube_url:
        return JSONResponse(status_code=400, content={"error": "Provide either a file or a YouTube URL."})
    if file and youtube_url:
        return JSONResponse(status_code=400, content={"error": "Provide only one input: file or YouTube URL, not both."})

    # Generate a unique output filename
    output_filename = f"reel_{uuid.uuid4().hex[:8]}.mp4"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    # Save uploaded file if present
    input_path = None
    if file:
        input_path = os.path.join(OUTPUT_DIR, f"input_{uuid.uuid4().hex[:8]}_{file.filename}")
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    # Run the pipeline (blocking call)
    try:
        run_pipeline(
            input_source=youtube_url if youtube_url else input_path,
            output_file=output_path,
            keywords=[kw.strip() for kw in keywords.split(',') if kw.strip()] if keywords else [],
            whisper_model=whisper_model,
            min_length=min_length,
            max_length=max_length,
            is_youtube_url=bool(youtube_url)
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

    # Return download link
    return {"status": "success", "download_url": f"/download/{output_filename}"}

@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "File not found."})
    return FileResponse(file_path, media_type="video/mp4", filename=filename)

@app.post("/finalize", response_class=HTMLResponse)
async def finalize(
    request: Request,
    input_path: Optional[str] = Form(None),
    youtube_url: Optional[str] = Form(None),
    whisper_model: str = Form("base"),
    min_length: float = Form(30),
    max_length: float = Form(60),
    topic_idx: Optional[list] = Form(None),
    custom_keywords: str = Form("")
):
    # Re-run LLM to get the same suggestions (for topic mapping)
    from load_media import extract_audio
    from transcribe import transcribe_audio
    import json
    temp_dir = "temp_pipeline_files"
    transcript_path = os.path.join(temp_dir, "transcript.json")
    with open(transcript_path, 'r', encoding='utf-8') as f:
        full_transcript_data = json.load(f)
    full_transcript_text = " ".join([seg['text'] for seg in full_transcript_data['segments']])
    from llm_keyword_suggester import get_llm_suggestions
    llm_suggestions = get_llm_suggestions(full_transcript_text)

    # Determine final keywords
    if custom_keywords.strip():
        final_keywords = [kw.strip() for kw in custom_keywords.split(',') if kw.strip()]
        selected_topics = []
    else:
        # topic_idx can be a single string or a list
        if isinstance(topic_idx, str):
            topic_idx = [topic_idx]
        selected_topics = [llm_suggestions['key_topics'][int(idx)] for idx in topic_idx] if topic_idx else []
        final_keywords = list({kw for topic in selected_topics for kw in topic['keywords']})

    # Generate a unique output filename
    output_filename = f"reel_{uuid.uuid4().hex[:8]}.mp4"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    # Run the rest of the pipeline
    from select_clip import select_best_window
    from extract_clip import extract_clip
    from caps import json_to_srt
    from moviepy.editor import VideoFileClip

    min_length = float(min_length)
    max_length = float(max_length)
    # For testing, use the existing downloaded video file
    actual_input_file = os.path.join("temp_pipeline_files", "downloaded_youtube_video.mp4")
    segments = full_transcript_data['segments']
    selected_clip_info = select_best_window(segments, min_length, max_length, final_keywords)
    if not selected_clip_info:
        return templates.TemplateResponse("select_keywords.html", {
            "request": request,
            "llm_suggestions": llm_suggestions,
            "input_path": input_path,
            "youtube_url": youtube_url,
            "keywords": ','.join(final_keywords),
            "whisper_model": whisper_model,
            "min_length": min_length,
            "max_length": max_length,
            "error": "No suitable clip found for the selected keywords."
        })
    clip_start = selected_clip_info['start']
    clip_end = selected_clip_info['end']
    extracted_video_path = os.path.join(temp_dir, "extracted_clip.mp4")
    extract_clip(actual_input_file, clip_start, clip_end, extracted_video_path)
    srt_path = os.path.join(temp_dir, "clip_captions.srt")
    json_to_srt(transcript_path, srt_path, clip_start, clip_end)
    # Get video dimensions
    video_clip_info = VideoFileClip(extracted_video_path)
    original_width = video_clip_info.w
    original_height = video_clip_info.h
    video_clip_info.close()
    target_width = 1080
    target_height = 1920
    scale_ratio = min(target_width / original_width, target_height / original_height)
    scaled_width = int(original_width * scale_ratio)
    scaled_height = int(original_height * scale_ratio)
    scaled_width = scaled_width if scaled_width % 2 == 0 else scaled_width - 1
    scaled_height = scaled_height if scaled_height % 2 == 0 else scaled_height - 1
    x_pad = (target_width - scaled_width) // 2
    y_pad = (target_height - scaled_height) // 2
    video_filters = (
        f"scale={scaled_width}:{scaled_height},"
        f"pad={target_width}:{target_height}:{x_pad}:{y_pad}:black"
    )
    subtitles_filter = (
        f"subtitles='{srt_path.replace(os.sep, '/')}':"
        f"force_style='Fontname=Arial,Fontsize=12,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=0'"
    )
    vf_string = f"{video_filters},{subtitles_filter}"

    # Build ffmpeg command as a list of arguments
    ffmpeg_args = [
        "ffmpeg", "-i", extracted_video_path,
        "-vf", vf_string,
        "-c:a", "copy",
        "-y",
        output_path
    ]
    ffmpeg_cmd = ' '.join(ffmpeg_args)
    ffmpeg_error = None
    try:
        subprocess.run(ffmpeg_args, check=True)
    except subprocess.CalledProcessError as e:
        ffmpeg_error = str(e)

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "ffmpeg_cmd": ffmpeg_cmd,
            "download_url": f"/download/{output_filename}" if not ffmpeg_error else None,
            "selected_keywords": ', '.join(final_keywords),
            "clip_start": clip_start,
            "clip_end": clip_end,
            "error": ffmpeg_error,
            "clear_success": False,
            "youtube_url": youtube_url,
            "whisper_model": whisper_model,
            "min_length": min_length,
            "max_length": max_length
        }
    )

@app.post("/select_keywords", response_class=HTMLResponse)
async def select_keywords(
    request: Request,
    youtube_url: str = Form(...),
    whisper_model: str = Form("base"),
    min_length: float = Form(30),
    max_length: float = Form(60)
):
    import json
    from llm_keyword_suggester import get_llm_suggestions
    transcript_path = os.path.join("temp_pipeline_files", "transcript.json")
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            full_transcript_data = json.load(f)
        full_transcript_text = " ".join([seg['text'] for seg in full_transcript_data['segments']])
        llm_suggestions = get_llm_suggestions(full_transcript_text)
    except Exception as e:
        return templates.TemplateResponse("index.html", {"request": request, "error": f"Error: {str(e)}"})

    return templates.TemplateResponse(
        "select_keywords.html",
        {
            "request": request,
            "llm_suggestions": llm_suggestions,
            "input_path": None,
            "youtube_url": youtube_url,
            "whisper_model": whisper_model,
            "min_length": min_length,
            "max_length": max_length
        }
    )

@app.post("/clear_temp", response_class=HTMLResponse)
async def clear_temp(request: Request):
    import os, shutil
    temp_dir = os.path.join(os.getcwd(), "temp_pipeline_files")
    clear_success = False
    try:
        if os.path.exists(temp_dir):
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            clear_success = True
    except Exception as e:
        clear_success = False
    # Render a minimal result page with the clear_success message
    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "ffmpeg_cmd": None,
            "download_url": None,
            "selected_keywords": "",
            "clip_start": 0,
            "clip_end": 0,
            "error": None,
            "clear_success": clear_success,
            "youtube_url": "",
            "whisper_model": "",
            "min_length": "",
            "max_length": ""
        }
    ) 