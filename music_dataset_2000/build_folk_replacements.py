#!/usr/bin/env python3
"""Create a replacement-only Folk playlist without re-recording overlaps."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import build_dataset_playlists as builder


SCRIPT_DIR = Path(__file__).resolve().parent
OLD_MANIFEST = SCRIPT_DIR / "dataset_build" / "dataset_manifest.csv"
CLEAN_MANIFEST = SCRIPT_DIR / "folk_clean_build" / "dataset_manifest.csv"
OUTPUT_DIR = SCRIPT_DIR / "folk_replacement_build"
PLAYLIST_NAME = "Dataset_Folk_Replacement_67"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else builder.MANIFEST_FIELDS
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def split_rows() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    old = [
        row
        for row in read_rows(OLD_MANIFEST)
        if row["dataset_label"] == "Acoustic_Folk"
    ]
    clean = read_rows(CLEAN_MANIFEST)
    old_ids = {row["persistent_id"].strip().casefold() for row in old}
    reused = [row for row in clean if row["persistent_id"].strip().casefold() in old_ids]
    new = [row for row in clean if row["persistent_id"].strip().casefold() not in old_ids]
    if len(old) != 200 or len(clean) != 100 or len(reused) != 33 or len(new) != 67:
        raise RuntimeError(
            f"清单数量异常：旧Folk={len(old)}，纯Folk={len(clean)}，复用={len(reused)}，新录={len(new)}"
        )
    return reused, new


def to_candidate(row: dict[str, str]) -> builder.Candidate:
    return builder.Candidate(
        label="Folk_Clean",
        source_playlist=row["source_playlist"],
        source_index=int(row["source_index"]),
        persistent_id=row["persistent_id"],
        title=row["title"],
        artist=row["artist"],
        album=row["album"],
        apple_genre=row["apple_genre"],
        duration_seconds=float(row["duration_seconds"]),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="创建只需新录的67首纯Folk替换歌单")
    parser.add_argument("command", choices=("check", "build"))
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()

    reused, new = split_rows()
    print(f"最终纯Folk：100首；复用旧录音：{len(reused)}首；需要新录：{len(new)}首")
    if args.command == "check":
        return 0

    playlists = builder.list_local_playlists()
    existing = next((p for p in playlists if p.name == PLAYLIST_NAME), None)
    if existing:
        if existing.track_count != len(new):
            raise RuntimeError(f"已有 {PLAYLIST_NAME}，但曲目数为{existing.track_count}，预期67")
        print(f"歌单已存在且数量正确：{PLAYLIST_NAME}（67首）")
        return 0

    if not args.yes:
        answer = input(f"输入 BUILD 创建 {PLAYLIST_NAME}：").strip()
        if answer != "BUILD":
            print("已取消。")
            return 1

    candidates = [to_candidate(row) for row in new]
    succeeded, failed = builder.create_playlist(
        PLAYLIST_NAME,
        "纯Folk替换曲目：复用旧录音33首，仅新录本歌单67首。",
        candidates,
        len(candidates),
    )
    if failed or len(succeeded) != len(candidates):
        raise RuntimeError(f"创建未完成：成功{len(succeeded)}首，失败{len(failed)}首")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_rows(OUTPUT_DIR / "reused_old_33.csv", reused)
    replacement_rows = builder.make_manifest_rows("Folk_Clean", PLAYLIST_NAME, succeeded)
    write_rows(OUTPUT_DIR / "record_new_67.csv", replacement_rows)
    result = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "playlist_name": PLAYLIST_NAME,
        "final_clean_count": 100,
        "reused_old_count": len(reused),
        "record_new_count": len(succeeded),
    }
    (OUTPUT_DIR / "build_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"完成：{PLAYLIST_NAME} 共{len(succeeded)}首，只录这些新曲。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
