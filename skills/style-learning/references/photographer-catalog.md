# 摄影师统计参考目录

**历史本地研究记录，非 v1.0 可下载预设清单。** 下述原片、500张参考集、拟合文件与验证记录保留在研究者本机，未随开源包发布。它们不能在新安装中直接调用；日常调色请用 `assets/luts/catalog.json` 中的内置候选，或由模型按照片设计配方。

机器可读目录见 `assets/luts/learned/catalog.json`。以下十项均已用各摄影师公开作品中 **500 张唯一、可解码照片**完成校验；每张照片只投一票。拟合工具先按当前原片筛出内容和调性较相容的 40% 候选，再从中取 10% 的高色度创作模式；黑白作品集改为取低色度且调性相容的 10%。

当前 CUBE 全部绑定 `demo/input.jpg`，源图 SHA-256 为 `bce857a365ef80fff9d8da386e62fa25d745a3891ad1855ed45e722d6e2bf4ae`，拟合强度为 `2.0`。换图时必须重新调用 `learn_style_lut`，不能把这些文件当成摄影师的通用官方预设。

| 参考作者 | 当前原片上的可见方向 | 适合优先尝试 | CUBE / profile |
|---|---|---|---|
| Daniel Kordan | 玫瑰橙天空、琥珀高光、浓郁红橙灯光 | 日落风光、暖色旅行、戏剧性自然光 | `daniel-kordan-source-matched-creative-reference/fit-eae66beb1dbe.cube` / `.profile.json` |
| Trey Ratcliff | 鲜明金橙、冷色云层、强旅行/HDR 感 | 金色时刻、旅行奇观、色彩型城市风光 | `trey-ratcliff-source-matched-creative-reference/fit-5c5f657a3aca.cube` / `.profile.json` |
| Thomas Hawk | 青绿冷云与橙色夕阳对置，城市红蓝更醒目 | 城市日落、蓝调时刻、互补色画面 | `thomas-hawk-source-matched-creative-reference/fit-c5d2be13db08.cube` / `.profile.json` |
| G Dan Mitchell | 较克制的饱和度、清晰青灰天空、自然暖光 | 山地、海岸、自然主义金色时刻 | `g-dan-mitchell-source-matched-creative-reference/fit-0530c58deab5.cube` / `.profile.json` |
| Jeff Sullivan | 明净金黄、灰青云层、受控但活跃的风光色彩 | 荒漠、天气、星空与日落风光 | `jeff-sullivan-source-matched-creative-reference/fit-e54276b77d42.cube` / `.profile.json` |
| Ming Thein | 奶油暖高光、低调青灰、较深阴影 | 建筑、城市秩序、精炼暖冷平衡 | `ming-thein-source-matched-creative-reference/fit-4cb1926bc6ed.cube` / `.profile.json` |
| Maciej Dakowicz | 珊瑚与洋红暖色、青灰云层、突出的红色街灯 | 街头、旅行纪实、混合色温城市光 | `maciej-dakowicz-source-matched-creative-reference/fit-bed38124cbde.cube` / `.profile.json` |
| Bjørn Joachimsen | 中性黑白、银盐感云层分离、深黑前景 | 黑白风光、建筑、纹理与剪影 | `bjorn-joachimsen-source-matched-creative-reference/fit-958fd09d0ef7.cube` / `.profile.json` |
| Ralf Mittermüller / crosslens | 金黄与橄榄/青色组合，画面更图形化 | 极简风光、建筑线条、黄绿互补 | `ralf-mittermueller-crosslens-source-matched-creative-ref/fit-4ec87ac98f55.cube` / `.profile.json` |
| Andrew Smith / Cuba Gallery | 本组最强的青绿与金橙分离，色彩痕迹最明显 | 大胆日落、海岸旅行、电影感暖冷分离 | `cuba-gallery-source-matched-creative-reference/fit-eec0d95bd543.cube` / `.profile.json` |

## 官方来源与验证记录

- Daniel Kordan：`https://danielkordan.com/gallery/`；验证 `references/photographers/daniel-kordan/verification.json`。
- Trey Ratcliff：`https://stuckincustoms.smugmug.com/Portfolio`；验证 `references/photographers/trey-ratcliff/validation.json`。
- Thomas Hawk：`https://thomashawk.com/` 与 `https://www.flickr.com/photos/thomashawk/`；验证 `references/photographers/thomas-hawk/validation.json`。
- G Dan Mitchell：`https://gdanmitchell.com/purchasing-photographs/` 与 `https://www.flickr.com/photos/gdanmitchell/`；验证 `references/photographers/g-dan-mitchell/validation.json`。
- Jeff Sullivan：`https://www.jeffsullivanphotography.com/` 与 `https://www.flickr.com/photos/jeffreysullivan/`；验证 `references/photographers/jeff-sullivan/validation.json`。
- Ming Thein：`https://blog.mingthein.com/` 与 `https://www.flickr.com/photos/mingthein/`；验证 `references/photographers/ming-thein/validation.json`。
- Maciej Dakowicz：`https://www.maciejdakowicz.com/contact/` 与 `https://www.flickr.com/photos/maciejdakowicz/`；验证 `references/photographers/maciej-dakowicz/validation.json`。
- Bjørn Joachimsen：`https://www.joachimsenphotography.com/` 与 `https://www.flickr.com/people/joachimsen/`；验证 `references/photographers/bjorn-joachimsen/validation.json`。
- Ralf Mittermüller：`https://www.crosslens.de/about` 与 `https://www.flickr.com/photos/crosslens/`；验证 `references/photographers/ralf-mittermueller-crosslens/validation.json`。
- Andrew Smith / Cuba Gallery：`https://www.cubagallery.co.nz/` 与 `https://www.flickr.com/photos/cubagallery/`；验证 `references/photographers/cuba-gallery/validation.json`。

## 使用边界

- 这是非配对照片的统计颜色迁移，只能描述该公开样本集对当前原片形成的方向；不能识别摄影师真实的场景到成片曲线，也不能宣称复刻其风格。
- 样本统计同时包含题材、天气、光线、相机与后期选择。Codex 必须先看原片，再看输出，并根据主体、肤色与局部细节拒绝不合适的候选。
- LUT 处理全局 RGB 映射，不包含蒙版、分区曝光、天空选择、颗粒、光晕、降噪或锐化，也不能恢复原 JPEG 已剪切的细节。
- 参考预览保留原作者版权，仅作本地研究证据；不得随插件、LUT 或输出一起再分发。命名仅用于说明统计参考来源，不代表作者授权、官方预设或认可。
- 十张实际输出、并排图和数值诊断分别位于 `demo/learned-styles/`、`comparison-ten-v6.jpg` 与 `ten-style-metrics-v6.json`。
