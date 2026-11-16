#!/usr/bin/env python3
"""Build the era-balanced, artist-diverse Atmos reference playlist (V2)."""

from pathlib import Path

import build_atmos_reference_100 as base


base.TARGET_PLAYLIST = "Dataset_Atmos_Reference_100_V2"
base.OUTPUT_DIR = Path(__file__).resolve().parent / "atmos_reference_100_v2_build"
base.SELECTION_METHOD = "era_balanced_classic_modern_artist_diverse"

# About half classic/reference recordings and half modern productions.
# Every entry copies the exact item from an Apple-curated Spatial Audio playlist.
base.SELECTION = [
    # International classics and established reference productions (25)
    ("空間音訊體驗", "Michael Jackson", "Billie Jean"),
    ("空間音訊體驗", "Michael Jackson", "Beat It"),
    ("空間音訊體驗", "Bowie", "Starman (2012 Remaster)"),
    ("空間音訊體驗", "ELTON JOHN", "Rocket Man (I Think It's Going to Be a Long Long Time)"),
    ("空間音訊體驗", "Mariah Carey", "Fantasy"),
    ("空間音訊體驗", "Foo Fighters", "Everlong"),
    ("空間音訊體驗", "The Who", "Baba O'Riley (Remastered 2022)"),
    ("空間音訊體驗", "Pink Floyd", "Wish You Were Here"),
    ("空間音訊體驗", "Prince & The Revolution", "Purple Rain"),
    ("空間音訊體驗", "Weezer", "Buddy Holly"),
    ("空間音訊體驗", "Oasis", "Wonderwall"),
    ("空間音訊體驗", "Queen", "Bohemian Rhapsody"),
    ("空間音訊體驗", "Madonna", "Vogue"),
    ("空間音訊體驗", "Fleetwood Mac", "Dreams"),
    ("空間音訊體驗", "The Beatles", "All My Loving (2023 Mix)"),
    ("空間音訊體驗", "The Beatles", "In My Life (2023 Mix)"),
    ("空間音訊體驗", "Snoop Dogg", "Gin and Juice"),
    ("空間音訊體驗", "Pearl Jam", "Better Man"),
    ("空間音訊體驗", "Eminem", "Stan (feat. Dido)"),
    ("空間音訊體驗", "Lorde", "Royals"),
    ("空間音訊體驗", "Kendrick Lamar", "HUMBLE."),
    ("空間音訊體驗", "Taylor Swift", "Cruel Summer"),
    ("空間音訊體驗", "Harry Styles", "As It Was"),
    ("空間音訊體驗", "Miley Cyrus", "Party In the U.S.A."),
    ("空間音訊體驗", "Mariah Carey", "Always Be My Baby"),

    # Modern mainstream productions (25)
    ("空間音訊體驗", "Billie Eilish", "CHIHIRO"),
    ("空間音訊體驗：熱門歌曲", "Billie Eilish", "BIRDS OF A FEATHER"),
    ("空間音訊體驗：熱門歌曲", "SZA", "Saturn"),
    ("空間音訊體驗：熱門歌曲", "SZA", "Kill Bill"),
    ("空間音訊體驗：熱門歌曲", "Sabrina Carpenter", "Please Please Please"),
    ("空間音訊體驗", "Dua Lipa", "Illusion"),
    ("空間音訊體驗", "Olivia Rodrigo", "vampire"),
    ("空間音訊體驗：熱門歌曲", "Teddy Swims", "Lose Control"),
    ("空間音訊體驗：熱門歌曲", "Chappell Roan", "Pink Pony Club"),
    ("空間音訊體驗：熱門歌曲", "Doechii", "Anxiety"),
    ("空間音訊體驗：熱門歌曲", "Lady Gaga", "Abracadabra"),
    ("空間音訊體驗：熱門歌曲", "Djo", "End of Beginning"),
    ("空間音訊體驗：熱門歌曲", "Kendrick Lamar", "luther"),
    ("空間音訊體驗：熱門歌曲", "Sabrina Carpenter", "Espresso"),
    ("空間音訊體驗：熱門歌曲", "Benson Boone", "Beautiful Things"),
    ("空間音訊體驗：熱門歌曲", "Shaboozey", "A Bar Song (Tipsy)"),
    ("空間音訊體驗：熱門歌曲", "Hozier", "Too Sweet"),
    ("空間音訊體驗：熱門歌曲", "Charli xcx", "360"),
    ("空間音訊體驗：熱門歌曲", "Ariana Grande", "the boy is mine"),
    ("空間音訊體驗：熱門歌曲", "Tyla", "Water"),
    ("空間音訊體驗：熱門歌曲", "Doja Cat", "Agora Hills"),
    ("空間音訊體驗：熱門歌曲", "Rema & Selena Gomez", "Calm Down"),
    ("空間音訊體驗：熱門歌曲", "Noah Kahan", "Stick Season"),
    ("空間音訊體驗：熱門歌曲", "Tate McRae", "greedy"),
    ("空間音訊體驗：熱門歌曲", "Gracie Abrams", "That’s So True"),

    # Rock: seven classics plus three current productions (10)
    ("空間音訊體驗：搖滾", "Queen", "Another One Bites The Dust"),
    ("空間音訊體驗：搖滾", "Fleetwood Mac", "Rhiannon"),
    ("空間音訊體驗：搖滾", "Rush", "Tom Sawyer"),
    ("空間音訊體驗：搖滾", "U2", "Mysterious Ways"),
    ("空間音訊體驗：搖滾", "The Rolling Stones", "Start Me Up (Remastered 2009)"),
    ("空間音訊體驗：搖滾", "Bowie", "\"Heroes\" (2017 Remaster)"),
    ("空間音訊體驗：搖滾", "Pink Floyd", "Have a Cigar"),
    ("空間音訊體驗：搖滾", "Queens of the Stone Age", "Easy Street"),
    ("空間音訊體驗：搖滾", "turnstile", "LOOK OUT FOR ME"),
    ("空間音訊體驗：搖滾", "Mumford & Sons & Hozier", "Rubber Band Man"),

    # Jazz (8)
    ("空間音訊體驗：爵士樂", "Freddie Hubbard", "Arietis"),
    ("空間音訊體驗：爵士樂", "Art Blakey & The Jazz Messengers", "Along Came Betty"),
    ("空間音訊體驗：爵士樂", "Thelonious Monk", "Monk's Dream (Take 8)"),
    ("空間音訊體驗：爵士樂", "Herbie Hancock", "Speak Like a Child"),
    ("空間音訊體驗：爵士樂", "Art Blakey & The Jazz Messengers", "Moanin'"),
    ("空間音訊體驗：爵士樂", "Miles Davis", "Freddie Freeloader"),
    ("空間音訊體驗：爵士樂", "Miles Davis", "So What"),
    ("空間音訊體驗：爵士樂", "John Coltrane", "A Love Supreme, Pt. 1: Acknowledgement"),

    # Classical (5)
    ("空間音訊體驗：古典音樂", "馬友友, 列奧尼達斯・卡瓦科斯, 伊曼紐爾・艾克斯 & 安東尼・塔梅斯提", "Symphony No. 3 in E-Flat Major, Op. 55 \"Eroica\" (Arr. for Piano Quartet by Shai Wosner): I. Allegro con brio"),
    ("空間音訊體驗：古典音樂", "瑪莉亞・杜尼亞絲, 委內瑞拉玻利瓦爾青年管弦樂團 & 古斯塔沃 · 杜達美", "Violin Concerto in D Major, Op. 35: III. Finale. Allegro assai vivace"),
    ("空間音訊體驗：古典音樂", "魯多維柯・艾奧迪", "Summer Song"),
    ("空間音訊體驗：古典音樂", "維京格・歐拉夫森", "Piano Sonata No. 30 in E Major, Op. 109: III. Andante molto cantabile ed espressivo"),
    ("空間音訊體驗：古典音樂", "王羽佳, 波士頓交響樂團 & 安德里斯・尼爾森斯", "Piano Concerto No. 2 in F Major, Op. 102: II. Andante"),

    # Country and contemporary crossover (8)
    ("空間音訊體驗：鄉村樂", "Carrie Underwood", "Before He Cheats"),
    ("空間音訊體驗：鄉村樂", "Carrie Underwood", "Blown Away"),
    ("空間音訊體驗：鄉村樂", "Shania Twain", "Man! I Feel Like a Woman!"),
    ("空間音訊體驗：鄉村樂", "Shania Twain", "Any Man of Mine"),
    ("空間音訊體驗：鄉村樂", "Kacey Musgraves", "Follow Your Arrow"),
    ("空間音訊體驗：鄉村樂", "Kacey Musgraves", "Space Cowboy"),
    ("空間音訊體驗：鄉村樂", "Luke Combs", "The Kind of Love We Make"),
    ("空間音訊體驗：熱門歌曲", "Post Malone", "I Had Some Help (feat. Morgan Wallen)"),

    # Electronic: broad production styles with reduced artist repetition (9)
    ("空間音訊體驗：電子音樂", "Kraftwerk", "Autobahn (2024 Single Edit)"),
    ("空間音訊體驗：電子音樂", "Bonobo", "Drift"),
    ("空間音訊體驗：電子音樂", "Angèle & Justice", "What You Want"),
    ("空間音訊體驗：電子音樂", "Danny L Harle & Dua Lipa", "Two Hearts"),
    ("空間音訊體驗：電子音樂", "Bicep", "Taarsitillugu (feat. Tarrak)"),
    ("空間音訊體驗：電子音樂", "Jamie xx, Romy & Oliver Sim", "Waited All Night"),
    ("空間音訊體驗：電子音樂", "Justice & Tame Impala", "Neverender"),
    ("空間音訊體驗：電子音樂", "Fred again.., Duskus, Joy Anonymous, Four Tet & Skrillex", "glow"),
    ("空間音訊體驗：電子音樂", "Daft Punk", "Motherboard (Drumless Edition)"),

    # Recognisable C-Pop repertoire (10)
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

base.APPLE_SCRIPT_CREATE = base.APPLE_SCRIPT_CREATE.replace(
    "100首手工精选Dolby Atmos参考曲；经典作品与成熟空间混音优先。",
    "100首年代平衡的Dolby Atmos参考曲；经典与现代制作各约一半。",
)


if __name__ == "__main__":
    raise SystemExit(base.main())
