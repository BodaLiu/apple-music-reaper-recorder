#!/usr/bin/env python3
"""Find strict Folk tracks in Music.app that are absent from recorded playlists."""

from __future__ import annotations

import argparse
import csv
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


RS = chr(30)
FS = chr(31)
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT = SCRIPT_DIR / "folk_unrecorded_candidates.csv"
NEW_PLAYLIST = "Dataset_Folk_New_Strict_14"
REFERENCE_PLAYLISTS = ("Dataset_Acoustic_Folk", "Dataset_Folk_Clean_100")
SOURCE_PLAYLISTS = ("民謠代表作品", "英倫民謠代表作品", "獨立民謠")
STRICT_GENRES = {"Folk", "Traditional Folk", "Contemporary Folk", "Alternative Folk"}


APPLE_SCRIPT = r'''
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
        set sourcePlaylist to item 1 of matches
        set sourceTracks to every track of sourcePlaylist
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
    end tell
    return outputText
end run
'''

APPLE_SCRIPT_CREATE = r'''
on run argv
    set destinationName to item 1 of argv
    tell application "Music"
        if exists user playlist destinationName then error "目标歌单已经存在：" & destinationName
        set destinationPlaylist to make new user playlist with properties {name:destinationName, description:"严格Folk新增候选；排除旧200首和纯Folk 100首。"}
        repeat with argumentIndex from 2 to count of argv
            set rowText to item argumentIndex of argv
            set oldTIDs to AppleScript's text item delimiters
            set AppleScript's text item delimiters to character id 31
            set fields to text items of rowText
            set AppleScript's text item delimiters to oldTIDs
            set sourceName to item 1 of fields
            set sourceIndex to item 2 of fields as integer
            set matches to every playlist whose name is sourceName
            if (count of matches) is 0 then error "找不到来源歌单：" & sourceName
            set sourcePlaylist to item 1 of matches
            duplicate track sourceIndex of sourcePlaylist to destinationPlaylist
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


def read_playlist(name: str) -> list[Track]:
    result = subprocess.run(
        ["osascript", "-", name],
        input=APPLE_SCRIPT,
        text=True,
        capture_output=True,
        timeout=240,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"无法读取歌单：{name}")
    tracks: list[Track] = []
    for row in result.stdout.strip().split(RS):
        fields = row.split(FS)
        if len(fields) != 7:
            continue
        try:
            duration = float(fields[6])
        except ValueError:
            duration = 0.0
        tracks.append(Track(name, int(fields[0]), *fields[1:6], duration))
    return tracks


def create_playlist(candidates: list[Track]) -> None:
    args = ["osascript", "-", NEW_PLAYLIST]
    args.extend(f"{track.playlist}{FS}{track.index}" for track in candidates)
    result = subprocess.run(
        args,
        input=APPLE_SCRIPT_CREATE,
        text=True,
        capture_output=True,
        timeout=300,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "创建歌单失败")
    count = int(result.stdout.strip())
    if count != len(candidates):
        raise RuntimeError(f"创建数量异常：Music.app={count}，候选={len(candidates)}")
    print(f"已创建：{NEW_PLAYLIST}（{count}首）")


def main() -> int:
    parser = argparse.ArgumentParser(description="查找严格、未录过的Folk歌曲")
    parser.add_argument("--build", action="store_true", help="同时创建严格Folk新增歌单")
    args = parser.parse_args()
    references: list[Track] = []
    for name in REFERENCE_PLAYLISTS:
        tracks = read_playlist(name)
        print(f"排除歌单：{name}（{len(tracks)}首）", flush=True)
        references.extend(tracks)
    used_pids = {track.pid_key for track in references if track.pid_key}
    used_titles = {track.title_key for track in references}

    candidates: list[Track] = []
    seen_pids: set[str] = set()
    seen_titles: set[str] = set()
    for name in SOURCE_PLAYLISTS:
        tracks = read_playlist(name)
        accepted = 0
        for track in tracks:
            if track.genre not in STRICT_GENRES:
                continue
            if (track.pid_key and track.pid_key in used_pids) or track.title_key in used_titles:
                continue
            if (track.pid_key and track.pid_key in seen_pids) or track.title_key in seen_titles:
                continue
            candidates.append(track)
            if track.pid_key:
                seen_pids.add(track.pid_key)
            seen_titles.add(track.title_key)
            accepted += 1
        print(f"来源歌单：{name}（共{len(tracks)}首，严格未录候选{accepted}首）", flush=True)

    candidates.sort(key=lambda track: (track.playlist, track.index))
    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["source_playlist", "source_index", "persistent_id", "title", "artist", "album", "apple_genre", "duration_seconds"]
        )
        for track in candidates:
            writer.writerow(
                [track.playlist, track.index, track.pid, track.title, track.artist, track.album, track.genre, f"{track.duration:.3f}"]
            )
    print(f"\n严格、未录过、去重后的候选：{len(candidates)}首")
    print(f"标签分布：{dict(Counter(track.genre for track in candidates))}")
    print(f"候选清单：{OUTPUT}")
    if args.build:
        create_playlist(candidates)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
