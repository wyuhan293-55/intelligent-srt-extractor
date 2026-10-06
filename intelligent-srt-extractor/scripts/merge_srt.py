#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merge_srt.py — 将多个 SRT 字幕文件整合为一个总 SRT 文档（标准格式）

标准格式（用户确认，2026-10-05）：
  - 每个视频段开头单独一行标题：文件夹名-视频编号（如：术前采访-DE1A0870）
  - 各视频的字幕序号独立，从 1 重新开始编号（不要全局连续编号）
  - 时间帧保留各视频原始值（不做累计偏移，不改动）
  - 字幕原文原样保留，不加前缀、不插标记字幕条
  - 自动过滤 Whisper 幻觉/水印字幕（如"字幕by索兰娅""字幕製作人Zither Harp"）
  - 输出 UTF-8（带 BOM）+ CRLF 编码，用于案例素材检索（非单视频连续播放字幕）

用法一（推荐，显式顺序）：
  python scripts/merge_srt.py --out <输出.srt> <输入1.srt> <输入2.srt> ...

  - 输入文件按传入顺序排列（顺序由调用方按工作流/拍摄时间决定）
  - 段标题自动取「父文件夹名-文件名（去扩展名）」
  - 可选 --titles "标题1|标题2|..." 按顺序覆盖各段标题（| 分隔，数量须与输入一致），
    适用于嵌套子文件夹需要更完整标题时

用法二（自动扫描）：
  python scripts/merge_srt.py --folder <案例文件夹> [--name <姓名>]

  - 递归查找案例文件夹内所有有效 .srt（自动跳过已有的汇总文件）
  - 按自然排序合并；输出 <案例文件夹>/<姓名>-字幕汇总.srt（未指定姓名则为 字幕汇总.srt）
  - 注意：自动排序可能不符合工作流顺序，重要案例建议用用法一由 Agent 显式排序
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

# Whisper 幻觉/水印字幕（无实际内容），整条跳过
JUNK_RE = re.compile(r"字幕by.*|字幕製作人.*|索兰娅|ZitherHarp|滷汁|劇院|剧院", re.IGNORECASE)

TIMESTAMP_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
)

AGGREGATE_PATTERNS = ("字幕汇总", "案例素材母稿")


# ---------------------------------------------------------------- 时间工具

def to_ms(h: str, m: str, s: str, t: str) -> int:
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(t)



# ---------------------------------------------------------------- SRT 解析

def read_text(path: Path) -> str:
    """读取常见 SRT 编码，不改动内容。"""
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"无法解码字幕文件: {path}")


def parse_srt(path: Path) -> List[tuple]:
    """保留原始时间行与字幕文字；容忍 BOM/多余空行/序号缺失。"""
    raw = read_text(path).replace("\r\n", "\n").strip("\n")
    cues: List[tuple] = []
    for block in re.split(r"\n(?:[ \t]*\n)+", raw):
        if not block.strip():
            continue
        lines = block.split("\n")
        ti = 1 if lines[0].strip().isdigit() else 0
        m = TIMESTAMP_RE.fullmatch(lines[ti].strip()) if ti < len(lines) else None
        if m is None:
            raise ValueError("无效 SRT 字幕块：%s" % path)
        g = m.groups()
        start, end = to_ms(*g[:4]), to_ms(*g[4:])
        if any(int(g[i]) > 59 for i in (1, 2, 5, 6)) or end < start:
            raise ValueError("无效 SRT 时间帧：%s" % path)
        text = "\n".join(lines[ti + 1:])
        if text.strip():
            cues.append((lines[ti], text))
    return cues


def is_junk(text: str) -> bool:
    """只过滤整条水印/已知幻觉，不删除正常句子中出现的关键词。"""
    normalized = "".join(text.split()).strip("，。！？,.!?：:；;、")
    return JUNK_RE.fullmatch(normalized) is not None


def default_title(path: Path) -> str:
    """段标题 = 父文件夹名-文件名（去扩展名）。"""
    d = path.parent.name
    stem = path.stem
    return "%s-%s" % (d, stem) if d else stem


def natural_key(path: Path) -> list:
    """稳定自然排序：2.srt 排在 10.srt 之前。"""
    return [int(p) if p.isdigit() else p.casefold() for p in re.split(r"(\d+)", str(path))]


def is_aggregate(path: Path) -> bool:
    """识别已生成的汇总文件，避免二次合并时吃进自己。"""
    return any(pat in path.name for pat in AGGREGATE_PATTERNS)


# ---------------------------------------------------------------- 合并核心

def merge(out_path: Path, inputs: List[Path], title_overrides: dict) -> None:
    if any(path.resolve() == out_path.resolve() for path in inputs):
        raise ValueError("输出不能覆盖输入字幕：%s" % out_path)
    blocks: List[str] = []
    total = 0
    for idx, path in enumerate(inputs):
        if not path.is_file():
            raise FileNotFoundError("输入字幕不存在：%s" % path)
        if is_aggregate(path):
            print("SKIP %s：已有汇总文件" % path)
            continue
        title = title_overrides.get(idx) or default_title(path)
        if "\n" in title or "\r" in title:
            raise ValueError("段标题必须为单独一行：%s" % path)
        cues = parse_srt(path)
        kept = [c for c in cues if not is_junk(c[1])]
        dropped = len(cues) - len(kept)
        if not kept:
            print("SKIP %s：%s" % (path, "仅含幻觉/水印" if cues else "空字幕"))
            continue
        blocks.append(title)
        for n, (timestamp, text) in enumerate(kept, 1):
            blocks.append("%d\n%s\n%s" % (n, timestamp, text))
        total += len(kept)
        print("OK   %s title=%s cues=%d dropped=%d（幻觉/水印）" % (path, title, len(kept), dropped))
    if not total:
        raise RuntimeError("没有有效字幕，保留已有汇总文件")
    # 先完整生成，再原子覆盖；失败不损坏旧汇总，不留下备份文件。
    content = ("\n\n".join(blocks) + "\n").replace("\n", "\r\n")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8-sig", newline="",
                                         dir=out_path.parent, delete=False) as f:
            temp_path = Path(f.name)
            f.write(content)
        temp_path.replace(out_path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    print("---")
    print("total cues: %d" % total)
    print("output: %s (%d bytes)" % (out_path, os.path.getsize(out_path)))


def merge_folder(case_dir: Path, name: Optional[str]) -> Path:
    valid: List[Path] = []
    for path in sorted((p for p in case_dir.rglob("*") if p.is_file() and p.suffix.lower() == ".srt"),
                       key=natural_key):
        if is_aggregate(path):
            print("SKIP %s：已有汇总文件" % path)
            continue
        valid.append(path)
    if not valid:
        raise RuntimeError("没有找到有效的 SRT 文档：%s" % case_dir)

    out_path = case_dir / ("%s-字幕汇总.srt" % name if name else "字幕汇总.srt")
    if out_path.resolve().parent != case_dir.resolve():
        raise ValueError("姓名不能包含路径，输出必须在案例根目录")
    merge(out_path, valid, {})
    return out_path


# ---------------------------------------------------------------- CLI

def main() -> None:
    parser = argparse.ArgumentParser(
        description="按标准格式整合多个 SRT 为一个总文档：段标题=文件夹名-视频编号，"
                    "各段序号独立从 1 编号，保留原始时间戳，过滤幻觉水印。"
    )
    parser.add_argument("--out", help="输出 .srt 路径（显式顺序模式）")
    parser.add_argument("inputs", nargs="*", help="输入 .srt 文件，按目标顺序排列")
    parser.add_argument("--titles", default=None,
                        help="按顺序覆盖各段标题，用 | 分隔，数量须与输入文件数一致")
    parser.add_argument("--folder", help="案例素材文件夹（自动扫描模式）")
    parser.add_argument("--name", default=None, help="自动扫描模式下输出文件的人名（默认：字幕汇总）")
    args = parser.parse_args()

    if args.folder and (args.out or args.inputs or args.titles):
        parser.error("--folder 不能与 --out、输入文件列表或 --titles 混用")
    if args.name and not args.folder:
        parser.error("--name 仅用于 --folder 自动扫描模式")

    if args.folder:
        case_dir = Path(args.folder).expanduser().resolve()
        if not case_dir.is_dir():
            raise NotADirectoryError("输入路径不是文件夹：%s" % case_dir)
        merge_folder(case_dir, args.name)
        return

    if not args.out or not args.inputs:
        parser.error("需要 --out + 输入文件列表（显式顺序模式），或 --folder（自动扫描模式）")

    overrides: dict = {}
    if args.titles:
        titles = args.titles.split("|")
        if len(titles) != len(args.inputs):
            sys.exit("--titles 数量(%d)与输入文件数(%d)不一致" % (len(titles), len(args.inputs)))
        overrides = dict(enumerate(titles))

    merge(Path(args.out).expanduser().resolve(),
          [Path(p).expanduser().resolve() for p in args.inputs], overrides)


if __name__ == "__main__":
    main()
