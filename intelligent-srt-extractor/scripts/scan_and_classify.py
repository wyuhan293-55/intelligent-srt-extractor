#!/usr/bin/env python3
"""
Scan video folders and classify content into:
- SKIP: definitely no speech (B-roll, environment, unboxing, etc.)
- TRANSCRIBE: definitely has speech (interview, consultation, etc.)
- UNSURE: need user confirmation

Usage:
    python scan_and_classify.py "<folder_path>"
"""

import os
import sys
import json
from pathlib import Path

# ── Video extensions ───────────────────────────────────────────────
VIDEO_EXTS = {'.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v', '.mpg', '.mpeg', '.wmv', '.flv', '.3gp'}

# ── Classification rules ───────────────────────────────────────────
# Keywords in folder/file names that indicate "definitely skip"
SKIP_KEYWORDS = [
    # No dialogue content
    "开箱", "拆包", "unbox",
    "自拍", "氛围感", "b-roll", "B-roll",
    "灰底", "灰背景", "grey", "gray",
    "环境", "病床环境", "空镜",
    "等待", "等候",
    "朋友圈", "微信视频",
    "图片", "照片", "photo", "jpg",
    "术后即刻",
    "合影", "合照", "集体照",
    "术中", "手术过程",
    "案例协议", "协议",
    "术前档案室",
    "面诊图片", "画线照片",
    "术前即刻",
    "术后效果",
]

# Keywords that indicate "definitely transcribe"
TRANSCRIBE_KEYWORDS = [
    "采访", "访谈", "interview",
    "面诊", "问诊", "consult",
    "查房", "巡房",
    "讲解", "分析", "说明",
    "核对", "确认",
    "术前沟通",
    "术后回访",
]

# File size thresholds (MB)
SKIP_SIZE_MB = 3        # < 3MB almost certainly no meaningful audio
SUSPECT_SIZE_MB = 10    # 3-10MB could go either way
LARGE_FILE_MB = 100     # > 100MB: professional camera, may be silent


def get_folder_keywords(folder_path: str, base_dir: str) -> list:
    """Get relative path parts as keywords for matching."""
    try:
        rel = os.path.relpath(folder_path, base_dir)
    except ValueError:
        rel = os.path.basename(folder_path)
    parts = []
    for p in Path(rel).parts:
        parts.extend(p.lower().replace('_', ' ').replace('-', ' ').split())
    return parts


def classify_video(filepath: str, folder_keywords: list) -> str:
    """
    Classify a single video: 'skip', 'transcribe', or 'unsure'
    """
    filename = os.path.basename(filepath).lower()
    filepath_lower = filepath.lower()
    size_mb = os.path.getsize(filepath) / (1024 * 1024)

    # Check for existing SRT
    srt_path = os.path.splitext(filepath)[0] + '.srt'
    if os.path.exists(srt_path) and os.path.getsize(srt_path) > 50:
        return 'skip'

    # Build all keywords to check (folder + filename)
    all_kw = folder_keywords + [filename]

    # ── Definite SKIP checks ──
    # Size-based
    if size_mb < SKIP_SIZE_MB:
        return 'skip'

    # Keyword-based
    for kw in SKIP_KEYWORDS:
        kw_lower = kw.lower()
        # Check in full path
        if kw_lower in filepath_lower:
            return 'skip'

    # ── Definite TRANSCRIBE checks ──
    for kw in TRANSCRIBE_KEYWORDS:
        if kw.lower() in filepath_lower:
            return 'transcribe'

    # ── Heuristic fallbacks ──
    # Large professional camera files
    if size_mb > LARGE_FILE_MB:
        return 'unsure'

    # Medium files in unknown contexts
    if SKIP_SIZE_MB <= size_mb <= SUSPECT_SIZE_MB:
        return 'unsure'

    # Default: unsure for anything not matched
    return 'unsure'


def scan_folder(folder_path: str):
    """Main scan function. Returns structured classification results."""
    if not os.path.isdir(folder_path):
        print(f"ERROR: {folder_path} is not a valid directory")
        sys.exit(1)

    base = os.path.abspath(folder_path)
    all_videos = []
    existing_srts = set()

    # Collect all video files and existing SRTs
    for root, dirs, files in os.walk(base):
        # Ignore hidden folders
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in sorted(files):
            fp = os.path.join(root, f)
            ext = os.path.splitext(f)[1].lower()
            if ext in VIDEO_EXTS:
                all_videos.append(fp)
            elif ext == '.srt':
                existing_srts.add(os.path.splitext(fp)[0])

    # Classify
    skip_list = []
    transcribe_list = []
    unsure_list = []

    # Cache folder keywords
    folder_kw_cache = {}

    for v in all_videos:
        folder = os.path.dirname(v)
        if folder not in folder_kw_cache:
            folder_kw_cache[folder] = get_folder_keywords(folder, base)

        classification = classify_video(v, folder_kw_cache[folder])
        rel_path = os.path.relpath(v, base)
        size_mb = os.path.getsize(v) / (1024 * 1024)

        # Check audio for unsure large files (quick ffprobe probe)
        if classification == 'unsure' and size_mb > LARGE_FILE_MB:
            import subprocess
            try:
                r = subprocess.run(
                    ['ffprobe', '-v', 'quiet', '-select_streams', 'a:0',
                     '-show_entries', 'stream=duration', '-of', 'default=noprint_wrappers=1:nokey=1', v],
                    capture_output=True, text=True, timeout=15
                )
                dur = float(r.stdout.strip()) if r.stdout.strip() else 0
                if dur < 1.0:
                    classification = 'skip'
                    rel_path += f" [无声, {dur:.1f}s]"
            except Exception:
                pass

        entry = {'path': rel_path, 'size_mb': round(size_mb, 1)}

        if classification == 'skip':
            skip_list.append(entry)
        elif classification == 'transcribe':
            transcribe_list.append(entry)
        else:
            unsure_list.append(entry)

    # Print results
    print(f"\n{'='*70}")
    print(f"扫描结果: {base}")
    print(f"{'='*70}")

    total_videos = len(all_videos)
    print(f"\n📹 总视频数: {total_videos}")
    print(f"📝 已有SRT:  {len(existing_srts)}")

    print(f"\n{'─'*70}")
    print(f"✅ 需转录 ({len(transcribe_list)} 个):")
    print(f"{'─'*70}")
    for e in transcribe_list:
        print(f"  + {e['path']}  ({e['size_mb']:.1f}MB)")

    print(f"\n{'─'*70}")
    print(f"⏭️  跳过 ({len(skip_list)} 个):")
    print(f"{'─'*70}")
    for e in skip_list:
        print(f"  - {e['path']}  ({e['size_mb']:.1f}MB)")

    print(f"\n{'─'*70}")
    print(f"❓ 不确定 ({len(unsure_list)} 个):")
    print(f"{'─'*70}")
    if unsure_list:
        for i, e in enumerate(unsure_list, 1):
            print(f"  {i}. {e['path']}  ({e['size_mb']:.1f}MB)")

    print(f"\n{'='*70}")
    print("如需转录不确定的视频，请确认编号后重新运行转录。")
    print(f"{'='*70}\n")

    # Output JSON for programmatic use
    result = {
        'base': base,
        'total': total_videos,
        'existing_srts': len(existing_srts),
        'transcribe': transcribe_list,
        'skip': skip_list,
        'unsure': unsure_list,
    }
    return result


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scan_and_classify.py <folder_path>")
        sys.exit(1)
    scan_folder(sys.argv[1])
