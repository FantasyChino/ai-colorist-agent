# 已下载的 LUT：用途、边界与实测

资源入口：项目根目录 `assets/luts/catalog.json`。其中的路径均相对于项目根。
库中有 **18 个 33³ CUBE**：10 个原创通用创意风格与8个独立授权的第三方候选；另保留原始 Hald PNG、来源说明、许可证。
原创风格的适用场景与限制见 [Ready Looks](ready-looks.md)。它们安装即可使用，不要求训练；也不是摄影师官方 LUT 或预训练神经网络。
**这是风格候选库，不是自动套滤镜的规则。** 默认无 LUT，先看原图，再决定
是否需要颜色风格。以下场景都是筛选假设，必须由模型看实际预览确认。

## 来源与输入条件

- **Pat David 6 个创作性胶片近似**：下载自 NatronGitHub/clut，固定提交
  `af7b50d4caf6244fb6895a647f5b6a84efe7931a`。许可证 CC-BY-SA-4.0。
  原始文件是 512×512、16-bit RGB Hald64；本项目三线性重采样为 CUBE33。
  作者说明它们是艺术近似，不是精确复刻，也不包含颗粒等空间效果。
- **Zhengxiao Wu (t0saki) 2 个原创数学 LUT**：固定提交
  `708f98d97a26b123128480050c2a1459c8a58cca`。原始 CUBE 字节未改动，MIT。
  上游明确披露 AI 协作创作，设计基础是 LUMIX S9 Standard + sRGB；它们
  不是摄影大师预设，也不声称准确复刻真实胶片。
- Pat David 家族的相关 RawTherapee 文档以 sRGB 为基础，但这 6 个 Natron PNG
  都没有 sRGB、gAMA 或 ICC 标签，上游也没有逐个文件说明。因此目录记录
  `assumed_not_individually_verified`；不能声称本文件已通过色彩管理认证。
- 对普通 sRGB JPEG，这些都是需要预览的候选；对 P3、AdobeRGB、线性、HDR
  或相机 Log，不得直接应用。LUT 本身不会识别输入颜色空间。
- `auto_select` 全部为 `false`。LUT 强度是有创作含义的调节，不是通用
  曝光修正；目录的建议起点是本项目的保守试用范围，不是上游相机设置。

## 候选怎么筛

下表“黑/白”是把纯黑/纯白送入 LUT 后的 RGB，按 0–255 换算；它描述
LUT 的端点，不是说照片里的黑/白本来就应该位于那里。0.5 灰也是编码值，
不是物理 18% 灰卡。所有数值来自本项目的测试，不是作者的风格宣传。

| id / 文件 | 可以预览的场景 | 实测要点与避用条件 | 起始强度 |
| --- | --- | --- | --- |
| `pat_kodak_portra_160` / `pat-david-cc-by-sa-4.0/kodak_portra_160.cube` | 日光人像、旅行 | 黑约(6,4,3)，白约(253,249,251)，0.5灰约0.59。会抬黑、亮中灰；已经灰的照片、想保留深黑的晚霞慎用。检查皮肤，不按胶片名保证肤色。 | 0.15–0.35 |
| `pat_kodak_portra_400` / `pat-david-cc-by-sa-4.0/kodak_portra_400.cube` | 街拍、日常、人像 | 黑约(6,5,5)，白约(252,250,253)，0.5灰约0.62。也会抬黑和亮中灰；高调白色层次、明亮夕阳要特别检查。 | 0.15–0.35 |
| `pat_fuji_provia_100f` / `pat-david-cc-by-sa-4.0/fuji_provia_100f.cube` | 日光旅行、风景 | 黑约(7,16,5)，带绿黑；白约(240,251,251)，0.5灰约0.47。暗部有局部轻微亮度反转，不能默认当作中性胶片。 | 0.10–0.30 |
| `pat_fuji_velvia_50` / `pat-david-cc-by-sa-4.0/fuji_velvia_50.cube` | 绿植、自然、景观 | 黑约(1,0,0)，白约(250,251,240)，0.5灰约0.46。暗部密度增加，高亮偏黄。人像、已有浓烈晚霞、霓虹需要检查色彩压缩和饱和边界。 | 0.10–0.25 |
| `pat_fuji_superia_800` / `pat-david-cc-by-sa-4.0/fuji_superia_800.cube` | 混合光街拍、暖灯室内的风格试验 | 黑约(1,18,19)，明显青黑；白约(247,239,244)。存在小段亮度反转，暗部偏色和白色染色较明显。中性色准确、深黑或细腻肤色优先时避免。 | 0.10–0.25 |
| `pat_kodak_tri_x_400` / `pat-david-cc-by-sa-4.0/kodak_tri-x_400.cube` | 用户想要黑白，且照片故事由形状、明暗、纹理构成 | 输出 RGB 三通道相等；黑10、白243，不包含颗粒。黑端略抬并有极小段亮度反转。不能因照片不好调就擅自转黑白。 | 黑白意图明确后预览1.0 |
| `lumix_meridian` / `lumix-original-mit/Meridian.cube` | 日光、中性色基准风格试验 | 黑0、白255，中性轴最大通道差约0.25码，但0.5灰升到0.56；“中性轴”不等于 identity。普通 JPEG 的 camera-profile 匹配未经保证。 | 0.15–0.35 |
| `lumix_lowsun` / `lumix-original-mit/Lowsun.cube` | 金色时段、暖逆光的色彩方向试验 | 黑约(1,3,6)，白255，阴影冷、高亮暖。已有明显橙色的夕阳可能被过度强化；也可能把暗部抬灰。 | 0.10–0.25 |

上述文件路径需要前置 `assets/luts/`。库存用 `id` 查找，实际执行传 `path`。

## 校验与使用顺序

1. 识别图片已是 display-referred JPEG，检查可见高亮层次和应保持的黑锚点。
2. 先做必要的基础修正，保留无 LUT 对照。不要为“胶片感”统一抬黑、减反差。
3. 若选择 LUT，它已含色彩和明暗变换；避免在它之前再堆强 S 曲线和高曝光。
4. 以目录的小强度预览，比较主体肤色/物体色、云层与灯光分离、黑部质感。
   原图本来精彩的区域也必须保留。副作用大于风格收益就放弃这个 LUT。
5. 正式导出后再看成品，不以 `success` 或 histogram 数字代替视觉判断。

所有 CUBE 已检查大小33、节点数35937、有限值、单位输入域和单位输出范围，
并用当前 `tools.lut_engine` 成功加载和应用到 256级中性 ramp。离线验证还使用
1025级 ramp 和合成 RGB 色块。它们证明格式和响应特征，不证明审美质量。

Provia、Superia、Tri-X 的1025级中性 ramp有小段反转；单步最坏分别约0.076、
0.070、0.010个8-bit亮度码，累计下降约2.11、1.60、0.15码。目录保留这项
结果，不能把测试报告概括成“所有 LUT 单调无损”。

Hald64→CUBE33 的20000随机 RGB 重采样对比：RMS差约0.17–0.37个8-bit
通道码，最坏约1.32–9.02码。这是重采样误差，不是照片最终误差，也不是
感知ΔE。保留原始 PNG，严格颜色需求可重新转换更高分辨率；本库不声称无损。

## 许可和可复现

CC-BY-SA 原件和派生 LUT 单独存放，保留 `ATTRIBUTION.md`、完整许可证、
来源链接与转换说明；MIT 两个 CUBE 同样保留作者版权和许可。
每个原件及 CUBE 的 SHA-256 在 `catalog.json`。进一步派生 LUT 应保留对应
署名和许可证，不把整个混合素材库统一误标为 MIT。

`assets/luts/download_sources.py` 可重新下载固定提交的原件；
`assets/luts/prepare_library.py` 在下载后离线再生成第三方 CUBE 和实测目录；之后运行 `scripts/build_creative_looks.py` 合并10个原创风格，得到完整18项目录。
它们只处理 LUT 资产，不执行上游代码，不调用外部模型。

参考来源：

- [Pat David：创作性胶片近似的说明](https://patdavid.net/2013/08/film-emulation-presets-in-gmic-gimp/)
- [Natron 来源及逐类作者署名/许可](https://github.com/NatronGitHub/clut)
- [RawTherapee Film Simulation：格式与 sRGB 家族条件](https://rawpedia.rawtherapee.com/Film_Emulation)
- [LUMIX Original Looks：原创来源、profile 与 MIT](https://github.com/t0saki/lumix-original-looks)
- [Hald CLUT 原作者：布局与插值](https://www.quelsolaar.com/technology/clut.html)
