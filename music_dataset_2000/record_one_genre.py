#!/usr/bin/env python3
"""Record one configured dataset genre through the existing dataset runner."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import record_dataset


# 常用设置：以后逐类录制时，通常只需修改 DEFAULT_GENRE。
DEFAULT_GENRE = "Rock"
DEFAULT_DATASET_ROOT = Path.home() / "MusicGenreDataset"
DEFAULT_RECORDING_DIR = DEFAULT_DATASET_ROOT / "_REAPER_STAGING"
DEFAULT_BUILD_RESULT = Path(__file__).resolve().parent / "dataset_build/build_result.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="一次只录制一个音乐风格类别")
    parser.add_argument("--genre", default=DEFAULT_GENRE, help="要录制的类别，默认 Rock")
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=DEFAULT_DATASET_ROOT,
        help=f"最终数据集目录，默认 {DEFAULT_DATASET_ROOT}",
    )
    parser.add_argument(
        "--recording-dir",
        type=Path,
        default=DEFAULT_RECORDING_DIR,
        help=f"REAPER暂存目录，默认 {DEFAULT_RECORDING_DIR}",
    )
    parser.add_argument(
        "--build-result",
        type=Path,
        default=DEFAULT_BUILD_RESULT,
        help="build_result.json路径；默认使用脚本旁的dataset_build",
    )
    parser.add_argument("--limit", type=int, default=0, help="最多录几首；0表示录完整类")
    parser.add_argument("--check", action="store_true", help="只检查连接和播放列表")
    parser.add_argument("--yes", action="store_true", help="跳过开始前确认")
    parser.add_argument("--retries", type=int, default=1, help="每首失败后的额外重试次数")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    forwarded = [
        "--build-result",
        str(args.build_result),
        "--dataset-root",
        str(args.dataset_root),
        "--recording-dir",
        str(args.recording_dir),
        "--category",
        args.genre,
        "--retries",
        str(args.retries),
    ]
    if args.limit:
        forwarded.extend(["--limit-per-category", str(args.limit)])
    if args.check:
        forwarded.append("--check")
    if args.yes:
        forwarded.append("--yes")
    return record_dataset.main(forwarded)


if __name__ == "__main__":
    raise SystemExit(main())
