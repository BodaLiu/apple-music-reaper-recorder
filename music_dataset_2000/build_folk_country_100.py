#!/usr/bin/env python3
"""Build 100 new Folk/Country/Roots tracks, excluding all existing datasets."""

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
OUTPUT_DIR = SCRIPT_DIR / "folk_country_100_build"
TARGET_PLAYLIST = "Dataset_Folk_Country_New_100"
BASE_PLAYLIST = "Dataset_Folk_New_Strict_14"
REFERENCE_PLAYLISTS = (
    "Dataset_Pop",
    "Dataset_Rock",
    "Dataset_Classical",
    "Dataset_Jazz",
    "Dataset_EDM_Electronic",
    "Dataset_HipHop_Rap",
    "Dataset_RNB_Soul",
    "Dataset_Latin",
    "Dataset_Acoustic_Folk",
    "Dataset_Folk_Clean_100",
)
SOURCE_QUOTAS = {
    "Americana 代表作品": 40,
    "70 年代鄉村樂代表作品": 30,
    "輕鬆鄉村樂": 16,
}
COUNTRY_ROADS_SOURCE = "70 年代鄉村樂代表作品"
COUNTRY_ROADS_INDEX = 8
SEED = "folk-country-20260827"


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
        set destinationPlaylist to make new user playlist with properties {name:destinationName, description:"100首全新Folk/Country/Roots；排除全部既有Dataset歌单。"}
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


def read_playlist(name: str) -> list[Track]:
    result = subprocess.run(
        ["osascript", "-", name], input=APPLE_SCRIPT_READ, text=True,
        capture_output=True, timeout=300,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"无法读取歌单：{name}")
    output: list[Track] = []
    for row in result.stdout.strip().split(RS):
        fields = row.split(FS)
        if len(fields) != 7:
            continue
        try:
            output.append(Track(name, int(fields[0]), *fields[1:6], float(fields[6])))
        except ValueError:
            continue
    return output


def hash_key(track: Track) -> str:
    identity = track.pid_key or track.title_key
    return hashlib.sha256(f"{SEED}|{identity}".encode()).hexdigest()


def select_tracks() -> tuple[list[Track], list[Track], dict[str, int]]:
    used_pids: set[str] = set()
    used_titles: set[str] = set()
    for name in REFERENCE_PLAYLISTS:
        tracks = read_playlist(name)
        print(f"排除：{name}（{len(tracks)}首）", flush=True)
        used_pids.update(track.pid_key for track in tracks if track.pid_key)
        used_titles.update(track.title_key for track in tracks)

    base = read_playlist(BASE_PLAYLIST)
    if len(base) != 14:
        raise RuntimeError(f"{BASE_PLAYLIST} 应为14首，实际{len(base)}首")
    selected = list(base)
    seen_pids = {track.pid_key for track in base if track.pid_key}
    seen_titles = {track.title_key for track in base}
    artist_counts = Counter(track.artist_key for track in base)

    source_tracks = {name: read_playlist(name) for name in SOURCE_QUOTAS}
    country_roads = source_tracks[COUNTRY_ROADS_SOURCE][COUNTRY_ROADS_INDEX - 1]
    if "country roads" not in country_roads.title.casefold() or "john denver" not in country_roads.artist.casefold():
        raise RuntimeError("70年代乡村歌单第8首不再是 John Denver - Country Roads")

    country_selected: list[Track] = [country_roads]
    seen_pids.add(country_roads.pid_key)
    seen_titles.add(country_roads.title_key)
    artist_counts[country_roads.artist_key] += 1
    actual_quotas = {name: 0 for name in SOURCE_QUOTAS}
    actual_quotas[COUNTRY_ROADS_SOURCE] = 1

    for source_name, quota in SOURCE_QUOTAS.items():
        pool = sorted(source_tracks[source_name], key=hash_key)
        for track in pool:
            if actual_quotas[source_name] >= quota:
                break
            if track.title_key == country_roads.title_key:
                continue
            if not track.title.strip() or track.duration < 60 or track.duration > 900:
                continue
            if (track.pid_key and track.pid_key in used_pids) or track.title_key in used_titles:
                continue
            if (track.pid_key and track.pid_key in seen_pids) or track.title_key in seen_titles:
                continue
            if artist_counts[track.artist_key] >= 2:
                continue
            country_selected.append(track)
            actual_quotas[source_name] += 1
            if track.pid_key:
                seen_pids.add(track.pid_key)
            seen_titles.add(track.title_key)
            artist_counts[track.artist_key] += 1
        if actual_quotas[source_name] != quota:
            raise RuntimeError(
                f"{source_name} 只能选出{actual_quotas[source_name]}首，目标{quota}首"
            )

    if len(country_selected) != 86:
        raise RuntimeError(f"Country/Americana应选86首，实际{len(country_selected)}首")
    return base, country_selected, actual_quotas


def write_csv(path: Path, tracks: list[Track]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["dataset_index", "source_playlist", "source_index", "persistent_id", "title", "artist", "album", "apple_genre", "duration_seconds"])
        for index, track in enumerate(tracks, 1):
            writer.writerow([index, track.playlist, track.index, track.pid, track.title, track.artist, track.album, track.genre, f"{track.duration:.3f}"])


def playlist_exists(name: str) -> int | None:
    script = 'tell application "Music" to if exists user playlist "' + name + '" then return count every track of user playlist "' + name + '"'
    result = subprocess.run(["osascript", "-e", script], text=True, capture_output=True)
    if result.returncode or not result.stdout.strip():
        return None
    return int(result.stdout.strip())


def create_playlist(tracks: list[Track]) -> None:
    args = ["osascript", "-", TARGET_PLAYLIST]
    args.extend(f"{track.playlist}{FS}{track.index}" for track in tracks)
    result = subprocess.run(args, input=APPLE_SCRIPT_CREATE, text=True, capture_output=True, timeout=600)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "创建目标歌单失败")
    count = int(result.stdout.strip())
    if count != len(tracks):
        raise RuntimeError(f"目标歌单数量异常：{count}，预期{len(tracks)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="构建100首全新Folk/Country/Roots歌单")
    parser.add_argument("command", choices=("check", "build"))
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    base, country, quotas = select_tracks()
    final = base + country
    print(f"\n保留严格Folk：{len(base)}首")
    print(f"新增Country/Americana：{len(country)}首（含Country Roads）")
    print(f"来源配额：{quotas}")
    print(f"最终：{len(final)}首；艺人数：{len(set(track.artist_key for track in final))}")
    if args.command == "check":
        return 0
    existing = playlist_exists(TARGET_PLAYLIST)
    if existing is not None:
        raise RuntimeError(f"{TARGET_PLAYLIST} 已存在（{existing}首），未覆盖")
    if not args.yes and input("输入 BUILD 创建最终歌单：").strip() != "BUILD":
        return 1
    create_playlist(final)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT_DIR / "strict_folk_14.csv", base)
    write_csv(OUTPUT_DIR / "new_country_americana_86.csv", country)
    write_csv(OUTPUT_DIR / "final_100.csv", final)
    result = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "playlist_name": TARGET_PLAYLIST,
        "total": len(final),
        "strict_folk": len(base),
        "country_americana": len(country),
        "source_quotas": quotas,
    }
    (OUTPUT_DIR / "build_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"完成：{TARGET_PLAYLIST}（{len(final)}首）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
