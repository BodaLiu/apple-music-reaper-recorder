# Apple Music → REAPER Batch Recorder

一个面向 macOS 的 Apple Music 批量内录工具。它通过 AppleScript 逐首控制 Music.app，通过 REAPER Web Interface 启停录音，将每首歌曲保存为独立音频文件，并持续写入可断点续录的元数据 CSV。

项目只使用 Python 标准库，不包含、上传或分发任何音乐音频。

## 功能

- 按 Apple Music 播放列表顺序逐首录音
- 通过 REAPER Web Interface 自动开始和停止录音
- 自动识别、重命名和移动 REAPER 生成的音频文件
- 输出歌曲、艺人、专辑、时长、Apple genre 和 persistent ID 等元数据
- 根据 `metadata.csv` 自动跳过已经成功的曲目
- 失败录音移动到 `_failed_attempts`，不会与正式文件混合
- 忽略 exFAT 硬盘产生的 `._*.wav` AppleDouble 文件
- 支持单播放列表、单类别和多类别批量录制

## 项目结构

```text
apple_music_reaper_recorder/
├── apple_music_reaper_recorder.py   核心逐首录音程序
└── README_使用说明.md                完整配置与排错说明

music_dataset_2000/
├── record_dataset.py                按 build_result.json 批量录制多个类别
├── record_one_genre.py              单类别便捷入口
└── build_*.py                       Apple Music 数据集歌单构建工具
```

## 环境要求

- macOS
- Python 3.9 或更高版本
- Music.app
- REAPER
- 可将系统播放音频送入 REAPER 的虚拟音频设备

具体 Music.app、REAPER 和音频路由设置见 [中文使用说明](apple_music_reaper_recorder/README_使用说明.md)。

## 第一次检查

```bash
python3 -u apple_music_reaper_recorder/apple_music_reaper_recorder.py \
  --playlist "Research Capture" \
  --output "/Volumes/YourSSD/MusicDataset/ResearchCapture" \
  --recording-dir "/Volumes/YourSSD/REAPER_Staging" \
  --check
```

检查通过时会显示播放列表数量和样例曲目，不会开始录音。

## 试录与正式录制

先试录 10 首：

```bash
caffeinate -dimsu python3 -u \
  apple_music_reaper_recorder/apple_music_reaper_recorder.py \
  --playlist "Research Capture" \
  --output "/Volumes/YourSSD/MusicDataset/ResearchCapture" \
  --recording-dir "/Volumes/YourSSD/REAPER_Staging" \
  --limit 10 \
  --retries 1
```

确认结果后，去掉 `--limit 10` 即可录完整播放列表。启动时输入大写 `RECORD`。

中断后重新执行相同命令，已经在 `metadata.csv` 中标记为 `success` 的播放列表序号会自动跳过。开始录制后不要重排播放列表。

## 多类别批量录制

`record_dataset.py` 接受一个 `build_result.json`。通用格式示例见 [examples/build_result.example.json](examples/build_result.example.json)。

```bash
caffeinate -dimsu python3 -u music_dataset_2000/record_dataset.py \
  --build-result "examples/build_result.example.json" \
  --dataset-root "/Volumes/YourSSD/MusicGenreDataset" \
  --recording-dir "/Volumes/YourSSD/REAPER_Staging"
```

启动时输入大写 `RECORD_ALL`。也可以增加 `--category Rock` 只处理一个类别，或使用 `--limit-per-category 10` 进行小规模试录。

## 输出

每个输出目录包含：

```text
00001_Artist_Title.wav
00002_Artist_Title.wav
metadata.csv
capture_config.json
_failed_attempts/
```

实际通道数、采样率和位深由 REAPER 工程决定。脚本本身不对音频做转码、归一化、增益或响度处理。

## 合规说明

请仅录制和处理你有权使用的内容，并遵守订阅服务条款、著作权规定和所在机构的数据合规要求。本项目不提供规避 DRM、下载 Apple Music 文件或分发受版权保护音频的功能。

## License

[MIT](LICENSE)
