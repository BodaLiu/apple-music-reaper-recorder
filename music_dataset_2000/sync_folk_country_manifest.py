#!/usr/bin/env python3
"""Synchronize the local Folk/Country manifest with the current Music playlist."""

from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from build_folk_country_100 import Track, read_playlist


SCRIPT_DIR = Path(__file__).resolve().parent
BUILD_DIR = SCRIPT_DIR / "folk_country_100_build"
PLAYLIST = "Dataset_Folk_Country_New_100"
MANIFEST = BUILD_DIR / "final_100.csv"
BACKUP = BUILD_DIR / "final_100_before_llewyn_and_cleanup.csv"
REMOVED = BUILD_DIR / "removed_rock_soul_3.csv"
ADDED = BUILD_DIR / "added_inside_llewyn_davis_3.csv"
RESULT = BUILD_DIR / "build_result.json"
REMOVED_IDS = {"BDC70BF8399510AD", "89476EBCD23B7930", "12572F7EA37FA0EC"}
OST_ALBUM = "Inside Llewyn Davis (Original Soundtrack Recording)"
FIELDS = [
    "dataset_index", "source_playlist", "source_index", "persistent_id",
    "title", "artist", "album", "apple_genre", "duration_seconds",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def track_row(index: int, track: Track, provenance: dict[str, str] | None) -> dict[str, object]:
    source_playlist = provenance["source_playlist"] if provenance else f"{OST_ALBUM} (Library)"
    source_index = provenance["source_index"] if provenance else ""
    return {
        "dataset_index": index,
        "source_playlist": source_playlist,
        "source_index": source_index,
        "persistent_id": track.pid,
        "title": track.title,
        "artist": track.artist,
        "album": track.album,
        "apple_genre": track.genre,
        "duration_seconds": f"{track.duration:.3f}",
    }


def main() -> int:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    if not BACKUP.exists():
        shutil.copy2(MANIFEST, BACKUP)
    original = read_csv(BACKUP)
    original_by_pid = {row["persistent_id"].casefold(): row for row in original}

    tracks = read_playlist(PLAYLIST)
    if len(tracks) != 100:
        raise RuntimeError(f"目标歌单应为100首，实际{len(tracks)}首")
    current_ids = {track.pid.casefold() for track in tracks}
    if current_ids & {pid.casefold() for pid in REMOVED_IDS}:
        raise RuntimeError("三首待移除歌曲仍存在于目标歌单")

    ost_tracks = [track for track in tracks if track.album == OST_ALBUM]
    expected_ost_titles = {
        "Green, Green Rocky Road",
        "Fare Thee Well (Dink's Song)",
        "The Last Thing on My Mind (with Punch Brothers)",
    }
    if {track.title for track in ost_tracks} != expected_ost_titles:
        raise RuntimeError("Inside Llewyn Davis 三首曲目与预期不一致")

    final_rows = [
        track_row(index, track, original_by_pid.get(track.pid.casefold()))
        for index, track in enumerate(tracks, 1)
    ]
    removed_rows = [row for row in original if row["persistent_id"].casefold() in {pid.casefold() for pid in REMOVED_IDS}]
    added_rows = [row for row in final_rows if row["album"] == OST_ALBUM]
    if len(removed_rows) != 3 or len(added_rows) != 3:
        raise RuntimeError(f"本地差异数量异常：移除{len(removed_rows)}，新增{len(added_rows)}")

    write_csv(MANIFEST, final_rows)
    write_csv(REMOVED, removed_rows)
    write_csv(ADDED, added_rows)

    result = json.loads(RESULT.read_text(encoding="utf-8")) if RESULT.exists() else {}
    result.update({
        "playlist_name": PLAYLIST,
        "current_total": 100,
        "manifest_synced_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "manual_removed_count": 3,
        "manual_added_inside_llewyn_davis_count": 3,
    })
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已同步：{MANIFEST}")
    print("当前100首 = 原清单97首 + Inside Llewyn Davis 3首")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
