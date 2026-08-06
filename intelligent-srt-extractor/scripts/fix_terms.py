#!/usr/bin/env python3
"""
SRT 术语自动修正 — 扫描 SRT 文件，使用 medical_terms.py 词典修正 Whisper 常见误识别。
同时检测低质量 SRT（文件过小/静音幻觉）。

Usage:
    python fix_terms.py "<folder_path>"              # 扫描文件夹内所有 .srt
    python fix_terms.py "<folder_path>" --dry-run    # 预览修改，不实际写入
    python fix_terms.py "<folder_path>" --fix        # 自动修复并覆盖
"""

import os
import sys
import re
from pathlib import Path

# Import the lexicon (allow relative import)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PACKAGE_DIR)

try:
    from lexicon.medical_terms import TERM_CORRECTIONS, apply_term_fix
except ImportError:
    # Fallback: load directly
    lexicon_path = os.path.join(PACKAGE_DIR, 'lexicon', 'medical_terms.py')
    if os.path.exists(lexicon_path):
        import importlib.util
        spec = importlib.util.spec_from_file_location("medical_terms", lexicon_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        TERM_CORRECTIONS = mod.TERM_CORRECTIONS
        apply_term_fix = mod.apply_term_fix
    else:
        print("ERROR: Cannot find lexicon/medical_terms.py")
        sys.exit(1)


def parse_srt(path: str) -> list[dict]:
    """Parse SRT file into list of {index, start, end, text}"""
    try:
        text = Path(path).read_text(encoding='utf-8-sig', errors='replace')
    except Exception:
        return []

    entries = []
    blocks = re.split(r'\n\s*\n', text.strip())
    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if len(lines) < 2:
            continue
        tline = None
        for l in lines:
            if '-->' in l:
                tline = l
                break
        if not tline:
            continue
        m = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', tline)
        if not m:
            continue
        content = ' '.join(l for l in lines if l != tline and not l.isdigit()).strip()
        if content:
            entries.append({'start': m.group(1), 'end': m.group(2), 'text': content})
    return entries


def check_and_fix_srt(srt_path: str, fix: bool = False) -> dict:
    """Check one SRT file for issues. If fix=True, rewrite corrected version."""
    entries = parse_srt(srt_path)
    issues = []
    fixes = 0

    if not entries:
        return {'path': srt_path, 'status': 'empty', 'segments': 0, 'issues': ['文件为空或无法解析'], 'fixes': 0}

    file_size = os.path.getsize(srt_path)

    # Check: suspiciously small SRT
    if file_size < 50:
        issues.append(f'文件极小 ({file_size}B)，可能为静音幻觉')

    # Check: garbled text patterns
    garbled_patterns = [
        r'[\x00-\x08\x0b\x0c\x0e-\x1f]',  # control chars
        r'[Α-Ωα-ω]',  # Greek (common hallucination)
        r'[А-Яа-я]',  # Cyrillic (common hallucination)
    ]
    for entry in entries:
        for pat in garbled_patterns:
            if re.search(pat, entry['text']):
                issues.append(f'段{entries.index(entry)+1}: 含乱码字符 "{entry["text"][:20]}..."')
                break

    # Apply term corrections
    if fix:
        modified = False
        for entry in entries:
            original = entry['text']
            corrected = apply_term_fix(original)
            if corrected != original:
                entry['text'] = corrected
                fixes += 1
                modified = True

        if modified:
            # Rewrite SRT
            with open(srt_path, 'w', encoding='utf-8') as f:
                for i, entry in enumerate(entries, 1):
                    f.write(f"{i}\n")
                    f.write(f"{entry['start']} --> {entry['end']}\n")
                    f.write(f"{entry['text']}\n\n")

    return {
        'path': srt_path,
        'status': 'ok',
        'segments': len(entries),
        'issues': issues,
        'fixes': fixes,
    }


def scan_folder(folder: str, fix: bool = False, dry_run: bool = True):
    """Scan all SRT files in a folder tree."""
    srt_files = []
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith('.srt'):
                srt_files.append(os.path.join(root, f))

    if not srt_files:
        print("No SRT files found.")
        return

    print(f"Scanning {len(srt_files)} SRT files...\n")

    results = []
    total_fixes = 0
    problem_count = 0

    for srt in sorted(srt_files):
        rel = os.path.relpath(srt, folder)
        if not dry_run:
            print(f"  Fixing: {rel} ... ", end='')
            res = check_and_fix_srt(srt, fix=True)
            if res['fixes'] > 0:
                print(f"{res['fixes']} 处修正")
            elif res['issues']:
                print(f"⚠ {res['issues']}")
            else:
                print("OK")
        else:
            # Dry run: check only
            res = check_and_fix_srt(srt, fix=False)
            if res['issues']:
                problem_count += 1
                print(f"  ⚠ {rel}")
                for iss in res['issues']:
                    print(f"     {iss}")
        results.append(res)
        total_fixes += res.get('fixes', 0)

    print(f"\n{'='*50}")
    print(f"扫描完成: {len(srt_files)} 个文件, {problem_count} 个有问题")
    if not dry_run:
        print(f"共修正: {total_fixes} 处术语")
    else:
        print("(预览模式，未实际修改。使用 --fix 执行修复)")
    print(f"{'='*50}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='SRT 术语修正 + 质量检测')
    parser.add_argument('path', help='SRT 文件所在目录')
    parser.add_argument('--fix', action='store_true', help='执行修复（默认仅预览）')
    parser.add_argument('--dry-run', action='store_true', default=True, help='预览模式（默认）')
    args = parser.parse_args()

    if args.fix:
        args.dry_run = False

    scan_folder(args.path, fix=args.fix, dry_run=args.dry_run)
