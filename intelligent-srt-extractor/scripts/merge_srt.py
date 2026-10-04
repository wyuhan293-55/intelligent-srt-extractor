#!/usr/bin/env python3
"""
Merge all valid SRT files under one case-material folder into a single case transcript.

Rules:
- Recursively discover .srt files.
- Ignore the generated aggregate file itself.
- Treat non-empty, parseable SRT files as valid.
- Preserve each source SRT's original cue numbers, timestamps, and subtitle text.
- Add only a source-file section header; do not renumber cues.
- Write the aggregate file back into the input case folder.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import List, Tuple

DEFAULT_OUTPUT_NAME = "案例素材母稿.txt"

TIMESTAMP_RE = re.compile(
    r"^\s*\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}(?:\s+.*)?$"
)


def natural_key(path: Path) -> list:
    """Stable natural sort: 2.srt comes before 10.srt."""
    return [
        int(part) if part.isdigit() else part.casefold()
        for part in re.split(r"(\d+)", str(path))
    ]


def read_text(path: Path) -> str:
    """Read common SRT encodings without changing the content."""
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"无法解码字幕文件: {path}")


def is_valid_srt(text: str) -> bool:
    """A usable SRT must contain at least one timestamp line and subtitle text."""
    if not text.strip():
        return False

    lines = text.splitlines()
    has_timestamp = any(TIMESTAMP_RE.match(line) for line in lines)
    if not has_timestamp:
        return False

    has_text = any(
        line.strip()
        and not line.strip().isdigit()
        and not TIMESTAMP_RE.match(line)
        for line in lines
    )
    return has_text


def discover_srt_files(case_dir: Path, output_name: str) -> Tuple[List[Path], List[Path]]:
    valid: List[Path] = []
    skipped: List[Path] = []

    for path in sorted(case_dir.rglob("*.srt"), key=lambda p: natural_key(p.relative_to(case_dir))):
        # Defensive: if the output name is ever changed to .srt, never ingest it.
        if path.resolve() == (case_dir / output_name).resolve():
            continue

        try:
            text = read_text(path)
        except (OSError, UnicodeError):
            skipped.append(path)
            continue

        if is_valid_srt(text):
            valid.append(path)
        else:
            skipped.append(path)

    return valid, skipped


def build_case_transcript(case_dir: Path, srt_files: List[Path]) -> str:
    parts = [
        f"# 案例素材母稿：{case_dir.name}",
        "",
        f"素材文件数：{len(srt_files)}",
        "说明：以下内容保留每个原 SRT 的原始编号、原始时间码与字幕文本；未重新编号。",
        "",
    ]

    for path in srt_files:
        relative = path.relative_to(case_dir)
        text = read_text(path).strip()
        parts.extend(
            [
                "=" * 80,
                f"【原文件名】{path.name}",
                f"【相对路径】{relative.as_posix()}",
                "=" * 80,
                "",
                text,
                "",
            ]
        )

    return "\n".join(parts).rstrip() + "\n"


def merge_case_folder(case_dir: Path, output_name: str = DEFAULT_OUTPUT_NAME) -> Path:
    case_dir = case_dir.expanduser().resolve()
    if not case_dir.exists():
        raise FileNotFoundError(f"案例素材文件夹不存在：{case_dir}")
    if not case_dir.is_dir():
        raise NotADirectoryError(f"输入路径不是文件夹：{case_dir}")

    valid, skipped = discover_srt_files(case_dir, output_name)
    if not valid:
        raise RuntimeError(f"没有找到有效的 SRT 文档：{case_dir}")

    output_path = case_dir / output_name
    output_path.write_text(build_case_transcript(case_dir, valid), encoding="utf-8")

    print(f"案例素材文件夹：{case_dir}")
    print(f"有效 SRT：{len(valid)}")
    print(f"跳过无效 SRT：{len(skipped)}")
    print(f"输出：{output_path}")

    if skipped:
        print("\n跳过：")
        for path in skipped:
            print(f"  - {path.relative_to(case_dir)}")

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="合并一个案例素材文件夹内的有效 SRT，保留原编号、原文件名和原时间码。"
    )
    parser.add_argument("case_folder", help="案例素材文件夹地址")
    parser.add_argument(
        "--output-name",
        default=DEFAULT_OUTPUT_NAME,
        help=f"输出文件名（默认：{DEFAULT_OUTPUT_NAME}）",
    )
    args = parser.parse_args()
    merge_case_folder(Path(args.case_folder), args.output_name)


if __name__ == "__main__":
    main()
