#!/usr/bin/env python3
"""Run the REAPER recorder across all Dataset_* playlists by category."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable


class RunnerError(RuntimeError):
    pass


def load_result(path: Path) -> dict:
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunnerError(f"无法读取 build_result.json：{exc}") from exc
    categories = result.get("categories", [])
    if not categories:
        raise RunnerError("build_result.json 中没有类别。")
    return result


def merge_metadata(dataset_root: Path, categories: list[dict]) -> Path:
    all_rows: list[dict[str, str]] = []
    field_order: list[str] = ["dataset_label"]
    for category in categories:
        metadata_path = dataset_root / category["label"] / "metadata.csv"
        if not metadata_path.exists():
            continue
        with metadata_path.open("r", newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                merged = {"dataset_label": category["label"], **row}
                all_rows.append(merged)
                for key in merged:
                    if key not in field_order:
                        field_order.append(key)
    output = dataset_root / "recording_manifest.csv"
    if all_rows:
        with output.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=field_order)
            writer.writeheader()
            writer.writerows(all_rows)
    return output


def build_parser() -> argparse.ArgumentParser:
    default_recorder = (
        Path(__file__).resolve().parent.parent
        / "apple_music_reaper_recorder"
        / "apple_music_reaper_recorder.py"
    )
    parser = argparse.ArgumentParser(description="按配置类别依次录制Apple Music数据集")
    parser.add_argument("--build-result", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument(
        "--recording-dir",
        type=Path,
        help="REAPER固定录音暂存目录；默认 DATASET_ROOT/_REAPER_STAGING",
    )
    parser.add_argument("--recorder", type=Path, default=default_recorder)
    parser.add_argument("--reaper-url", default="http://127.0.0.1:8080")
    parser.add_argument("--reaper-user", default="")
    parser.add_argument("--reaper-password", default="")
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument(
        "--limit-per-category",
        type=int,
        default=0,
        help="每类最多录几首；0表示录完。试跑建议10",
    )
    parser.add_argument("--category", default="", help="只处理指定类别")
    parser.add_argument("--start-category", default="", help="从指定类别开始")
    parser.add_argument("--check", action="store_true", help="只检查全部歌单和REAPER连接")
    parser.add_argument("--keep-reaper-filenames", action="store_true")
    parser.add_argument("--yes", action="store_true", help="跳过总确认")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result_path = args.build_result.expanduser().resolve()
        dataset_root = args.dataset_root.expanduser().resolve()
        recording_dir = (
            args.recording_dir.expanduser().resolve()
            if args.recording_dir
            else dataset_root / "_REAPER_STAGING"
        )
        recorder = args.recorder.expanduser().resolve()
        if not recorder.exists():
            raise RunnerError(f"找不到录音脚本：{recorder}")
        if args.limit_per_category < 0 or args.retries < 0:
            raise RunnerError("数量参数不能为负数。")
        if args.category and args.start_category:
            raise RunnerError("--category 和 --start-category 不能同时使用。")

        result = load_result(result_path)
        all_categories = result["categories"]
        categories = all_categories
        if args.category:
            matches = [
                category
                for category in categories
                if category["label"].casefold() == args.category.casefold()
            ]
            if not matches:
                valid = ", ".join(c["label"] for c in categories)
                raise RunnerError(f"未知类别；可用值：{valid}")
            categories = matches
        elif args.start_category:
            indices = [
                i
                for i, category in enumerate(categories)
                if category["label"].casefold() == args.start_category.casefold()
            ]
            if not indices:
                valid = ", ".join(c["label"] for c in categories)
                raise RunnerError(f"未知类别；可用值：{valid}")
            categories = categories[indices[0] :]

        short = [
            category
            for category in categories
            if int(category.get("created_count", 0)) < int(category.get("target_count", 200))
        ]
        if short and not args.check:
            names = ", ".join(f"{c['label']}={c.get('created_count', 0)}" for c in short)
            raise RunnerError(f"以下目标歌单不足200首：{names}。请先修复建库结果。")

        dataset_root.mkdir(parents=True, exist_ok=True)
        recording_dir.mkdir(parents=True, exist_ok=True)
        if not args.check and not args.yes:
            print(f"REAPER固定录音目录：{recording_dir}")
            print("本次将依次处理：")
            for category in categories:
                suffix = (
                    f"前 {args.limit_per_category} 首"
                    if args.limit_per_category
                    else f"全部 {category.get('created_count', 200)} 首"
                )
                print(f"  {category['label']}: {category['playlist_name']}（{suffix}）")
            answer = input("输入 RECORD_ALL 开始：").strip()
            if answer != "RECORD_ALL":
                raise RunnerError("用户取消。")

        failures: list[tuple[str, int]] = []
        for ordinal, category in enumerate(categories, start=1):
            label = category["label"]
            output_dir = dataset_root / label
            output_dir.mkdir(parents=True, exist_ok=True)
            command = [
                sys.executable,
                str(recorder),
                "--playlist",
                category["playlist_name"],
                "--output",
                str(output_dir),
                "--recording-dir",
                str(recording_dir),
                "--reaper-url",
                args.reaper_url,
                "--retries",
                str(args.retries),
            ]
            if args.reaper_user:
                command.extend(["--reaper-user", args.reaper_user])
            if args.reaper_password:
                command.extend(["--reaper-password", args.reaper_password])
            if args.limit_per_category:
                command.extend(["--limit", str(args.limit_per_category)])
            if args.keep_reaper_filenames:
                command.append("--keep-reaper-filenames")
            if args.check:
                command.append("--check")
            else:
                command.append("--yes")

            print(f"\n===== [{ordinal}/{len(categories)}] {label} =====")
            completed = subprocess.run(command, check=False)
            if completed.returncode != 0:
                failures.append((label, completed.returncode))

        # Single-category runs must not overwrite the root manifest with only
        # the category processed in this invocation. Rebuild it from every
        # category metadata file currently present under the dataset root.
        manifest_path = merge_metadata(dataset_root, all_categories)
        if manifest_path.exists():
            print(f"\n合并录音清单：{manifest_path}")
        if failures:
            details = ", ".join(f"{label}(code={code})" for label, code in failures)
            print(f"存在未完全成功的类别：{details}", file=sys.stderr)
            return 2
        print("\n全部类别处理完成。")
        return 0
    except RunnerError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已中断。当前子录音脚本会尝试停止Music.app与REAPER。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
