#!/usr/bin/env python3
"""Build a fixed, genre-balanced Apple Music Atmos playlist snapshot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


RS = chr(30)
FS = chr(31)
SCRIPT_DIR = Path(__file__).resolve().parent
PLAN_PATH = SCRIPT_DIR / "atmos_playlist_plan.json"
OUTPUT_DIR = SCRIPT_DIR / "atmos_balanced_100_build"
TARGET_PLAYLIST = "Dataset_Atmos_Balanced_100"
SEED = "atmos-balanced-20260831"
EXCLUDED_TRACK_KEYS = {
    "ramones\x1fblitzkrieg bop",
    "future\x1fkonnichiwa",
    "maribou state & holly walker\x1fotherside",
    "art blakey & the jazz messengers\x1fhipsippy blues",
    "孫燕姿\x1f克卜勒",
    "白安\x1f路邊野餐",
}


APPLE_SCRIPT_READ = r'''
on cleanText(valueText)
    set oldTIDs to AppleScript's text item delimiters
    set AppleScript's text item delimiters to character id 30
    set valueText to text items of valueText as text
    set AppleScript's text item delimiters to character id 31
    set valueText to text items of valueText as text
    set AppleScript's text item delimiters to oldTIDs
    return valueText
end cleanText
on run argv
    set playlistName to item 1 of argv
    tell application "Music"
        set matches to every playlist whose name is playlistName
        if (count of matches) is 0 then error "找不到播放列表：" & playlistName
        set sourceTracks to every track of item 1 of matches
        set outputText to ""
        repeat with trackIndex from 1 to count of sourceTracks
            set musicTrack to item trackIndex of sourceTracks
            try
                set pidText to persistent ID of musicTrack as text
            on error
                set pidText to ""
            end try
            try
                set titleText to name of musicTrack as text
            on error
                set titleText to ""
            end try
            try
                set artistText to artist of musicTrack as text
            on error
                set artistText to ""
            end try
            try
                set albumText to album of musicTrack as text
            on error
                set albumText to ""
            end try
            try
                set genreText to genre of musicTrack as text
            on error
                set genreText to ""
            end try
            try
                set durationText to duration of musicTrack as text
            on error
                set durationText to "0"
            end try
            set fields to {trackIndex as text, my cleanText(pidText), my cleanText(titleText), my cleanText(artistText), my cleanText(albumText), my cleanText(genreText), durationText}
            set oldTIDs to AppleScript's text item delimiters
            set AppleScript's text item delimiters to character id 31
            set rowText to fields as text
            set AppleScript's text item delimiters to oldTIDs
            if outputText is not "" then set outputText to outputText & character id 30
            set outputText to outputText & rowText
        end repeat
        return outputText
    end tell
end run
'''


APPLE_SCRIPT_CREATE = r'''
on run argv
    set destinationName to item 1 of argv
    tell application "Music"
        if exists user playlist destinationName then error "目标歌单已经存在：" & destinationName
        set destinationPlaylist to make new user playlist with properties {name:destinationName, description:"100首固定Dolby Atmos候选；10类各10首；用于Atmos开/关配对录制。"}
        repeat with argumentIndex from 2 to count of argv
            set oldTIDs to AppleScript's text item delimiters
            set AppleScript's text item delimiters to character id 31
            set fields to text items of (item argumentIndex of argv)
            set AppleScript's text item delimiters to oldTIDs
            set sourceName to item 1 of fields
            set sourceIndex to item 2 of fields as integer
            set sourceMatches to every playlist whose name is sourceName
            if (count of sourceMatches) is 0 then error "找不到来源歌单：" & sourceName
            duplicate track sourceIndex of item 1 of sourceMatches to destinationPlaylist
        end repeat
        return count every track of destinationPlaylist
    end tell
end run
'''


@dataclass(frozen=True)
class Track:
    label: str
    playlist: str
    index: int
    pid: str
    title: str
    artist: str
    album: str
    genre: str
    duration: float

    @property
    def pid_key(self) -> str:
        return self.pid.strip().casefold()

    @property
    def title_key(self) -> str:
        return f"{self.artist.strip().casefold()}\x1f{self.title.strip().casefold()}"

    @property
    def artist_key(self) -> str:
        return self.artist.strip().casefold() or "unknown artist"


def read_playlist(label: str, name: str) -> list[Track]:
    result = subprocess.run(
        ["osascript", "-", name], input=APPLE_SCRIPT_READ, text=True,
        capture_output=True, timeout=600,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"无法读取歌单：{name}")
    tracks: list[Track] = []
    for row in result.stdout.strip().split(RS):
        fields = row.split(FS)
        if len(fields) != 7:
            continue
        try:
            tracks.append(Track(label, name, int(fields[0]), *fields[1:6], float(fields[6])))
        except ValueError:
            continue
    return tracks


def hash_key(track: Track) -> str:
    identity = track.pid_key or track.title_key
    return hashlib.sha256(f"{SEED}|{track.label}|{identity}".encode()).hexdigest()


def select_tracks() -> tuple[list[Track], dict[str, int]]:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    rules = plan["selection_rules"]
    markers = tuple(value.casefold() for value in rules["exclude_title_markers"])
    minimum = float(rules["minimum_duration_seconds"])
    maximum = float(rules["maximum_duration_seconds"])
    artist_limit = int(rules["maximum_tracks_per_artist"])
    selected: list[Track] = []
    seen_pids: set[str] = set()
    seen_titles: set[str] = set()
    artist_counts: Counter[str] = Counter()
    counts: dict[str, int] = {}

    for source in plan["sources"]:
        label = source["label"]
        name = source["name"]
        quota = int(source["quota"])
        tracks = read_playlist(label, name)
        print(f"读取：{label} / {name}（{len(tracks)}首）", flush=True)
        chosen: list[Track] = []
        for track in sorted(tracks, key=hash_key):
            title_folded = track.title.casefold()
            if not track.title.strip() or not track.artist.strip():
                continue
            if track.duration < minimum or track.duration > maximum:
                continue
            if any(marker in title_folded for marker in markers):
                continue
            if track.title_key in EXCLUDED_TRACK_KEYS:
                continue
            if track.album and "soundtrack" in track.album.casefold():
                continue
            if track.pid_key and track.pid_key in seen_pids:
                continue
            if track.title_key in seen_titles:
                continue
            if artist_counts[track.artist_key] >= artist_limit:
                continue
            chosen.append(track)
            if track.pid_key:
                seen_pids.add(track.pid_key)
            seen_titles.add(track.title_key)
            artist_counts[track.artist_key] += 1
            if len(chosen) == quota:
                break
        if len(chosen) != quota:
            raise RuntimeError(f"{label}只能选出{len(chosen)}首，目标{quota}首")
        selected.extend(chosen)
        counts[label] = len(chosen)

    if len(selected) != 100:
        raise RuntimeError(f"最终数量异常：{len(selected)}，预期100")
    return selected, counts


def write_manifest(tracks: list[Track]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUTPUT_DIR / "final_100.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["dataset_index", "category", "source_playlist", "source_index", "persistent_id", "title", "artist", "album", "apple_genre", "duration_seconds"])
        for index, track in enumerate(tracks, 1):
            writer.writerow([index, track.label, track.playlist, track.index, track.pid, track.title, track.artist, track.album, track.genre, f"{track.duration:.3f}"])


def playlist_count(name: str) -> int | None:
    script = f'tell application "Music" to if exists user playlist "{name}" then return count every track of user playlist "{name}"'
    result = subprocess.run(["osascript", "-e", script], text=True, capture_output=True)
    if result.returncode or not result.stdout.strip():
        return None
    return int(result.stdout.strip())


def create_playlist(tracks: list[Track]) -> None:
    args = ["osascript", "-", TARGET_PLAYLIST]
    args.extend(f"{track.playlist}{FS}{track.index}" for track in tracks)
    result = subprocess.run(args, input=APPLE_SCRIPT_CREATE, text=True, capture_output=True, timeout=1200)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "创建Atmos歌单失败")
    count = int(result.stdout.strip())
    if count != len(tracks):
        raise RuntimeError(f"目标歌单数量异常：{count}，预期{len(tracks)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("check", "build"))
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    tracks, counts = select_tracks()
    write_manifest(tracks)
    print(f"候选清单：{OUTPUT_DIR / 'final_100.csv'}", flush=True)
    print(f"类别：{counts}；艺人数：{len(set(t.artist_key for t in tracks))}", flush=True)
    if args.command == "check":
        return 0
    existing = playlist_count(TARGET_PLAYLIST)
    if existing is not None:
        raise RuntimeError(f"{TARGET_PLAYLIST}已存在（{existing}首），未覆盖")
    if not args.yes and input("输入 BUILD 创建Atmos歌单：").strip() != "BUILD":
        return 1
    create_playlist(tracks)
    result = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "playlist_name": TARGET_PLAYLIST,
        "total": len(tracks),
        "category_counts": counts,
        "artist_count": len(set(t.artist_key for t in tracks)),
        "note": "All sources are Apple Music editorial Spatial Audio playlists; per-track Atmos playback must still be spot-checked before recording."
    }
    (OUTPUT_DIR / "build_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"完成：{TARGET_PLAYLIST}（{len(tracks)}首）", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
