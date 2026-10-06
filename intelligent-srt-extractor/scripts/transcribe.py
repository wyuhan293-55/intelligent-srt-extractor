#!/usr/bin/env python3
"""
Video-to-SRT Transcription Script
Dual-engine: faster-whisper (GPU, preferred) → openai-whisper (CPU, fallback)
Output: .srt alongside source videos.

Usage:
    python transcribe.py <video_file_or_folder> [--model medium] [--device cuda] [--engine auto]
"""

import os
import sys
import csv
import time
import shutil
import argparse
import subprocess
import tempfile
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────
WHISPER_MODEL = "small"
WHISPER_LANG = "zh"
WHISPER_DEVICE = "cuda"
WHISPER_COMPUTE = "float16"
SKIP_EXISTING_SRT = True
MIN_AUDIO_DURATION = 1.0

VIDEO_EXTS = {'.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v', '.mpg', '.mpeg', '.wmv', '.flv', '.3gp'}

# Auto-detect ffmpeg
def _find_ffmpeg():
    """Find ffmpeg in PATH or common install locations."""
    candidates = ["ffmpeg"]
    if sys.platform == "win32":
        candidates += [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\ffmpeg\ffmpeg-8.1.2-essentials_build\bin\ffmpeg.exe",
        ]
    for c in candidates:
        try:
            subprocess.run([c, "-version"], capture_output=True, timeout=5, check=True)
            return os.path.dirname(c) if os.path.sep in c else None
        except Exception:
            continue
    return None

_FFMPEG_DIR = _find_ffmpeg()
if _FFMPEG_DIR:
    os.environ["PATH"] = _FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")

# ── Helpers ────────────────────────────────────────────────────────

def format_srt_time(seconds: float) -> str:
    ms = int((seconds % 1) * 1000)
    s = int(seconds)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def find_videos(path: str) -> list:
    p = Path(path)
    if p.is_file():
        return [str(p)] if p.suffix.lower() in VIDEO_EXTS else []
    videos = []
    for root, _, files in os.walk(path):
        for f in files:
            fp = Path(root) / f
            if fp.suffix.lower() in VIDEO_EXTS:
                if SKIP_EXISTING_SRT and fp.with_suffix('.srt').exists():
                    continue
                videos.append(str(fp))
    return videos


def write_srt(video_path: str, segments: list, elapsed: float) -> dict | None:
    base = os.path.splitext(video_path)[0]
    srt_path = base + '.srt'

    with open(srt_path, 'w', encoding='utf-8') as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n")
            f.write(f"{format_srt_time(seg['start'])} --> {format_srt_time(seg['end'])}\n")
            f.write(f"{seg['text'].strip()}\n\n")

    duration = segments[-1]['end'] if segments else 0
    speed = duration / elapsed if elapsed > 0 else 0
    print(f'  Segments: {len(segments)} | Duration: {duration:.0f}s | Speed: {speed:.1f}x -> {os.path.basename(srt_path)}')

    return {'video': os.path.basename(video_path), 'duration_s': round(duration,1), 'segments': len(segments), 'elapsed_s': round(elapsed,1)}


def extract_audio(video_path: str) -> str:
    """Extract audio to temp WAV, handling UNC paths for large files."""
    audio_path = os.path.join(tempfile.gettempdir(), f'_wsr_audio_{os.getpid()}.wav')
    is_unc = video_path.startswith('\\\\') or video_path.startswith('//')
    file_size = os.path.getsize(video_path) if os.path.exists(video_path) else 0
    local_video = video_path
    tmp_video = None

    if is_unc and file_size > 100 * 1024 * 1024:
        print(f'  Copying to local ({file_size/1024/1024:.0f}MB)...')
        tmp_video = os.path.join(tempfile.gettempdir(), f'_wsr_vid_{os.getpid()}_{os.path.basename(video_path)}')
        shutil.copy2(video_path, tmp_video)
        local_video = tmp_video

    cmd = ['ffmpeg', '-y', '-hwaccel', 'none', '-i', local_video,
           '-map', '0:a:0', '-ac', '1', '-ar', '16000', '-acodec', 'pcm_s16le', audio_path]
    r = subprocess.run(cmd, capture_output=True, text=True)

    if tmp_video:
        try: os.remove(tmp_video)
        except OSError: pass

    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {r.stderr[-300:]}")
    return audio_path


def get_audio_duration(audio_path: str) -> float:
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
           '-of', 'default=noprint_wrappers=1:nokey=1', audio_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try: return float(r.stdout.strip())
    except ValueError: return 0


# ── Engine: faster-whisper ─────────────────────────────────────────

def transcribe_faster(video_path, model) -> dict | None:
    t0 = time.time()
    print('  Extracting audio...')
    audio_path = extract_audio(video_path)
    duration = get_audio_duration(audio_path)

    if duration < MIN_AUDIO_DURATION:
        print(f'  SKIP: audio too short ({duration:.1f}s)')
        try: os.remove(audio_path)
        except OSError: pass
        return None

    segments_gen, _info = model.transcribe(
        audio_path, language=WHISPER_LANG, beam_size=5,
        word_timestamps=False, vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    segs = [{'start': s.start, 'end': s.end, 'text': s.text.strip()}
            for s in segments_gen if s.text.strip()]

    try: os.remove(audio_path)
    except OSError: pass

    if not segs:
        print(f'  No speech detected ({duration:.1f}s)')
        return None
    return write_srt(video_path, segs, time.time() - t0)


# ── Engine: openai-whisper ─────────────────────────────────────────

def transcribe_openai(video_path, model) -> dict | None:
    print('  Extracting audio...')
    audio_path = extract_audio(video_path)
    duration = get_audio_duration(audio_path)

    if duration < MIN_AUDIO_DURATION:
        print(f'  SKIP: audio too short ({duration:.1f}s)')
        try: os.remove(audio_path)
        except OSError: pass
        return None

    t0 = time.time()
    result = model.transcribe(audio_path, language=WHISPER_LANG, word_timestamps=True)
    segs = [{'start': s['start'], 'end': s['end'], 'text': s['text'].strip()}
            for s in result['segments'] if s['text'].strip()]

    try: os.remove(audio_path)
    except OSError: pass

    if not segs:
        print('  No speech detected')
        return None
    return write_srt(video_path, segs, time.time() - t0)


# ── Main ───────────────────────────────────────────────────────────

def main():
    global WHISPER_LANG, SKIP_EXISTING_SRT
    parser = argparse.ArgumentParser(description='Video → SRT transcription (dual-engine Whisper)')
    parser.add_argument('path', help='Video file or directory')
    parser.add_argument('--model', default=WHISPER_MODEL,
                        choices=['tiny','base','small','medium','large-v3','large-v3-turbo'])
    parser.add_argument('--device', default=WHISPER_DEVICE, choices=['cuda','cpu'])
    parser.add_argument('--compute', default=WHISPER_COMPUTE,
                        choices=['float16','float32','int8','int8_float16','bfloat16'])
    parser.add_argument('--engine', default='auto', choices=['auto','faster-whisper','openai-whisper'])
    parser.add_argument('--lang', default=WHISPER_LANG, help='Language code (default: zh)')
    parser.add_argument('--force', action='store_true', help='Overwrite existing SRT files')
    args = parser.parse_args()

    WHISPER_LANG = args.lang
    if args.force:
        SKIP_EXISTING_SRT = False

    if not os.path.exists(args.path):
        print(f'ERROR: {args.path} not found'); sys.exit(1)

    videos = find_videos(args.path)
    if not videos:
        print('No videos to transcribe (all have .srt, or none found).')
        sys.exit(0)

    print(f'Found {len(videos)} video(s) to transcribe\n')

    # Select engine
    model = None
    transcribe_fn = None
    engine = args.engine

    if engine in ('auto', 'faster-whisper'):
        try:
            from faster_whisper import WhisperModel
            print(f'Loading faster-whisper "{args.model}" on {args.device}/{args.compute}...')
            model = WhisperModel(args.model, device=args.device, compute_type=args.compute, num_workers=2)
            transcribe_fn = transcribe_faster
        except Exception as e:
            if engine == 'faster-whisper':
                print(f'ERROR: {e}'); sys.exit(1)
            print(f'faster-whisper unavailable, falling back to openai-whisper...')
            engine = 'openai-whisper'

    if engine == 'openai-whisper':
        import whisper
        print(f'Loading openai-whisper "{args.model}" on CPU...')
        model = whisper.load_model(args.model)
        transcribe_fn = transcribe_openai

    # Process
    results = []
    for v in videos:
        print(f'{"="*60}\nVideo: {os.path.basename(v)}')
        try:
            info = transcribe_fn(v, model)
            if info: results.append(info)
        except Exception as e:
            print(f'  ERROR: {e}')

    print(f'\nDone: {len(results)}/{len(videos)} transcribed')


if __name__ == '__main__':
    main()
