import os
import uuid
import subprocess
import threading
import json
import shutil
import glob
import time
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, Optional, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from s3_uploader import upload_job_artifacts
from prompts import PROMPT_LIBRARY

load_dotenv()

# Constants
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "output"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

MAX_CONCURRENT_JOBS = int(os.environ.get("MAX_CONCURRENT_JOBS", "5"))
MAX_FILE_SIZE_MB = 500
JOB_RETENTION_SECONDS = 3600

job_queue = asyncio.Queue()
jobs: Dict[str, Dict] = {}
concurrency_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)

def get_timestamp():
    return datetime.now().strftime("%H:%M:%S")

# --- PERSISTENCE HELPERS ---
def save_job_state(job_id):
    """Saves the current job state to disk so it survives restarts."""
    if job_id not in jobs: return
    try:
        job_dir = os.path.join(OUTPUT_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)
        path = os.path.join(job_dir, "job_state.json")
        with open(path, 'w') as f:
            # Create a copy to avoid race conditions
            data = jobs[job_id].copy()
            json.dump(data, f)
    except Exception as e:
        print(f"⚠️ Failed to save job state: {e}")

def restore_job_state(job_id):
    """Restores job state from disk if missing in memory."""
    if job_id in jobs: return True
    path = os.path.join(OUTPUT_DIR, job_id, "job_state.json")
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                jobs[job_id] = json.load(f)
            print(f"♻️ Restored job {job_id} from disk.")
            return True
        except Exception as e:
            print(f"❌ Failed to restore job: {e}")
    return False

# --- DRIVE SYNC ---
def copy_to_gdrive(job_id, output_dir, data, base_name):
    drive_root = "/content/drive/MyDrive"
    if not os.path.exists(drive_root): return
    try:
        clips_root = os.path.join(drive_root, "CLIPS")
        os.makedirs(clips_root, exist_ok=True)
        project_folder = os.path.join(clips_root, base_name)
        os.makedirs(project_folder, exist_ok=True)
        
        shorts = data.get('shorts', [])
        summary_text = f"PROJECT: {base_name}\nDATE: {datetime.now()}\nSOURCE: {job_id}\n\n"
        
        for i, clip in enumerate(shorts):
            clip_filename = f"{base_name}_clip_{i+1}.mp4"
            src_path = os.path.join(output_dir, clip_filename)
            dst_path = os.path.join(project_folder, clip_filename)
            
            # Get Metadata
            title = clip.get('video_title_for_youtube_short', 'N/A')
            # Fallback logic for caption: Instagram -> TikTok -> YouTube -> N/A
            caption = clip.get('video_description_for_instagram') or \
                      clip.get('video_description_for_tiktok') or \
                      clip.get('video_description_for_youtube') or 'N/A'
            script = clip.get('script', 'N/A')
            
            if os.path.exists(src_path):
                shutil.copy2(src_path, dst_path)
                
                # Append detailed info to text file
                summary_text += f"========================================\n"
                summary_text += f"🎬 CLIP {i+1}\n"
                summary_text += f"========================================\n"
                summary_text += f"📁 FILE:    {clip_filename}\n"
                summary_text += f"📺 TITLE:   {title}\n"
                summary_text += f"📝 CAPTION: {caption}\n"
                summary_text += f"🗣️ SCRIPT:  {script}\n"
                summary_text += f"⏱️ TIME:    {clip.get('start')}s - {clip.get('end')}s\n\n"
        
        # Save the rich text file
        with open(os.path.join(project_folder, "clips_info.txt"), "w", encoding="utf-8") as f:
            f.write(summary_text)
            
        if job_id in jobs: 
            jobs[job_id]['logs'].append(f"[{get_timestamp()}] ✅ Synced to Drive (with Titles & Captions).")
            save_job_state(job_id) 
    except Exception as e:
        if job_id in jobs: 
            jobs[job_id]['logs'].append(f"[{get_timestamp()}] ❌ Drive Sync Error: {e}")
            save_job_state(job_id)

async def cleanup_jobs():
    while True:
        await asyncio.sleep(300)
        # Cleanup logic can be added here

async def process_queue():
    while True:
        try:
            job_id = await job_queue.get()
            await concurrency_semaphore.acquire()
            asyncio.create_task(run_job_wrapper(job_id))
        except Exception: await asyncio.sleep(1)

async def run_job_wrapper(job_id):
    try:
        job = jobs.get(job_id)
        if job: await run_job(job_id, job)
    finally:
        concurrency_semaphore.release()
        job_queue.task_done()

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(process_queue())
    asyncio.create_task(cleanup_jobs())
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/videos", StaticFiles(directory=OUTPUT_DIR), name="videos")

def enqueue_output(out, job_id):
    try:
        for line in iter(out.readline, b''):
            decoded = line.decode('utf-8').strip()
            if decoded:
                if job_id in jobs:
                    jobs[job_id]['logs'].append(f"[{get_timestamp()}] {decoded}")
                    # We don't save state on every log line to avoid IO thrashing, 
                    # but we rely on status changes to checkpoint.
    finally: out.close()

async def run_job(job_id, job_data):
    cmd = job_data['cmd']
    env = job_data['env']
    output_dir = job_data['output_dir']
    
    jobs[job_id]['status'] = 'processing'
    jobs[job_id]['logs'].append(f"[{get_timestamp()}] Executing: {' '.join(cmd)}")
    save_job_state(job_id) # Checkpoint
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, cwd=os.getcwd())
        t_log = threading.Thread(target=enqueue_output, args=(process.stdout, job_id))
        t_log.daemon = True
        t_log.start()
        
        while process.poll() is None:
            await asyncio.sleep(2)
            try:
                # --- REAL TIME FILE DETECTION START ---
                # Check for metadata
                json_files = glob.glob(os.path.join(output_dir, "*_metadata.json"))
                if json_files:
                    target_json = json_files[0]
                    if os.path.getsize(target_json) > 0:
                        with open(target_json, 'r') as f:
                            data = json.load(f)
                            
                        # Check for generated clips (Phase 2)
                        base_name = os.path.basename(target_json).replace('_metadata.json', '')
                        clips = data.get('shorts', [])
                        ready_clips = []
                        
                        for i, clip in enumerate(clips):
                             clip_filename = f"{base_name}_clip_{i+1}.mp4"
                             clip_path = os.path.join(output_dir, clip_filename)
                             if os.path.exists(clip_path) and os.path.getsize(clip_path) > 0:
                                 # Clone clip data to avoid modifying original
                                 new_clip = clip.copy()
                                 new_clip['video_url'] = f"/videos/{job_id}/{clip_filename}"
                                 ready_clips.append(new_clip)
                        
                        # If we found any ready clips, update result immediately
                        if ready_clips:
                             jobs[job_id]['result'] = {
                                 'clips': ready_clips, 
                                 'shorts': clips,
                                 'cost_analysis': data.get('cost_analysis')
                             }
                # --- REAL TIME FILE DETECTION END ---
            except Exception:
                pass # Ignore file read errors during processing
        
        if process.returncode == 0:
            if "--analyze-only" in cmd:
                jobs[job_id]['status'] = 'analyzed'
                jobs[job_id]['logs'].append(f"[{get_timestamp()}] Analysis Complete. Waiting for selection.")
                
                json_files = glob.glob(os.path.join(output_dir, "*_metadata.json"))
                if json_files:
                    with open(json_files[0], 'r') as f:
                        data = json.load(f)
                        jobs[job_id]['result'] = data
            else:
                jobs[job_id]['status'] = 'completed'
                jobs[job_id]['logs'].append(f"[{get_timestamp()}] Generation Complete.")
                
                # Final pass to ensure all clips are caught
                json_files = glob.glob(os.path.join(output_dir, "*_metadata.json"))
                if json_files:
                    with open(json_files[0], 'r') as f: data = json.load(f)
                    base_name = os.path.basename(json_files[0]).replace('_metadata.json', '')
                    
                    generated_clips = []
                    for i, clip in enumerate(data.get('shorts', [])):
                         clip_filename = f"{base_name}_clip_{i+1}.mp4"
                         if os.path.exists(os.path.join(output_dir, clip_filename)):
                             clip['video_url'] = f"/videos/{job_id}/{clip_filename}"
                             generated_clips.append(clip)
                    
                    jobs[job_id]['result'] = {'clips': generated_clips, 'cost_analysis': data.get('cost_analysis')}
                    loop = asyncio.get_event_loop()
                    loop.run_in_executor(None, copy_to_gdrive, job_id, output_dir, data, base_name)
        else:
            jobs[job_id]['status'] = 'failed'
        
        save_job_state(job_id) # Final Checkpoint
            
    except Exception as e:
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['logs'].append(f"[{get_timestamp()}] Error: {str(e)}")
        save_job_state(job_id)

@app.get("/api/config")
async def get_config():
    return {"has_gemini_key": bool(os.environ.get("GEMINI_API_KEY"))}

@app.get("/api/styles")
async def get_styles():
    return {"styles": list(PROMPT_LIBRARY.keys())}

@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    # Try to restore if missing (Backend Restart Recovery)
    if job_id not in jobs:
        restored = restore_job_state(job_id)
        if not restored:
            raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]

@app.post("/api/analyze")
async def analyze_endpoint(request: Request, file: Optional[UploadFile] = File(None), url: Optional[str] = Form(None), style: Optional[str] = Form("original")):
    header_key = request.headers.get("X-Gemini-Key")
    api_key = header_key if header_key and header_key != "MANAGED_BY_SERVER" else os.environ.get("GEMINI_API_KEY")
    if not api_key: raise HTTPException(status_code=400, detail="Missing API Key")

    if "application/json" in request.headers.get("content-type", ""):
        body = await request.json()
        url = body.get("url")
        style = body.get("style", "original")
    
    job_id = str(uuid.uuid4())
    job_output_dir = os.path.join(OUTPUT_DIR, job_id)
    os.makedirs(job_output_dir, exist_ok=True)
    
    cmd = ["python", "-u", "main.py", "--analyze-only", "--style", style]
    env = os.environ.copy()
    env["GEMINI_API_KEY"] = api_key
    
    if url:
        cmd.extend(["-u", url])
    else:
        input_path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        cmd.extend(["-i", input_path])

    cmd.extend(["-o", job_output_dir])

    jobs[job_id] = {
        'status': 'queued',
        'logs': [f"[{get_timestamp()}] Analysis Job queued."],
        'cmd': cmd,
        'env': env, # Env contains secrets, but we're only saving to local disk
        'output_dir': job_output_dir
    }
    
    save_job_state(job_id) # Initial Save
    await job_queue.put(job_id)
    return {"job_id": job_id, "status": "queued"}

class GenerateSelectionRequest(BaseModel):
    job_id: str
    selected_indices: List[int]

@app.post("/api/generate-selected")
async def generate_selected(req: GenerateSelectionRequest):
    # Try restore
    if req.job_id not in jobs:
        if not restore_job_state(req.job_id):
            raise HTTPException(status_code=404, detail="Job not found")
    
    original_job = jobs[req.job_id]
    base_cmd = [x for x in original_job['cmd'] if x != "--analyze-only"]
    indices_str = ",".join(map(str, req.selected_indices))
    new_cmd = base_cmd + ["--process-indices", indices_str]
    
    jobs[req.job_id]['cmd'] = new_cmd
    jobs[req.job_id]['status'] = 'queued'
    jobs[req.job_id]['logs'].append(f"[{get_timestamp()}] Generation queued for clips: {indices_str}")
    
    save_job_state(req.job_id) # Save new state
    await job_queue.put(req.job_id)
    return {"success": True, "status": "queued"}
