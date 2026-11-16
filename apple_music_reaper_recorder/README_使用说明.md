# Apple Music → BlackHole → REAPER 自动分首录音

这个脚本面向 macOS：它逐首播放一个 Apple Music 播放列表，每首开始前启动 REAPER 录音，播放结束后停止 REAPER，并将新生成的音频文件改名，同时把元数据追加到 CSV。

目标链路：

```text
Apple Music → BlackHole 2ch → REAPER → Fireface/其他硬件输出
```

## 重要说明

- 请仅录制和使用你有权处理的内容，并遵守 Apple Music 条款、著作权规定和单位的数据合规要求。
- Apple Music 的 `genre` 是曲库标签，不是严格的科研真值；缺失时 CSV 会留空。
- 脚本会在歌曲前后各保留约 0.35 秒，以优先保证不丢歌头、歌尾。
- 默认会在 REAPER 停止录音后改名 WAV。因此 REAPER 时间线中的旧媒体引用可能显示离线；请使用空白专用工程，不要把它当作需要长期保存的剪辑工程。

## 一、Apple Music 设置

1. 建立一个专用播放列表，例如 `Research Capture`。
2. 将播放列表里的歌曲加入“资料库”。Music.app 对未加入资料库或自动播放产生的曲目，AppleScript 的当前曲目信息可能不可靠。
3. 关闭交叉淡化、Dolby Atmos、EQ、声音增强器和 Sound Check。
4. 建议关闭随机播放。
5. 系统音频输出选择 `BlackHole 2ch`。

## 二、REAPER 设置

1. 新建一个空白专用工程。
2. `Preferences → Audio → Device`：
   - Input device：`BlackHole 2ch`
   - Output device：你的 Fireface 或其他硬件输出
   - Sample rate：`48000`
3. 新建一个轨道：
   - Stereo input：BlackHole Input 1/2
   - 开启录音准备
   - 只允许这一个轨道处于录音准备状态
4. 录音格式设置为 `WAV / 24-bit PCM / stereo`。
5. 将 REAPER 的录音目录设为一个固定目录。单歌单录制时可与最终输出目录相同；
   多类别批处理时建议使用独立暂存目录。
6. 关闭“每次停止后询问保存/删除/重命名录音文件”的弹窗。
7. `Preferences → Control/OSC/web → Add`：
   - Control surface mode：`Web browser interface`
   - Port：`8080`
   - 可先不设置用户名和密码

## 三、第一次检查

打开 REAPER 和 Music.app，然后在终端进入脚本目录。

```bash
python3 apple_music_reaper_recorder.py \
  --playlist "Research Capture" \
  --output "/Volumes/YourSSD/AppleMusicDataset/wav" \
  --check
```

第一次运行时，macOS 会询问终端是否允许控制“音乐”，请选择允许。也可在：

```text
系统设置 → 隐私与安全性 → 自动化 → 终端 → 音乐
```

确认 `--check` 显示播放列表数量和样例曲目。

## 四、先试录10首

默认情况下，确保 REAPER 的实际录音目录与 `--output` 完全相同，然后运行：

```bash
caffeinate -dimsu python3 apple_music_reaper_recorder.py \
  --playlist "Research Capture" \
  --output "/Volumes/YourSSD/AppleMusicDataset/wav" \
  --limit 10
```

脚本开始前要求输入大写 `RECORD`。试录完成后检查：

- 是否恰好生成10个WAV；
- 歌头和歌尾是否完整；
- 左右声道是否正确；
- 是否削波；
- `metadata.csv` 中歌名、艺人、专辑和 genre 是否正确；
- REAPER、微信、浏览器或系统通知是否混入录音。

## 五、正式录制

10首测试无误后，去掉 `--limit 10`：

```bash
caffeinate -dimsu python3 apple_music_reaper_recorder.py \
  --playlist "Research Capture" \
  --output "/Volumes/YourSSD/AppleMusicDataset/wav"
```

如果想从播放列表第501首开始：

```bash
python3 apple_music_reaper_recorder.py \
  --playlist "Research Capture" \
  --output "/Volumes/YourSSD/AppleMusicDataset/wav" \
  --start-index 501
```

## 断点续录

脚本每完成一首都会立即刷新 `metadata.csv`。意外中断后，重新运行完全相同的命令即可；CSV 中已经标记为 `success` 的播放列表序号会被跳过，`failed` 会再次尝试。

请不要在中途重排、插入或删除播放列表曲目，否则原来的序号映射会改变。若必须修改播放列表，建议建立一个新的输出目录和 CSV。

按 `Control+C` 时，脚本会尝试停止 Music.app 和 REAPER。

## 输出

默认文件名：

```text
00001_Artist_Title.wav
00002_Artist_Title.wav
...
```

同目录还会生成：

```text
metadata.csv
capture_config.json
```

CSV 包括：播放列表序号、状态、WAV文件名、歌名、艺人、专辑、专辑艺人、genre、时长、年份、曲目号、碟号、persistent ID、录音时间、实际最大播放位置、尝试次数和错误信息。

## 常用参数

```text
--limit 10                   只处理10首
--start-index 501            从第501首开始
--recording-dir DIR          REAPER实际写入目录；默认与--output相同
--retries 2                  每首失败后额外重试2次
--lead-seconds 0.35          开始播放前先录0.35秒
--tail-seconds 0.35          播放结束后多录0.35秒
--coarse-poll-seconds 5      歌曲中段每5秒检查一次状态
--poll-seconds 0.25          临近结尾每0.25秒检查一次
--keep-reaper-filenames      不改名，只在CSV中建立映射
--strict-track-id            严格核对Music.app当前曲目ID（默认关闭）
--reaper-url URL             默认 http://127.0.0.1:8080
--reaper-user USER           REAPER Web interface 用户名
--reaper-password PASSWORD   REAPER Web interface 密码
--yes                        跳过输入 RECORD 的确认
```

## 常见错误

### 无法连接 REAPER Web interface

- 检查 REAPER 是否打开；
- 检查 `Control/OSC/web` 中是否启用了 Web browser interface；
- 浏览器打开 `http://127.0.0.1:8080` 看是否出现 REAPER 遥控页面；
- 如果端口不是8080，用 `--reaper-url` 指定实际端口。

### 找不到新音频文件

REAPER 的实际录音目录与 `--recording-dir` 不一致，或者停止录音时出现了保存/删除弹窗。

### 一首歌产生多个文件

通常是有多个轨道处于录音准备状态。只保留一个立体声轨道。

失败或中断的短录音不会自动删除，而会移入 `_failed_attempts` 子目录，防止它们与正式WAV混在一起。

### Music.app 没有开始播放

- 确认歌曲已经加入资料库；
- 手动播放一次，确认订阅、网络和地区授权正常；
- 在系统设置中重新允许终端控制“音乐”；
- 避免让 Apple Music 的自动播放队列代替脚本指定的播放列表。

部分 macOS 版本可能让 `current track` 返回空值或陈旧值，因此脚本默认以“播放列表中的目标曲目对象”为准，不强制核对当前曲目ID。只有确认系统返回可靠时才使用 `--strict-track-id`。

### WAV在REAPER中显示离线

这是因为脚本在停止录音后改了物理文件名。数据集文件本身不受影响。若希望REAPER工程始终保持在线，增加 `--keep-reaper-filenames`，文件和歌曲的对应关系仍保存在CSV中。
