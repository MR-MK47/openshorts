import time
import cv2
import scenedetect
import subprocess
import argparse
import re
import sys
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector
from ultralytics import YOLO
import torch
import os
import numpy as np
from tqdm import tqdm
import yt_dlp
import mediapipe as mp
from google import genai
from dotenv import load_dotenv
import json

# --- IMPORTS ---
try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None
    print("❌ youtube-transcript-api not found. Falling back to Whisper.")

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module='google.protobuf')

# Load environment variables
load_dotenv()

# --- Constants ---
ASPECT_RATIO = 9 / 16

# --- IMPORTS ---
from prompts import PROMPT_LIBRARY


# Load models
model = YOLO('yolov8n.pt')
mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)

class SmoothedCameraman:
    def __init__(self, output_width, output_height, video_width, video_height):
        self.output_width = output_width
        self.output_height = output_height
        self.video_width = video_width
        self.video_height = video_height
        self.current_center_x = video_width / 2
        self.target_center_x = video_width / 2
        self.crop_height = video_height
        self.crop_width = int(self.crop_height * ASPECT_RATIO)
        if self.crop_width > video_width:
             self.crop_width = video_width
             self.crop_height = int(self.crop_width / ASPECT_RATIO)
        self.safe_zone_radius = self.crop_width * 0.25

    def update_target(self, face_box):
        if face_box:
            x, y, w, h = face_box
            self.target_center_x = x + w / 2
    
    def get_crop_box(self, force_snap=False):
        if force_snap:
            self.current_center_x = self.target_center_x
        else:
            diff = self.target_center_x - self.current_center_x
            if abs(diff) > self.safe_zone_radius:
                direction = 1 if diff > 0 else -1
                speed = 15.0 if abs(diff) > self.crop_width * 0.5 else 3.0
                self.current_center_x += direction * speed
                new_diff = self.target_center_x - self.current_center_x
                if (direction == 1 and new_diff < 0) or (direction == -1 and new_diff > 0):
                    self.current_center_x = self.target_center_x
        
        half_crop = self.crop_width / 2
        if self.current_center_x - half_crop < 0:
            self.current_center_x = half_crop
        if self.current_center_x + half_crop > self.video_width:
            self.current_center_x = self.video_width - half_crop
            
        x1 = int(self.current_center_x - half_crop)
        x2 = int(self.current_center_x + half_crop)
        x1 = max(0, x1)
        x2 = min(self.video_width, x2)
        return x1, 0, x2, self.video_height

class SpeakerTracker:
    def __init__(self, stabilization_frames=15, cooldown_frames=30):
        self.active_speaker_id = None
        self.speaker_scores = {}
        self.last_seen = {}
        self.locked_counter = 0
        self.stabilization_threshold = stabilization_frames
        self.switch_cooldown = cooldown_frames
        self.last_switch_frame = -1000
        self.next_id = 0
        self.known_faces = []

    def get_target(self, face_candidates, frame_number, width):
        current_candidates = []
        for face in face_candidates:
            x, y, w, h = face['box']
            center_x = x + w / 2
            best_match_id = -1
            min_dist = width * 0.15
            for kf in self.known_faces:
                if frame_number - kf['last_frame'] > 30: continue
                dist = abs(center_x - kf['center'])
                if dist < min_dist:
                    min_dist = dist
                    best_match_id = kf['id']
            if best_match_id == -1:
                best_match_id = self.next_id
                self.next_id += 1
            self.known_faces = [kf for kf in self.known_faces if kf['id'] != best_match_id]
            self.known_faces.append({'id': best_match_id, 'center': center_x, 'last_frame': frame_number})
            current_candidates.append({'id': best_match_id, 'box': face['box'], 'score': face['score']})

        for pid in list(self.speaker_scores.keys()):
             self.speaker_scores[pid] *= 0.85
             if self.speaker_scores[pid] < 0.1: del self.speaker_scores[pid]

        for cand in current_candidates:
            pid = cand['id']
            raw_score = cand['score'] / (width * width * 0.05)
            self.speaker_scores[pid] = self.speaker_scores.get(pid, 0) + raw_score

        if not current_candidates: return None
        best_candidate = None
        max_score = -1
        for cand in current_candidates:
            pid = cand['id']
            total_score = self.speaker_scores.get(pid, 0)
            if pid == self.active_speaker_id: total_score *= 3.0
            if total_score > max_score:
                max_score = total_score
                best_candidate = cand

        if best_candidate:
            target_id = best_candidate['id']
            if target_id == self.active_speaker_id:
                self.locked_counter += 1
                return best_candidate['box']
            if frame_number - self.last_switch_frame < self.switch_cooldown:
                old_cand = next((c for c in current_candidates if c['id'] == self.active_speaker_id), None)
                if old_cand: return old_cand['box']
            self.active_speaker_id = target_id
            self.last_switch_frame = frame_number
            self.locked_counter = 0
            return best_candidate['box']
        return None

def detect_face_candidates(frame):
    height, width, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_detection.process(rgb_frame)
    candidates = []
    if not results.detections: return []
    for detection in results.detections:
        bboxC = detection.location_data.relative_bounding_box
        x = int(bboxC.xmin * width)
        y = int(bboxC.ymin * height)
        w = int(bboxC.width * width)
        h = int(bboxC.height * height)
        candidates.append({'box': [x, y, w, h], 'score': w * h})
    return candidates

def detect_person_yolo(frame):
    results = model(frame, verbose=False, classes=[0])
    if not results: return None
    best_box = None
    max_area = 0
    for result in results:
        boxes = result.boxes
        for box in boxes:
            x1, y1, x2, y2 = [int(i) for i in box.xyxy[0]]
            w = x2 - x1
            h = y2 - y1
            area = w * h
            if area > max_area:
                max_area = area
                face_h = int(h * 0.4)
                best_box = [x1, y1, w, face_h]
    return best_box

def create_general_frame(frame, output_width, output_height):
    orig_h, orig_w = frame.shape[:2]
    bg_scale = output_height / orig_h
    bg_w = int(orig_w * bg_scale)
    bg_resized = cv2.resize(frame, (bg_w, output_height))
    start_x = (bg_w - output_width) // 2
    if start_x < 0: start_x = 0
    background = bg_resized[:, start_x:start_x+output_width]
    if background.shape[1] != output_width:
        background = cv2.resize(background, (output_width, output_height))
    background = cv2.GaussianBlur(background, (51, 51), 0)
    scale = output_width / orig_w
    fg_h = int(orig_h * scale)
    foreground = cv2.resize(frame, (output_width, fg_h))
    y_offset = (output_height - fg_h) // 2
    final_frame = background.copy()
    final_frame[y_offset:y_offset+fg_h, :] = foreground
    return final_frame

def analyze_scenes_strategy(video_path, scenes):
    cap = cv2.VideoCapture(video_path)
    strategies = []
    if not cap.isOpened(): return ['TRACK'] * len(scenes)
    for start, end in tqdm(scenes, desc="   Analyzing Scenes"):
        frames_to_check = [start.get_frames() + 5, int((start.get_frames() + end.get_frames()) / 2), end.get_frames() - 5]
        face_counts = []
        for f_idx in frames_to_check:
            cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = cap.read()
            if not ret: continue
            candidates = detect_face_candidates(frame)
            face_counts.append(len(candidates))
        avg_faces = sum(face_counts) / len(face_counts) if face_counts else 0
        if avg_faces > 1.2 or avg_faces < 0.5: strategies.append('GENERAL')
        else: strategies.append('TRACK')
    cap.release()
    return strategies

def detect_scenes(video_path):
    video = scenedetect.open_video(video_path)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video=video, show_progress=False)
    scene_list = scene_manager.get_scene_list()
    fps = video.frame_rate
    return scene_list, fps

def get_video_resolution(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened(): raise IOError(f"Could not open video file {video_path}")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return width, height

def sanitize_filename(filename):
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = filename.replace(' ', '_')
    return filename[:100]

def download_youtube_video(url, output_dir="."):
    print(f"🔍 Debug: yt-dlp version: {yt_dlp.version.__version__}")
    print("📥 Downloading video from YouTube...")
    step_start_time = time.time()
    cookies_path = '/app/cookies.txt'
    cookies_env = os.environ.get("YOUTUBE_COOKIES")
    if cookies_env:
        try:
            with open(cookies_path, 'w') as f: f.write(cookies_env)
        except Exception as e: cookies_path = None
    else: cookies_path = None
    
    ydl_opts_info = {'quiet': True, 'no_warnings': True, 'cookiefile': cookies_path, 'nocheckcertificate': True}
    with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            video_title = info.get('title', 'youtube_video')
            sanitized_title = sanitize_filename(video_title)
        except Exception as e: raise e
    
    output_template = os.path.join(output_dir, f'{sanitized_title}.%(ext)s')
    
    # Force H.264/AVC to avoid AV1 issues in OpenCV
    ydl_opts = {
        'format': 'bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/best[ext=mp4]/best', 
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
        'quiet': False, 'verbose': True, 'no_warnings': False, 'overwrites': True,
        'cookiefile': cookies_path, 'nocheckcertificate': True,
        'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
    
    downloaded_file = os.path.join(output_dir, f'{sanitized_title}.mp4')
    if not os.path.exists(downloaded_file):
        for f in os.listdir(output_dir):
            if f.startswith(sanitized_title) and f.endswith('.mp4'):
                downloaded_file = os.path.join(output_dir, f)
                break
    print(f"✅ Video downloaded in {time.time() - step_start_time:.2f}s: {downloaded_file}")
    return downloaded_file, sanitized_title

def create_stitched_clip(clip_data, input_video, output_path, work_dir):
    """
    Cuts multiple segments defined in clip_data and stitches them into a single file.
    Returns the path to the stitched file (or None if failed).
    """
    segments = clip_data.get('segments', [])
    
    # Fallback for legacy/continuous clips
    if not segments and 'start' in clip_data:
        segments = [{'start': clip_data['start'], 'end': clip_data['end']}]
    
    if not segments:
        print("   ❌ No segments found.")
        return None

    # If only one segment, just cut it directly (faster)
    if len(segments) == 1:
        start, end = segments[0]['start'], segments[0]['end']
        cmd = [
            'ffmpeg', '-y', '-ss', str(start), '-to', str(end),
            '-i', input_video, 
            '-c:v', 'libx264', '-crf', '18', '-preset', 'fast',
            '-c:a', 'aac', 
            output_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return output_path

    # Multi-segment stitching
    segment_files = []
    base_name = os.path.basename(output_path)
    
    try:
        # 1. Cut individual segments
        for i, seg in enumerate(segments):
            seg_temp = os.path.join(work_dir, f"temp_seg_{i}_{base_name}")
            cmd = [
                'ffmpeg', '-y', '-ss', str(seg['start']), '-to', str(seg['end']),
                '-i', input_video,
                '-c:v', 'libx264', '-crf', '18', '-preset', 'fast',
                '-c:a', 'aac',
                seg_temp
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            segment_files.append(seg_temp)

        # 2. Create concat list
        list_file = os.path.join(work_dir, f"concat_{base_name}.txt")
        with open(list_file, 'w') as f:
            for seg_file in segment_files:
                f.write(f"file '{os.path.abspath(seg_file)}'\n")

        # 3. Concatenate
        concat_cmd = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', list_file, '-c', 'copy', output_path
        ]
        subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        
        # Cleanup
        if os.path.exists(list_file): os.remove(list_file)
        for f in segment_files:
            if os.path.exists(f): os.remove(f)
            
        return output_path

    except Exception as e:
        print(f"   ❌ Stitching failed: {e}")
        return None

def process_video_to_vertical(input_video, final_output_video):
    script_start_time = time.time()
    base_name = os.path.splitext(final_output_video)[0]
    temp_video_output = f"{base_name}_temp_video.mp4"
    temp_audio_output = f"{base_name}_temp_audio.aac"
    if os.path.exists(temp_video_output): os.remove(temp_video_output)
    if os.path.exists(temp_audio_output): os.remove(temp_audio_output)
    if os.path.exists(final_output_video): os.remove(final_output_video)

    print(f"🎬 Processing clip: {input_video}")
    print("   Step 1: Detecting scenes...")
    scenes, fps = detect_scenes(input_video)
    if not scenes:
        cap = cv2.VideoCapture(input_video)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        from scenedetect import FrameTimecode
        scenes = [(FrameTimecode(0, fps), FrameTimecode(total_frames, fps))]

    print(f"   ✅ Found {len(scenes)} scenes.")
    print("\n   🧠 Step 2: Preparing Active Tracking...")
    original_width, original_height = get_video_resolution(input_video)
    OUTPUT_HEIGHT = original_height
    OUTPUT_WIDTH = int(OUTPUT_HEIGHT * ASPECT_RATIO)
    if OUTPUT_WIDTH % 2 != 0: OUTPUT_WIDTH += 1

    cameraman = SmoothedCameraman(OUTPUT_WIDTH, OUTPUT_HEIGHT, original_width, original_height)
    print("\n   🤖 Step 3: Analyzing Scenes for Strategy (Single vs Group)...")
    scene_strategies = analyze_scenes_strategy(input_video, scenes)
    print("\n   ✂️ Step 4: Processing video frames...")
    
    command = [
        'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo',
        '-s', f'{OUTPUT_WIDTH}x{OUTPUT_HEIGHT}', '-pix_fmt', 'bgr24',
        '-r', str(fps), '-i', '-', 
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        '-preset', 'fast', '-crf', '23', '-an', temp_video_output
    ]

    ffmpeg_process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    cap = cv2.VideoCapture(input_video)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_number = 0
    current_scene_index = 0
    scene_boundaries = []
    for s_start, s_end in scenes:
        scene_boundaries.append((s_start.get_frames(), s_end.get_frames()))
    speaker_tracker = SpeakerTracker(cooldown_frames=30)

    with tqdm(total=total_frames, desc="   Processing", file=sys.stdout) as pbar:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            if current_scene_index < len(scene_boundaries):
                start_f, end_f = scene_boundaries[current_scene_index]
                if frame_number >= end_f and current_scene_index < len(scene_boundaries) - 1:
                    current_scene_index += 1
            current_strategy = scene_strategies[current_scene_index] if current_scene_index < len(scene_strategies) else 'TRACK'
            
            if current_strategy == 'GENERAL':
                output_frame = create_general_frame(frame, OUTPUT_WIDTH, OUTPUT_HEIGHT)
                cameraman.current_center_x = original_width / 2
                cameraman.target_center_x = original_width / 2
            else:
                if frame_number % 2 == 0:
                    candidates = detect_face_candidates(frame)
                    target_box = speaker_tracker.get_target(candidates, frame_number, original_width)
                    if target_box: cameraman.update_target(target_box)
                    else:
                        person_box = detect_person_yolo(frame)
                        if person_box: cameraman.update_target(person_box)
                is_scene_start = (frame_number == scene_boundaries[current_scene_index][0])
                x1, y1, x2, y2 = cameraman.get_crop_box(force_snap=is_scene_start)
                if y2 > y1 and x2 > x1:
                    cropped = frame[y1:y2, x1:x2]
                    output_frame = cv2.resize(cropped, (OUTPUT_WIDTH, OUTPUT_HEIGHT))
                else:
                    output_frame = cv2.resize(frame, (OUTPUT_WIDTH, OUTPUT_HEIGHT))

            ffmpeg_process.stdin.write(output_frame.tobytes())
            frame_number += 1
            pbar.update(1)
    
    ffmpeg_process.stdin.close()
    stderr_output = ffmpeg_process.stderr.read().decode()
    ffmpeg_process.wait()
    cap.release()

    if ffmpeg_process.returncode != 0:
        print("\n   ❌ FFmpeg frame processing failed.")
        print("   Stderr:", stderr_output)
        return False

    print("\n   🔊 Step 5: Extracting audio...")
    audio_extract_command = ['ffmpeg', '-y', '-i', input_video, '-vn', '-acodec', 'copy', temp_audio_output]
    try: subprocess.run(audio_extract_command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError: pass

    print("\n   ✨ Step 6: Merging...")
    if os.path.exists(temp_audio_output):
        merge_command = ['ffmpeg', '-y', '-i', temp_video_output, '-i', temp_audio_output, '-c:v', 'copy', '-c:a', 'copy', final_output_video]
    else:
         merge_command = ['ffmpeg', '-y', '-i', temp_video_output, '-c:v', 'copy', final_output_video]
    try:
        subprocess.run(merge_command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        print(f"   ✅ Clip saved to {final_output_video}")
    except subprocess.CalledProcessError as e:
        print("\n   ❌ Final merge failed.")
        print("   Stderr:", e.stderr.decode())
        return False

    if os.path.exists(temp_video_output): os.remove(temp_video_output)
    if os.path.exists(temp_audio_output): os.remove(temp_audio_output)
    return True

# --- YOUR REQUESTED SNIPPET IMPLEMENTATION ---
def get_youtube_transcript(url):
    """Fetches transcript directly from YouTube using the INSTANCE BASED approach you provided."""
    if not YouTubeTranscriptApi:
        return None
    
    print("🌍 Attempting to fetch transcript directly from YouTube...")
    try:
        # 1. EXTRACT ID
        regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
        match = re.search(regex, url)
        if not match:
            print("   ⚠️ Could not extract video ID via regex.")
            return None
        video_id = match.group(1)
        print(f"   🆔 Video ID: {video_id}")

        # 2. FETCH USING YOUR SNIPPET LOGIC
        # Attempt 1: Your specific instance method (likely from a specific version/wrapper)
        raw_data = None
        try:
            print("   ▶️ Trying Instance-based fetch (Your Snippet)...")
            ytt_api = YouTubeTranscriptApi()  # Instantiate
            transcript_obj = ytt_api.fetch(video_id) # Call fetch
            raw_data = transcript_obj.to_raw_data() # Get data
        except Exception as e1:
            print(f"   ⚠️ Instance method failed ({e1}). Trying Static method...")
            # Attempt 2: Standard Static Method (Fallback within the wrapper)
            try:
                raw_data = YouTubeTranscriptApi.get_transcript(video_id)
            except Exception as e2:
                print(f"   ⚠️ Static method failed ({e2}).")
                return None

        if not raw_data:
            return None

        # 3. FORMAT FOR GEMINI
        full_text = ""
        segments = []
        
        for item in raw_data:
            text = item['text']
            start = item['start']
            duration = item.get('duration', 0.0) # Duration might be missing in some raw formats
            end = start + duration
            
            full_text += text + " "
            
            # Heuristic for word timestamps
            words_list = []
            raw_words = text.split()
            if raw_words:
                word_duration = duration / len(raw_words) if duration > 0 else 0
                for i, w in enumerate(raw_words):
                    words_list.append({
                        'word': w,
                        'start': start + (i * word_duration),
                        'end': start + ((i + 1) * word_duration),
                        'probability': 1.0
                    })

            segments.append({
                'text': text,
                'start': start,
                'end': end,
                'words': words_list
            })
            
        print("   ✅ YouTube Transcript fetched successfully!")
        return {'text': full_text.strip(), 'segments': segments, 'language': 'en'}

    except Exception as e:
        print(f"   ⚠️ YouTube Transcript fetch failed: {e}")
        print("   ➡️ Falling back to Whisper...")
        return None

def transcribe_video(video_path):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    print(f"🎙️  Transcribing video with Faster-Whisper ({device.upper()} Optimized - {compute_type})...")
    from faster_whisper import WhisperModel
    model = WhisperModel("base", device=device, compute_type=compute_type)
    segments, info = model.transcribe(video_path, word_timestamps=True)
    print(f"   Detected language '{info.language}' with probability {info.language_probability:.2f}")
    transcript_segments = []
    full_text = ""
    for segment in segments:
        print(f"   [{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
        seg_dict = {'text': segment.text, 'start': segment.start, 'end': segment.end, 'words': []}
        if segment.words:
            for word in segment.words:
                seg_dict['words'].append({'word': word.word, 'start': word.start, 'end': word.end, 'probability': word.probability})
        transcript_segments.append(seg_dict)
        full_text += segment.text + " "
    return {'text': full_text.strip(), 'segments': transcript_segments, 'language': info.language}

def add_scripts_to_clips(transcript, clips):
    """Maps timestamps back to text, handling multi-segment jump cuts."""
    all_words = []
    for seg in transcript['segments']:
        if 'words' in seg:
            all_words.extend(seg['words'])
            
    for clip in clips:
        # Calculate full script from all segments
        segments = clip.get('segments', [])
        
        # Fallback if AI didn't output segments but used start/end
        if not segments and 'start' in clip:
            segments = [{'start': clip['start'], 'end': clip['end']}]
            
        full_script = []
        for seg in segments:
            s, e = seg['start'], seg['end']
            seg_words = [w['word'] for w in all_words if w['start'] >= s and w['end'] <= e]
            full_script.append(" ".join(seg_words))
        
        clip['script'] = " ... ".join(full_script) # Use "..." to indicate jumps

        # CRITICAL: Backfill top-level start/end for Frontend Compatibility
        if segments:
            clip['start'] = segments[0]['start']
            clip['end'] = segments[-1]['end']
            
    return clips

def get_viral_clips(transcript_result, video_duration, style="original"):
    print("🤖  Analyzing with Gemini...")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found.")
        return None
    client = genai.Client(api_key=api_key)
    # Using specific model version to ensure availability
    model_name = 'gemini-2.5-flash' 
    
    # Collect all words
    all_words = []
    for segment in transcript_result['segments']:
        for word in segment.get('words', []):
            all_words.append({'w': word['word'], 's': word['start'], 'e': word['end']})
    
    # OPTIMIZATION: Sample words for long videos to avoid rate limits
    # Free tier limit: 250K tokens/minute. A long transcript can easily exceed this.
    total_words = len(all_words)
    
    # Decide sampling rate based on video length
    if total_words < 1000:  # ~10 min video
        words = all_words
        print(f"   📊 Using all {total_words} words for analysis")
    elif total_words < 2000:  # ~20 min video
        words = all_words[::2]  # Every 2nd word
        print(f"   📊 Sampling every 2nd word ({len(words)}/{total_words}) to stay within rate limits")
    elif total_words < 3000:  # ~30 min video
        words = all_words[::3]  # Every 3rd word
        print(f"   📊 Sampling every 3rd word ({len(words)}/{total_words}) to stay within rate limits")
    else:  # Very long videos
        words = all_words[::5]  # Every 5th word
        print(f"   📊 Sampling every 5th word ({len(words)}/{total_words}) to stay within rate limits")
    
    prompt_template = PROMPT_LIBRARY.get(style, PROMPT_LIBRARY["original"])
    prompt = prompt_template.format(
        video_duration=video_duration, 
        transcript_text=json.dumps(transcript_result['text']), 
        words_json=json.dumps(words)
    )
    
    # Retry logic for rate limits
    max_retries = 3
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            
            # If successful, process the response
            try:
                usage = response.usage_metadata
                if usage:
                    input_cost = (usage.prompt_token_count / 1_000_000) * 0.10
                    output_cost = (usage.candidates_token_count / 1_000_000) * 0.40
                    total_cost = input_cost + output_cost
                    cost_analysis = {
                        "input_tokens": usage.prompt_token_count, 
                        "output_tokens": usage.candidates_token_count, 
                        "total_cost": total_cost, 
                        "model": model_name
                    }
                    print(f"💰 Estimated Cost: ${total_cost:.6f} (Input: {usage.prompt_token_count} tokens)")
            except Exception: 
                cost_analysis = None

            text = response.text
            
            # --- ROBUST JSON EXTRACTION ---
            try:
                start_index = text.find('{')
                end_index = text.rfind('}')
                if start_index != -1 and end_index != -1:
                    json_str = text[start_index : end_index + 1]
                    result_json = json.loads(json_str)
                else:
                    if text.startswith("```json"): text = text[7:]
                    if text.endswith("```"): text = text[:-3]
                    text = text.strip()
                    result_json = json.loads(text)
            except json.JSONDecodeError as e:
                print(f"❌ Gemini JSON Parse Error: {e}")
                print(f"   Raw Text: {text[:200]}...") 
                return None

            if cost_analysis: result_json['cost_analysis'] = cost_analysis
            return result_json
            
        except Exception as e:
            error_str = str(e)
            
            # Check if it's a rate limit error (429)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                retry_count += 1
                
                # Try to extract retry delay from error message
                retry_delay = None
                try:
                    import re
                    # Look for "retry in XXs" or "retryDelay: XXs"
                    match = re.search(r'retry.*?(\d+(?:\.\d+)?)\s*s', error_str, re.IGNORECASE)
                    if match:
                        retry_delay = float(match.group(1))
                except:
                    pass
                
                # Use exponential backoff if no delay specified
                if retry_delay is None:
                    retry_delay = min(30 * (2 ** (retry_count - 1)), 120)  # Max 120s
                
                if retry_count <= max_retries:
                    print(f"⚠️  Rate limit hit. Waiting {retry_delay:.1f}s before retry {retry_count}/{max_retries}...")
                    time.sleep(retry_delay)
                else:
                    print(f"❌ Gemini Error (after {max_retries} retries): {e}")
                    return None
            else:
                # Not a rate limit error, fail immediately
                print(f"❌ Gemini Error: {e}")
                return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="AutoCrop-Vertical with Viral Clip Detection.")
    parser.add_argument('--analyze-only', action='store_true', help="Stop after generating metadata.json (for review).")
    parser.add_argument('--process-indices', type=str, help="Comma-separated list of clip indices to process (e.g. '0,2,5').")
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('-i', '--input', type=str, help="Path to input video.")
    input_group.add_argument('-u', '--url', type=str, help="YouTube URL.")
    
    parser.add_argument('-o', '--output', type=str, help="Output directory.")
    parser.add_argument('--keep-original', action='store_true', help="Keep original video.")
    parser.add_argument('--skip-analysis', action='store_true', help="Process whole video.")
    parser.add_argument('--style', type=str, default='original', choices=list(PROMPT_LIBRARY.keys()), help="Style of viral clips to generate.")

    
    args = parser.parse_args()
    script_start_time = time.time()
    
    def _ensure_dir(path: str) -> str:
        if path: os.makedirs(path, exist_ok=True)
        return path
    
    # --- 1. SETUP OUTPUT DIRECTORY ---
    if args.output and os.path.isdir(args.output):
        output_dir = args.output
    elif args.output:
        output_dir = _ensure_dir(args.output)
    else:
        output_dir = "."

    # --- 2. INPUT HANDLING ---
    if args.url:
        if args.process_indices:
            print(f"🔄 Phase 2: Searching for existing video in {output_dir}...")
            candidates = [f for f in os.listdir(output_dir) if f.endswith('.mp4') and '_clip_' not in f and 'vertical' not in f]
            if candidates:
                candidates.sort(key=lambda f: os.path.getsize(os.path.join(output_dir, f)), reverse=True)
                input_video = os.path.join(output_dir, candidates[0])
                video_title = os.path.splitext(candidates[0])[0]
                print(f"   ✅ Found cached video: {input_video}")
            else:
                 print("   ⚠️ Video not found. Re-downloading...")
                 input_video, video_title = download_youtube_video(args.url, output_dir)
        else:
            input_video, video_title = download_youtube_video(args.url, output_dir)
    else:
        input_video = args.input
        video_title = os.path.splitext(os.path.basename(input_video))[0]
        if not output_dir: output_dir = os.path.dirname(input_video)

    if not os.path.exists(input_video):
        print(f"❌ Input file not found: {input_video}")
        exit(1)

    metadata_file = os.path.join(output_dir, f"{video_title}_metadata.json")

# --- 3. LOGIC BRANCHING ---
    
    # CASE A: Process Only Specific Clips (Phase 2)
    if args.process_indices:
        print(f"🎬 Phase 2: Generating Selected Clips [{args.process_indices}]")
        if not os.path.exists(metadata_file):
            print(f"❌ Metadata file not found: {metadata_file}. Run analysis first.")
            exit(1)
        
        with open(metadata_file, 'r') as f:
            clips_data = json.load(f)
            
        selected_indices = [int(i) for i in args.process_indices.split(',') if i.strip().isdigit()]
        
        for i, clip in enumerate(clips_data['shorts']):
            if i not in selected_indices:
                continue
                
            print(f"\n🎬 Rendering Clip {i+1} (Selected)...")
            
            clip_filename = f"{video_title}_clip_{i+1}.mp4"
            clip_temp_path = os.path.join(output_dir, f"temp_{clip_filename}")
            clip_final_path = os.path.join(output_dir, clip_filename)
            
            # --- NEW STITCHING LOGIC ---
            # This stitches the segments first, then passes the result to the vertical cropper
            stitched_file = create_stitched_clip(clip, input_video, clip_temp_path, output_dir)
            
            if stitched_file:
                # Vertical Crop
                success = process_video_to_vertical(stitched_file, clip_final_path)
                
                if success: print(f"   ✅ Clip {i+1} Ready: {clip_final_path}")
                # Cleanup stitched temp
                if os.path.exists(stitched_file): os.remove(stitched_file)
            
        print("\n✅ Generation Complete.")
        exit(0)

    # CASE B: Analyze Only (Phase 1)
    if args.analyze_only:
        print("🔍 Phase 1: Analysis Only (No Video Generation)")
        
        transcript = None
        if args.url:
            transcript = get_youtube_transcript(args.url)
        
        if not transcript:
            transcript = transcribe_video(input_video)
        
        cap = cv2.VideoCapture(input_video)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps
        cap.release()
        
        clips_data = get_viral_clips(transcript, duration, style=args.style)
        
        if clips_data and 'shorts' in clips_data:
            # Add Scripts (Updated to handle segments)
            clips_data['shorts'] = add_scripts_to_clips(transcript, clips_data['shorts'])
            
            # Save
            clips_data['transcript'] = transcript
            with open(metadata_file, 'w') as f:
                json.dump(clips_data, f, indent=2)
            print(f"✅ Analysis Saved: {metadata_file}")
            print(f"📊 Found {len(clips_data['shorts'])} potential viral clips.")
        else:
            print("❌ No clips found.")
            
        exit(0)

    # CASE C: Legacy / Skip Analysis (Default)
    if args.skip_analysis:
        print("⏩ Processing Entire Video...")
        output_file = os.path.join(output_dir, f"{video_title}_vertical.mp4")
        process_video_to_vertical(input_video, output_file)
    else:
        # Standard Flow (Analyze + Process All)
        transcript = None
        if args.url:
            transcript = get_youtube_transcript(args.url)
        
        if not transcript:
            transcript = transcribe_video(input_video)

        cap = cv2.VideoCapture(input_video)
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / fps
        cap.release()
        
        clips_data = get_viral_clips(transcript, duration, style=args.style)
        
        if clips_data:
            clips_data['shorts'] = add_scripts_to_clips(transcript, clips_data['shorts'])
            clips_data['transcript'] = transcript
            with open(metadata_file, 'w') as f: json.dump(clips_data, f, indent=2)
            
            for i, clip in enumerate(clips_data['shorts']):
                print(f"Processing Clip {i+1}...")
                clip_filename = f"{video_title}_clip_{i+1}.mp4"
                clip_temp = os.path.join(output_dir, f"temp_{clip_filename}")
                clip_final = os.path.join(output_dir, clip_filename)
                
                # --- NEW STITCHING LOGIC ---
                stitched_file = create_stitched_clip(clip, input_video, clip_temp, output_dir)
                
                if stitched_file:
                    process_video_to_vertical(stitched_file, clip_final)
                    if os.path.exists(stitched_file): os.remove(stitched_file)

    # Clean up original if requested AND we are in a mode that consumed it
    if args.url and not args.keep_original and os.path.exists(input_video):
        if not args.analyze_only:
            os.remove(input_video)
            print("🗑️  Cleaned up original video.")

    print(f"\n⏱️  Total time: {time.time() - script_start_time:.2f}s")
