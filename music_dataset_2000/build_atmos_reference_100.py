#!/usr/bin/env python3
"""Build a hand-curated 100-track Dolby Atmos reference playlist."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from build_atmos_balanced_100 import FS, Track, read_playlist


SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "atmos_reference_100_build"
TARGET_PLAYLIST = "Dataset_Atmos_Reference_100"
SELECTION_METHOD = "hand_curated_recognisable_and_reference_mix_priority"

# source playlist, exact artist, exact title
SELECTION = [
    # International canon and modern reference productions (50)
    ("空間音訊體驗", "Michael Jackson", "The Way You Make Me Feel (2012 Remaster)"),
    ("空間音訊體驗", "Michael Jackson", "Beat It"),
    ("空間音訊體驗", "Michael Jackson", "Billie Jean"),
    ("空間音訊體驗", "Michael Jackson", "Don't Stop 'Til You Get Enough"),
    ("空間音訊體驗", "Michael Jackson", "Rock with You (Single Version)"),
    ("空間音訊體驗", "Bowie", "Modern Love"),
    ("空間音訊體驗", "Bowie", "Starman (2012 Remaster)"),
    ("空間音訊體驗", "ELTON JOHN", "Rocket Man (I Think It's Going to Be a Long Long Time)"),
    ("空間音訊體驗", "ELTON JOHN", "Goodbye Yellow Brick Road (2014 Remaster)"),
    ("空間音訊體驗", "Billie Eilish", "bad guy"),
    ("空間音訊體驗", "Billie Eilish", "LUNCH"),
    ("空間音訊體驗", "Billie Eilish", "CHIHIRO"),
    ("空間音訊體驗：熱門歌曲", "Billie Eilish", "BIRDS OF A FEATHER"),
    ("空間音訊體驗：熱門歌曲", "Billie Eilish", "WILDFLOWER"),
    ("空間音訊體驗", "Mariah Carey", "Always Be My Baby"),
    ("空間音訊體驗", "Mariah Carey", "Fantasy"),
    ("空間音訊體驗", "Mariah Carey", "One Sweet Day (feat. Boyz II Men)"),
    ("空間音訊體驗", "Foo Fighters", "Learn to Fly"),
    ("空間音訊體驗", "Foo Fighters", "Everlong"),
    ("空間音訊體驗", "The Who", "Baba O'Riley (Remastered 2022)"),
    ("空間音訊體驗", "The Who", "Behind Blue Eyes (Remastered 2022)"),
    ("空間音訊體驗", "Pink Floyd", "Wish You Were Here"),
    ("空間音訊體驗", "Prince & The Revolution", "Let's Go Crazy"),
    ("空間音訊體驗", "Prince & The Revolution", "Purple Rain"),
    ("空間音訊體驗", "Prince & The Revolution", "When Doves Cry"),
    ("空間音訊體驗", "Weezer", "Buddy Holly"),
    ("空間音訊體驗", "Weezer", "Say It Ain't So (2024 Remaster)"),
    ("空間音訊體驗", "Oasis", "Wonderwall"),
    ("空間音訊體驗", "Oasis", "Don't Look Back in Anger"),
    ("空間音訊體驗", "Oasis", "Champagne Supernova"),
    ("空間音訊體驗", "Queen", "Bohemian Rhapsody"),
    ("空間音訊體驗", "Madonna", "Vogue"),
    ("空間音訊體驗", "Lorde", "Royals"),
    ("空間音訊體驗", "Kendrick Lamar", "HUMBLE."),
    ("空間音訊體驗", "Fleetwood Mac", "Dreams"),
    ("空間音訊體驗", "The Beatles", "All My Loving (2023 Mix)"),
    ("空間音訊體驗", "The Beatles", "In My Life (2023 Mix)"),
    ("空間音訊體驗", "The Beatles", "Yesterday (2023 Mix)"),
    ("空間音訊體驗", "Snoop Dogg", "Gin and Juice"),
    ("空間音訊體驗", "Taylor Swift", "Anti-Hero"),
    ("空間音訊體驗", "Taylor Swift", "Cruel Summer"),
    ("空間音訊體驗", "Harry Styles", "As It Was"),
    ("空間音訊體驗", "Miley Cyrus", "Party In the U.S.A."),
    ("空間音訊體驗", "Dua Lipa", "Illusion"),
    ("空間音訊體驗", "Pearl Jam", "Better Man"),
    ("空間音訊體驗", "Olivia Rodrigo", "vampire"),
    ("空間音訊體驗", "Eminem", "Stan (feat. Dido)"),
    ("空間音訊體驗：熱門歌曲", "SZA", "Snooze"),
    ("空間音訊體驗：熱門歌曲", "SZA", "Saturn"),
    ("空間音訊體驗：熱門歌曲", "SZA", "Kill Bill"),

    # Rock reference mixes (10)
    ("空間音訊體驗：搖滾", "Queen", "Another One Bites The Dust"),
    ("空間音訊體驗：搖滾", "Fleetwood Mac", "Rhiannon"),
    ("空間音訊體驗：搖滾", "Rush", "Tom Sawyer"),
    ("空間音訊體驗：搖滾", "U2", "Mysterious Ways"),
    ("空間音訊體驗：搖滾", "The Rolling Stones", "Start Me Up (Remastered 2009)"),
    ("空間音訊體驗：搖滾", "Bowie", "\"Heroes\" (2017 Remaster)"),
    ("空間音訊體驗：搖滾", "Pink Floyd", "Have a Cigar"),
    ("空間音訊體驗：搖滾", "The Who", "Who Are You"),
    ("空間音訊體驗：搖滾", "Alice In Chains", "Rooster"),
    ("空間音訊體驗：搖滾", "The Cure", "Boys Don't Cry (86 Mix / 2026 Remaster)"),

    # Canonical jazz performances and Atmos remixes (8)
    ("空間音訊體驗：爵士樂", "Freddie Hubbard", "Arietis"),
    ("空間音訊體驗：爵士樂", "Art Blakey & The Jazz Messengers", "Along Came Betty"),
    ("空間音訊體驗：爵士樂", "Thelonious Monk", "Monk's Dream (Take 8)"),
    ("空間音訊體驗：爵士樂", "Herbie Hancock", "Speak Like a Child"),
    ("空間音訊體驗：爵士樂", "Art Blakey & The Jazz Messengers", "Moanin'"),
    ("空間音訊體驗：爵士樂", "Miles Davis", "Freddie Freeloader"),
    ("空間音訊體驗：爵士樂", "Miles Davis", "So What"),
    ("空間音訊體驗：爵士樂", "John Coltrane", "A Love Supreme, Pt. 1: Acknowledgement"),

    # Familiar classical repertoire and established performers (5)
    ("空間音訊體驗：古典音樂", "馬友友, 列奧尼達斯・卡瓦科斯, 伊曼紐爾・艾克斯 & 安東尼・塔梅斯提", "Symphony No. 3 in E-Flat Major, Op. 55 \"Eroica\" (Arr. for Piano Quartet by Shai Wosner): I. Allegro con brio"),
    ("空間音訊體驗：古典音樂", "瑪莉亞・杜尼亞絲, 委內瑞拉玻利瓦爾青年管弦樂團 & 古斯塔沃 · 杜達美", "Violin Concerto in D Major, Op. 35: III. Finale. Allegro assai vivace"),
    ("空間音訊體驗：古典音樂", "魯多維柯・艾奧迪", "Summer Song"),
    ("空間音訊體驗：古典音樂", "維京格・歐拉夫森", "Piano Sonata No. 30 in E Major, Op. 109: III. Andante molto cantabile ed espressivo"),
    ("空間音訊體驗：古典音樂", "王羽佳, 波士頓交響樂團 & 安德里斯・尼爾森斯", "Piano Concerto No. 2 in F Major, Op. 102: II. Andante"),

    # Country standards and modern canon (8)
    ("空間音訊體驗：鄉村樂", "Carrie Underwood", "Before He Cheats"),
    ("空間音訊體驗：鄉村樂", "Carrie Underwood", "Blown Away"),
    ("空間音訊體驗：鄉村樂", "Shania Twain", "Man! I Feel Like a Woman!"),
    ("空間音訊體驗：鄉村樂", "Shania Twain", "Any Man of Mine"),
    ("空間音訊體驗：鄉村樂", "Kacey Musgraves", "Follow Your Arrow"),
    ("空間音訊體驗：鄉村樂", "Kacey Musgraves", "Space Cowboy"),
    ("空間音訊體驗：鄉村樂", "Kacey Musgraves", "Merry Go 'Round"),
    ("空間音訊體驗：鄉村樂", "Luke Combs", "The Kind of Love We Make"),

    # Electronic productions selected for spatial movement and texture (9)
    ("空間音訊體驗：電子音樂", "Kraftwerk", "Autobahn (2024 Single Edit)"),
    ("空間音訊體驗：電子音樂", "Daft Punk", "Motherboard (Drumless Edition)"),
    ("空間音訊體驗：電子音樂", "Bonobo", "Drift"),
    ("空間音訊體驗：電子音樂", "Bonobo", "Me and You"),
    ("空間音訊體驗：電子音樂", "Bonobo & Joy Crookes", "Always on Your Side"),
    ("空間音訊體驗：電子音樂", "Danny L Harle & Dua Lipa", "Two Hearts"),
    ("空間音訊體驗：電子音樂", "Fred again.. & John Martyn", "little mystery"),
    ("空間音訊體驗：電子音樂", "Fred again.., Duskus, Joy Anonymous, Four Tet & Skrillex", "glow"),
    ("空間音訊體驗：電子音樂", "Fred again.., Skepta & PlaqueBoyMax", "Victory Lap"),

    # Recognisable C-Pop standards (10)
    ("空間音訊體驗：C-Pop 熱門歌曲", "齊豫", "橄欖樹"),
    ("空間音訊體驗：C-Pop 熱門歌曲", "李宗盛", "愛的代價"),
    ("空間音訊體驗：C-Pop 熱門歌曲", "張惠妹", "掉了"),
    ("空間音訊體驗：C-Pop 熱門歌曲", "張震嶽", "思念是一種病 (feat. 蔡健雅)"),
    ("空間音訊體驗：C-Pop 熱門歌曲", "梁靜茹", "可惜不是你"),
    ("空間音訊體驗：C-Pop 熱門歌曲", "張惠妹", "我最親愛的"),
    ("空間音訊體驗：C-Pop 熱門歌曲", "張學友", "祝福"),
    ("空間音訊體驗：C-Pop 熱門歌曲", "伍佰 & China Blue", "Last Dance"),
    ("空間音訊體驗：C-Pop 熱門歌曲", "張惠妹", "連名帶姓"),
    ("空間音訊體驗：C-Pop 熱門歌曲", "孫燕姿", "尚好的青春"),
]


APPLE_SCRIPT_CREATE = r'''
on run argv
    set destinationName to item 1 of argv
    tell application "Music"
        if exists user playlist destinationName then error "目标歌单已经存在：" & destinationName
        set destinationPlaylist to make new user playlist with properties {name:destinationName, description:"100首手工精选Dolby Atmos参考曲；经典作品与成熟空间混音优先。"}
        repeat with argumentIndex from 2 to count of argv
            set oldTIDs to AppleScript's text item delimiters
            set AppleScript's text item delimiters to character id 31
            set fields to text items of (item argumentIndex of argv)
            set AppleScript's text item delimiters to oldTIDs
            set sourceName to item 1 of fields
            set sourceIndex to item 2 of fields as integer
            set sourcePlaylist to first playlist whose name is sourceName
            duplicate track sourceIndex of sourcePlaylist to destinationPlaylist
        end repeat
        return count every track of destinationPlaylist
    end tell
end run
'''


def resolve_selection() -> list[Track]:
    if len(SELECTION) != 100:
        raise RuntimeError(f"手工清单不是100首：{len(SELECTION)}")
    source_names = list(dict.fromkeys(source for source, _, _ in SELECTION))
    pools = {name: read_playlist("Reference", name) for name in source_names}
    for name, tracks in pools.items():
        print(f"读取：{name}（{len(tracks)}首）", flush=True)
    resolved: list[Track] = []
    used: set[str] = set()
    for source, artist, title in SELECTION:
        matches = [track for track in pools[source] if track.artist == artist and track.title == title]
        # Apple occasionally repeats the same catalog item inside an editorial
        # playlist. Treat repeated rows with one persistent ID as one track.
        unique_matches = {track.pid_key or track.title_key: track for track in matches}
        if len(unique_matches) != 1:
            raise RuntimeError(f"无法唯一定位：{source} / {artist} - {title}（匹配{len(matches)}）")
        track = next(iter(unique_matches.values()))
        key = track.pid_key or track.title_key
        if key in used:
            raise RuntimeError(f"清单重复：{artist} - {title}")
        used.add(key)
        resolved.append(track)
    return resolved


def write_manifest(tracks: list[Track]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUTPUT_DIR / "final_100.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["dataset_index", "source_playlist", "source_index", "persistent_id", "title", "artist", "album", "apple_genre", "duration_seconds"])
        for index, track in enumerate(tracks, 1):
            writer.writerow([index, track.playlist, track.index, track.pid, track.title, track.artist, track.album, track.genre, f"{track.duration:.3f}"])


def playlist_count() -> int | None:
    script = f'tell application "Music" to if exists user playlist "{TARGET_PLAYLIST}" then return count every track of user playlist "{TARGET_PLAYLIST}"'
    result = subprocess.run(["osascript", "-e", script], text=True, capture_output=True)
    return int(result.stdout.strip()) if not result.returncode and result.stdout.strip() else None


def create_playlist(tracks: list[Track]) -> None:
    args = ["osascript", "-", TARGET_PLAYLIST]
    args.extend(f"{track.playlist}{FS}{track.index}" for track in tracks)
    result = subprocess.run(args, input=APPLE_SCRIPT_CREATE, text=True, capture_output=True, timeout=1200)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "创建参考歌单失败")
    if int(result.stdout.strip()) != 100:
        raise RuntimeError(f"目标歌单实际数量异常：{result.stdout.strip()}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("check", "build"))
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    tracks = resolve_selection()
    write_manifest(tracks)
    print(f"清单完成：100首，{len(set(t.artist_key for t in tracks))}位艺人", flush=True)
    if args.command == "check":
        return 0
    existing = playlist_count()
    if existing is not None:
        raise RuntimeError(f"{TARGET_PLAYLIST}已存在（{existing}首），未覆盖")
    if not args.yes and input("输入 BUILD 创建参考歌单：").strip() != "BUILD":
        return 1
    create_playlist(tracks)
    result = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "playlist_name": TARGET_PLAYLIST,
        "total": 100,
        "artist_count": len(set(t.artist_key for t in tracks)),
        "selection": SELECTION_METHOD,
        "catalog_verification": "exact_track_copy_from_apple_curated_spatial_audio_playlists"
    }
    (OUTPUT_DIR / "build_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"完成：{TARGET_PLAYLIST}（100首）", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
