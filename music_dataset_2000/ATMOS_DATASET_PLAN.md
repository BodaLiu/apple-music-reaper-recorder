# Apple Music Atmos 录制方案

## 目标

建立 `Dataset_Atmos_Balanced_100`：100首固定的、曲风均衡的 Dolby Atmos 歌曲，并对同一首歌分别录制：

- `Atmos_On`：音乐 App 的 Dolby Atmos 设为“始终开启”；
- `Atmos_Off`：音乐 App 的 Dolby Atmos 设为“关闭”。

两次录音使用完全相同的歌曲顺序、BlackHole/REAPER设置和录制增益。这样得到的是可配对比较的数据，而不是两组不同歌曲。

## 输出的含义

现有 `BlackHole 2ch -> REAPER stereo` 链路只能录到 Apple Music 输出的两声道 Atmos 空间渲染结果。它不是原始 Dolby Atmos ADM/BWF，也不包含独立的 7.1.4 床声道或对象元数据。

因此这批数据适用于：

- Atmos开/关的听感、频谱、相关性和声场差异研究；
- 两声道空间音频检测或分类实验；
- 上混算法与 Apple Music 两声道 Atmos 渲染结果的参考比较。

它不适用于训练真正的对象音频解码器，也不能作为离散多声道 Atmos 真值。

## 选歌结构

从10个 Apple Music 官方空间音讯分类歌单各选10首：Pop、Rock、Hip-Hop、R&B、Electronic、Jazz、Classical、Country、Alternative、C-Pop。

每首必须满足：

- 台湾区目录元数据包含 `atmos` 和 `spatial`；
- 时长2至8分钟；
- 同一艺人最多2首；
- 排除重复 catalog ID/ISRC；
- 第一批排除 Live、DJ Mix、Remix、Karaoke 和影视原声；
- 选完后冻结 catalog ID 和顺序，不跟随官方歌单更新。

具体来源ID和配额见 `atmos_playlist_plan.json`。

## 为什么不直接录官方综合歌单前100首

官方综合歌单会持续更新，排序也会改变；前排通常偏向近期热门流行音乐。直接取前100首会造成时间漂移、曲风偏斜和断点续录时的序号风险。

## 录制前必须修改的旧设置

原录音说明要求关闭 Dolby Atmos，那是普通曲风数据集的设置。录制本批数据时：

1. Atmos批次设为“始终开启”；
2. Stereo批次设为“关闭”；
3. 两批均关闭 Sound Check、EQ、交叉淡化和声音增强；
4. 不改变REAPER输入增益和Master增益；
5. 每批开始先试录同一首并确认 Music 播放界面确实显示 Dolby Atmos。

## 暂不开始长录

必须先完成三个检查：

1. 100首均已固定并加入资料库；
2. BlackHole作为输出时，音乐 App 仍实际提供 Atmos 渲染；
3. 同一首歌 Atmos开/关的短录音确实存在可重复差异。

通过后再各录100首，共200遍歌曲时长。
