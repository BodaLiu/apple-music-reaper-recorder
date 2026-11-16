#!/usr/bin/env python3
"""Record an Apple Music playlist into one REAPER WAV file per track.

Designed for macOS + Music.app + BlackHole + REAPER.  The script controls
Music.app through AppleScript and REAPER through its local Web interface.
It uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


FIELD_SEPARATOR = chr(31)
SUPPORTED_AUDIO_SUFFIXES = {".wav", ".wave", ".w64"}
REAPER_RECORD_ACTION = 1013
REAPER_STOP_ACTION = 1016


APPLE_SCRIPT_PLAYLIST_COUNT = r'''
on run argv
    set playlistName to item 1 of argv
    tell application "Music"
        set matches to every user playlist whose name is playlistName
        if (count of matches) is 0 then error "找不到播放列表：" & playlistName
        set p to item 1 of matches
        return (count of tracks of p) as text
    end tell
end run
'''


APPLE_SCRIPT_TRACK_INFO = r'''
on safeText(v)
    try
        if v is missing value then return ""
        return v as text
    on error
        return ""
    end try
end safeText

on run argv
    set playlistName to item 1 of argv
    set trackIndex to (item 2 of argv) as integer
    tell application "Music"
        set matches to every user playlist whose name is playlistName
        if (count of matches) is 0 then error "找不到播放列表：" & playlistName
        set p to item 1 of matches
        if trackIndex < 1 or trackIndex > (count of tracks of p) then error "曲目序号越界"
        set t to track trackIndex of p

        set trackName to ""
        set artistName to ""
        set albumName to ""
        set albumArtistName to ""
        set genreName to ""
        set trackDuration to ""
        set trackYear to ""
        set trackNumberValue to ""
        set discNumberValue to ""
        set trackID to ""

        try
            set trackName to my safeText(name of t)
        end try
        try
            set artistName to my safeText(artist of t)
        end try
        try
            set albumName to my safeText(album of t)
        end try
        try
            set albumArtistName to my safeText(album artist of t)
        end try
        try
            set genreName to my safeText(genre of t)
        end try
        try
            set trackDuration to my safeText(duration of t)
        end try
        try
            set trackYear to my safeText(year of t)
        end try
        try
            set trackNumberValue to my safeText(track number of t)
        end try
        try
            set discNumberValue to my safeText(disc number of t)
        end try
        try
            set trackID to my safeText(persistent ID of t)
        end try
    end tell

    set oldDelimiters to AppleScript's text item delimiters
    set AppleScript's text item delimiters to ASCII character 31
    set resultText to {trackName, artistName, albumName, albumArtistName, genreName, trackDuration, trackYear, trackNumberValue, discNumberValue, trackID} as text
    set AppleScript's text item delimiters to oldDelimiters
    return resultText
end run
'''


APPLE_SCRIPT_PLAY_ONCE = r'''
on run argv
    set playlistName to item 1 of argv
    set trackIndex to (item 2 of argv) as integer
    tell application "Music"
        set matches to every user playlist whose name is playlistName
        if (count of matches) is 0 then error "找不到播放列表：" & playlistName
        set p to item 1 of matches
        set t to track trackIndex of p
        stop
        play t with once
    end tell
end run
'''


APPLE_SCRIPT_PLAYER_STATUS = r'''
on safeText(v)
    try
        if v is missing value then return ""
        return v as text
    on error
        return ""
    end try
end safeText

tell application "Music"
    set stateText to ""
    set positionText to "0"
    set trackID to ""
    try
        set stateText to my safeText(player state)
    end try
    try
        set positionText to my safeText(player position)
    end try
    try
        set trackID to my safeText(persistent ID of current track)
    end try
end tell

set oldDelimiters to AppleScript's text item delimiters
set AppleScript's text item delimiters to ASCII character 31
set resultText to {stateText, positionText, trackID} as text
set AppleScript's text item delimiters to oldDelimiters
return resultText
'''


APPLE_SCRIPT_STOP = 'tell application "Music" to stop'


APPLE_SCRIPT_CAPABILITY_CHECK = r'''
on compileOnlyHandler()
    tell application "Music"
        play current track with once
    end tell
end compileOnlyHandler
return "ok"
'''


@dataclass(frozen=True)
class TrackInfo:
    playlist_index: int
    title: str
    artist: str
    album: str
    album_artist: str
    genre: str
    duration_seconds: float
    year: str
    track_number: str
    disc_number: str
    persistent_id: str


@dataclass(frozen=True)
class PlayerStatus:
    state: str
    position_seconds: float
    persistent_id: str


CSV_FIELDS = [
    "playlist_index",
    "status",
    "wav_filename",
    "title",
    "artist",
    "album",
    "album_artist",
    "genre",
    "duration_seconds",
    "year",
    "track_number",
    "disc_number",
    "persistent_id",
    "recording_started_utc",
    "recording_finished_utc",
    "max_player_position_seconds",
    "attempts",
    "error",
]


class RecorderError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def parse_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value.strip().replace(",", "."))
    except (AttributeError, ValueError):
        return default


def sanitize_filename(value: str, fallback: str, limit: int = 90) -> str:
    value = unicodedata.normalize("NFC", value or "")
    value = re.sub(r"[\x00-\x1f/:*?\"<>|]", "_", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    if not value:
        value = fallback
    return value[:limit].rstrip(" .")


def run_osascript(script: str, *args: object, timeout: float = 30.0) -> str:
    command = ["osascript", "-"] + [str(arg) for arg in args]
    try:
        result = subprocess.run(
            command,
            input=script,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RecorderError("找不到 osascript；此脚本只能在 macOS 上运行。") from exc
    except subprocess.TimeoutExpired as exc:
        raise RecorderError("Music.app 的 AppleScript 调用超时。") from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "未知 AppleScript 错误"
        raise RecorderError(detail)
    return result.stdout.rstrip("\r\n")


def get_playlist_count(playlist: str) -> int:
    raw = run_osascript(APPLE_SCRIPT_PLAYLIST_COUNT, playlist)
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise RecorderError(f"无法解析播放列表曲目数：{raw!r}") from exc


def get_track_info(playlist: str, index: int) -> TrackInfo:
    raw = run_osascript(APPLE_SCRIPT_TRACK_INFO, playlist, index)
    fields = raw.split(FIELD_SEPARATOR)
    if len(fields) != 10:
        raise RecorderError(f"第 {index} 首的元数据字段数量异常：{len(fields)}")
    return TrackInfo(
        playlist_index=index,
        title=fields[0].strip(),
        artist=fields[1].strip(),
        album=fields[2].strip(),
        album_artist=fields[3].strip(),
        genre=fields[4].strip(),
        duration_seconds=parse_float(fields[5]),
        year=fields[6].strip(),
        track_number=fields[7].strip(),
        disc_number=fields[8].strip(),
        persistent_id=fields[9].strip(),
    )


def play_track_once(playlist: str, index: int) -> None:
    run_osascript(APPLE_SCRIPT_PLAY_ONCE, playlist, index)


def get_player_status() -> PlayerStatus:
    raw = run_osascript(APPLE_SCRIPT_PLAYER_STATUS, timeout=10.0)
    fields = raw.split(FIELD_SEPARATOR)
    if len(fields) != 3:
        raise RecorderError(f"播放器状态字段数量异常：{len(fields)}")
    return PlayerStatus(
        state=fields[0].strip().lower(),
        position_seconds=parse_float(fields[1]),
        persistent_id=fields[2].strip(),
    )


def stop_music() -> None:
    run_osascript(APPLE_SCRIPT_STOP, timeout=10.0)


def check_music_applescript_capability() -> None:
    result = run_osascript(APPLE_SCRIPT_CAPABILITY_CHECK, timeout=10.0)
    if result.strip() != "ok":
        raise RecorderError("Music.app AppleScript 单曲播放能力检查失败。")


class ReaperRemote:
    def __init__(self, base_url: str, username: str = "", password: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        handlers: list[urllib.request.BaseHandler] = []
        if username:
            manager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
            manager.add_password(None, self.base_url, username, password)
            handlers.append(urllib.request.HTTPBasicAuthHandler(manager))
        self.opener = urllib.request.build_opener(*handlers)

    def _get(self, path: str, timeout: float = 5.0) -> bytes:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            headers={"User-Agent": "AppleMusicReaperRecorder/1.0"},
        )
        try:
            with self.opener.open(request, timeout=timeout) as response:
                return response.read(4096)
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RecorderError(
                f"无法连接 REAPER Web interface：{self.base_url}（{exc}）"
            ) from exc

    def check(self) -> None:
        self._get("/", timeout=5.0)

    def action(self, action_id: int) -> None:
        self._get(f"/_/{action_id}", timeout=5.0)

    def record(self) -> None:
        self.action(REAPER_RECORD_ACTION)

    def stop(self) -> None:
        self.action(REAPER_STOP_ACTION)


def audio_snapshot(directory: Path) -> dict[Path, tuple[int, int]]:
    result: dict[Path, tuple[int, int]] = {}
    if not directory.exists():
        return result
    for path in directory.iterdir():
        # exFAT stores macOS extended attributes in AppleDouble sidecars such
        # as `._01-260818_1548.wav`. They are metadata, not a second recording,
        # despite carrying the original file's `.wav` suffix. Ignore all hidden
        # entries so they can never be mistaken for captured audio.
        if (
            path.name.startswith(".")
            or not path.is_file()
            or path.suffix.lower() not in SUPPORTED_AUDIO_SUFFIXES
        ):
            continue
        try:
            stat = path.stat()
            result[path.resolve()] = (stat.st_size, stat.st_mtime_ns)
        except FileNotFoundError:
            pass
    return result


def changed_audio_files(
    before: dict[Path, tuple[int, int]], directory: Path
) -> list[Path]:
    after = audio_snapshot(directory)
    return sorted(
        [path for path, signature in after.items() if before.get(path) != signature],
        key=lambda p: p.stat().st_mtime_ns,
    )


def wait_for_recorded_files(
    before: dict[Path, tuple[int, int]], directory: Path, timeout: float = 12.0
) -> list[Path]:
    deadline = time.monotonic() + timeout
    previous_sizes: dict[Path, int] = {}
    stable_rounds = 0
    candidates: list[Path] = []

    while time.monotonic() < deadline:
        candidates = changed_audio_files(before, directory)
        sizes = {}
        for path in candidates:
            try:
                sizes[path] = path.stat().st_size
            except FileNotFoundError:
                pass
        if sizes and sizes == previous_sizes:
            stable_rounds += 1
            if stable_rounds >= 2:
                return list(sizes)
        else:
            stable_rounds = 0
        previous_sizes = sizes
        time.sleep(0.35)
    return candidates


def choose_destination(output_dir: Path, track: TrackInfo, suffix: str) -> Path:
    artist = sanitize_filename(track.artist, "Unknown Artist")
    title = sanitize_filename(track.title, "Unknown Title")
    base = f"{track.playlist_index:05d}_{artist}_{title}"
    candidate = output_dir / f"{base}{suffix.lower()}"
    if not candidate.exists():
        return candidate

    token = sanitize_filename(track.persistent_id[-8:], "duplicate", limit=16)
    candidate = output_dir / f"{base}_{token}{suffix.lower()}"
    number = 2
    while candidate.exists():
        candidate = output_dir / f"{base}_{token}_{number}{suffix.lower()}"
        number += 1
    return candidate


def load_successful_indices(csv_path: Path) -> set[int]:
    if not csv_path.exists():
        return set()
    completed: set[int] = set()
    with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row.get("status") != "success":
                continue
            try:
                completed.add(int(row.get("playlist_index", "")))
            except ValueError:
                pass
    return completed


def append_csv(csv_path: Path, row: dict[str, object]) -> None:
    exists = csv_path.exists() and csv_path.stat().st_size > 0
    with csv_path.open("a", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow(row)
        handle.flush()
        os.fsync(handle.fileno())


def write_session_config(path: Path, args: argparse.Namespace) -> None:
    public = {
        "playlist": args.playlist,
        "output_dir": str(args.output_dir),
        "recording_dir": str(args.recording_dir),
        "metadata_csv": str(args.metadata),
        "reaper_url": args.reaper_url,
        "sample_rate_recommended": 48000,
        "record_format_recommended": "WAV 24-bit PCM stereo",
        "lead_seconds": args.lead_seconds,
        "tail_seconds": args.tail_seconds,
        "poll_seconds": args.poll_seconds,
        "coarse_poll_seconds": args.coarse_poll_seconds,
        "final_window_seconds": args.final_window_seconds,
        "strict_track_id": args.strict_track_id,
        "created_utc": utc_now(),
    }
    path.write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class CaptureController:
    def __init__(self, args: argparse.Namespace, reaper: ReaperRemote) -> None:
        self.args = args
        self.reaper = reaper
        self.reaper_recording = False
        self.interrupted = False

    def emergency_stop(self) -> None:
        try:
            stop_music()
        except Exception:
            pass
        if self.reaper_recording:
            try:
                self.reaper.stop()
            except Exception:
                pass
            self.reaper_recording = False

    def capture_once(self, track: TrackInfo) -> tuple[Path, float, str, str]:
        before = audio_snapshot(self.args.recording_dir)
        started_utc = utc_now()
        max_position = 0.0
        last_position = 0.0
        playback_started = False
        capture_error: Exception | None = None

        self.reaper.record()
        self.reaper_recording = True
        time.sleep(self.args.lead_seconds)

        try:
            play_track_once(self.args.playlist, track.playlist_index)
            start_deadline = time.monotonic() + self.args.start_timeout
            hard_timeout = (
                track.duration_seconds + self.args.timeout_extra
                if track.duration_seconds > 0
                else self.args.unknown_duration_timeout
            )
            hard_deadline = time.monotonic() + hard_timeout

            while time.monotonic() < hard_deadline:
                status = get_player_status()
                max_position = max(max_position, status.position_seconds)

                if status.state == "playing":
                    if not playback_started:
                        playback_started = True
                    if (
                        self.args.strict_track_id
                        and track.persistent_id
                        and status.persistent_id
                        and status.persistent_id != track.persistent_id
                    ):
                        raise RecorderError(
                            "Music.app 播放的曲目与目标曲目不一致；请确认歌曲已加入资料库。"
                        )
                    if last_position > 2.0 and status.position_seconds < last_position - 1.5:
                        # Some Music.app versions briefly start the next queued
                        # song even after `play ... with once`.  When the reset
                        # happens only after reaching the target track's final
                        # few seconds, the requested song has been captured in
                        # full. Stop Music immediately and accept the take.
                        end_tolerance = max(3.0, self.args.final_window_seconds)
                        reached_expected_end = (
                            track.duration_seconds > 0
                            and max_position
                            >= track.duration_seconds - end_tolerance
                        )
                        if reached_expected_end:
                            stop_music()
                            break
                        raise RecorderError("播放器位置发生回跳，可能没有按单曲模式播放。")
                    last_position = status.position_seconds
                elif playback_started:
                    tolerance = max(2.5, self.args.poll_seconds * 4)
                    if track.duration_seconds <= 0 or max_position >= track.duration_seconds - tolerance:
                        break
                    raise RecorderError(
                        f"歌曲提前停止：播放至 {max_position:.2f}s，标称时长 {track.duration_seconds:.2f}s"
                    )
                elif time.monotonic() > start_deadline:
                    raise RecorderError("Apple Music 未在限定时间内开始播放。")

                # Most of a song does not need sub-second polling.  Poll slowly
                # until its final few seconds, then switch to the fine interval.
                if playback_started and track.duration_seconds > 0:
                    remaining = track.duration_seconds - max_position
                    sleep_for = (
                        self.args.coarse_poll_seconds
                        if remaining > self.args.final_window_seconds
                        else self.args.poll_seconds
                    )
                else:
                    sleep_for = self.args.poll_seconds
                time.sleep(max(self.args.poll_seconds, sleep_for))
            else:
                raise RecorderError("等待歌曲结束超时。")

            time.sleep(self.args.tail_seconds)
        except Exception as exc:
            capture_error = exc
        finally:
            self.reaper.stop()
            self.reaper_recording = False

        finished_utc = utc_now()
        files = wait_for_recorded_files(before, self.args.recording_dir)
        if capture_error is not None:
            # Never delete failed captures automatically. Move them aside so a
            # retry cannot be mistaken for the successful WAV.
            failed_dir = self.args.output_dir / "_failed_attempts"
            failed_dir.mkdir(exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            for number, source in enumerate(files, start=1):
                failed_name = (
                    f"{track.playlist_index:05d}_{stamp}_{number}"
                    f"{source.suffix.lower()}"
                )
                try:
                    shutil.move(str(source), str(failed_dir / failed_name))
                except OSError:
                    pass
            raise capture_error
        if not files:
            raise RecorderError(
                "REAPER停止后没有检测到新音频文件。请确认 REAPER 的录音目录与 "
                "--recording-dir 完全相同。"
            )
        if len(files) != 1:
            names = ", ".join(path.name for path in files)
            raise RecorderError(
                f"本次检测到 {len(files)} 个新音频文件（{names}）。请只保留一个立体声轨道处于录音准备状态。"
            )

        source = files[0]
        if self.args.keep_reaper_filenames:
            destination = self.args.output_dir / source.name
            if destination.resolve() != source.resolve():
                if destination.exists():
                    stem = destination.stem
                    suffix = destination.suffix
                    number = 2
                    while destination.exists():
                        destination = self.args.output_dir / f"{stem}_{number}{suffix}"
                        number += 1
                shutil.move(str(source), str(destination))
        else:
            destination = choose_destination(self.args.output_dir, track, source.suffix)
            shutil.move(str(source), str(destination))

        return destination, max_position, started_utc, finished_utc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="逐首播放 Apple Music 播放列表，并控制 REAPER 分别录成 WAV。"
    )
    parser.add_argument("--playlist", required=True, help="Music.app 中的播放列表名称")
    parser.add_argument(
        "--output",
        dest="output_dir",
        type=Path,
        required=True,
        help="最终 WAV 与 metadata.csv 的保存目录",
    )
    parser.add_argument(
        "--recording-dir",
        type=Path,
        help="REAPER实际录音目录；默认与--output相同",
    )
    parser.add_argument("--metadata", type=Path, help="CSV 路径，默认 OUTPUT/metadata.csv")
    parser.add_argument("--reaper-url", default="http://127.0.0.1:8080")
    parser.add_argument("--reaper-user", default="")
    parser.add_argument("--reaper-password", default="")
    parser.add_argument("--start-index", type=int, default=1, help="从播放列表第几首开始")
    parser.add_argument("--limit", type=int, default=0, help="最多录几首；0 表示直到列表末尾")
    parser.add_argument("--retries", type=int, default=1, help="单曲失败后的额外重试次数")
    parser.add_argument("--lead-seconds", type=float, default=0.35)
    parser.add_argument("--tail-seconds", type=float, default=0.35)
    parser.add_argument("--poll-seconds", type=float, default=0.25)
    parser.add_argument(
        "--coarse-poll-seconds",
        type=float,
        default=5.0,
        help="歌曲中段检查间隔；结尾会自动切换为 --poll-seconds",
    )
    parser.add_argument(
        "--final-window-seconds",
        type=float,
        default=5.0,
        help="距离标称结尾多少秒时切换为高频检查",
    )
    parser.add_argument("--start-timeout", type=float, default=20.0)
    parser.add_argument("--timeout-extra", type=float, default=45.0)
    parser.add_argument("--unknown-duration-timeout", type=float, default=1200.0)
    parser.add_argument(
        "--keep-reaper-filenames",
        action="store_true",
        help="不重命名 REAPER 生成的文件；CSV 仍会建立歌曲映射",
    )
    parser.add_argument(
        "--strict-track-id",
        action="store_true",
        help="严格核对 current track ID；部分 macOS 版本可能返回陈旧ID，默认不启用",
    )
    parser.add_argument("--check", action="store_true", help="只检查配置，不开始录音")
    parser.add_argument("--yes", action="store_true", help="跳过开始前确认")
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.start_index < 1:
        raise RecorderError("--start-index 必须不小于 1。")
    if args.limit < 0 or args.retries < 0:
        raise RecorderError("--limit 和 --retries 不能为负数。")
    for name in (
        "lead_seconds",
        "tail_seconds",
        "poll_seconds",
        "coarse_poll_seconds",
        "final_window_seconds",
    ):
        if getattr(args, name) < 0:
            raise RecorderError(f"--{name.replace('_', '-')} 不能为负数。")
    if args.poll_seconds < 0.05:
        raise RecorderError("--poll-seconds 建议不小于 0.05，以免频繁调用 Music.app。")


def confirm_start(args: argparse.Namespace, count: int, indices: list[int]) -> None:
    if args.yes:
        return
    print("\n开始前请确认：")
    print("  1. REAPER 使用空白专用工程，且只有一个立体声轨道处于录音准备状态")
    print("  2. REAPER 录音目录与 --recording-dir 完全相同")
    print("  3. 已关闭录音结束后的保存/删除询问窗口")
    print("  4. Music.app 输出到 BlackHole，且交叉淡化、Atmos、EQ、Sound Check 已关闭")
    print(f"\n播放列表共 {count} 首，本次计划处理 {len(indices)} 首。")
    answer = input("输入 RECORD 开始：").strip()
    if answer != "RECORD":
        raise RecorderError("用户取消。")


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.output_dir = args.output_dir.expanduser().resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.recording_dir = (
        args.recording_dir.expanduser().resolve()
        if args.recording_dir
        else args.output_dir
    )
    args.recording_dir.mkdir(parents=True, exist_ok=True)
    args.metadata = (
        args.metadata.expanduser().resolve()
        if args.metadata
        else args.output_dir / "metadata.csv"
    )
    args.metadata.parent.mkdir(parents=True, exist_ok=True)

    try:
        validate_args(args)
        if platform.system() != "Darwin":
            raise RecorderError("此脚本只能在 macOS 上运行。")

        reaper = ReaperRemote(args.reaper_url, args.reaper_user, args.reaper_password)
        print("检查 REAPER Web interface…")
        reaper.check()
        check_music_applescript_capability()
        print("检查 Apple Music 播放列表…")
        count = get_playlist_count(args.playlist)
        if count < 1:
            raise RecorderError("播放列表为空。")
        sample_index = min(max(args.start_index, 1), count)
        sample = get_track_info(args.playlist, sample_index)
        print(f"连接正常：{count} 首；样例为 {sample.artist} - {sample.title}")

        write_session_config(args.output_dir / "capture_config.json", args)
        if args.check:
            print("配置检查通过。未启动播放或录音。")
            return 0

        completed = load_successful_indices(args.metadata)
        end_index = count
        if args.limit:
            end_index = min(count, args.start_index + args.limit - 1)
        indices = [i for i in range(args.start_index, end_index + 1) if i not in completed]
        if not indices:
            print("范围内的曲目均已成功记录，无需继续。")
            return 0

        confirm_start(args, count, indices)
        controller = CaptureController(args, reaper)

        def handle_signal(signum: int, _frame: object) -> None:
            controller.interrupted = True
            raise KeyboardInterrupt

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        stop_music()
        reaper.stop()
        success_count = 0
        failure_count = 0

        try:
            for ordinal, index in enumerate(indices, start=1):
                try:
                    track = get_track_info(args.playlist, index)
                except Exception as exc:
                    failure_count += 1
                    error_text = f"读取第 {index} 首元数据失败：{exc}"
                    print(f"\n[{ordinal}/{len(indices)} | playlist #{index}] {error_text}")
                    append_csv(
                        args.metadata,
                        {
                            "playlist_index": index,
                            "status": "failed",
                            "attempts": 0,
                            "error": error_text,
                        },
                    )
                    continue
                display = f"{track.artist or 'Unknown Artist'} - {track.title or 'Unknown Title'}"
                print(f"\n[{ordinal}/{len(indices)} | playlist #{index}] {display}")
                last_error = ""
                destination: Path | None = None
                max_position = 0.0
                started_utc = ""
                finished_utc = ""
                attempts = 0

                for attempt in range(1, args.retries + 2):
                    attempts = attempt
                    try:
                        destination, max_position, started_utc, finished_utc = controller.capture_once(track)
                        break
                    except KeyboardInterrupt:
                        raise
                    except Exception as exc:
                        last_error = str(exc)
                        controller.emergency_stop()
                        print(f"  第 {attempt} 次失败：{last_error}")
                        if attempt <= args.retries:
                            print("  2 秒后重试…")
                            time.sleep(2.0)

                success = destination is not None
                row = {
                    "playlist_index": track.playlist_index,
                    "status": "success" if success else "failed",
                    "wav_filename": destination.name if destination else "",
                    "title": track.title,
                    "artist": track.artist,
                    "album": track.album,
                    "album_artist": track.album_artist,
                    "genre": track.genre,
                    "duration_seconds": f"{track.duration_seconds:.3f}",
                    "year": track.year,
                    "track_number": track.track_number,
                    "disc_number": track.disc_number,
                    "persistent_id": track.persistent_id,
                    "recording_started_utc": started_utc,
                    "recording_finished_utc": finished_utc,
                    "max_player_position_seconds": f"{max_position:.3f}",
                    "attempts": attempts,
                    "error": "" if success else last_error,
                }
                append_csv(args.metadata, row)

                if success:
                    success_count += 1
                    print(f"  已保存：{destination.name}")
                    if not track.genre:
                        print("  提示：Apple Music 的 genre 字段为空。")
                else:
                    failure_count += 1
                    print("  已写入 failed 记录，可稍后重新运行相同命令重试。")
        finally:
            controller.emergency_stop()

        print(f"\n完成：成功 {success_count} 首，失败 {failure_count} 首。")
        print(f"元数据：{args.metadata}")
        return 0 if failure_count == 0 else 2
    except KeyboardInterrupt:
        print("\n已中断，并尝试停止 Apple Music 与 REAPER。", file=sys.stderr)
        return 130
    except RecorderError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
