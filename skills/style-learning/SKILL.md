---
name: style-learning
description: Fit and validate a source-dependent creative LUT from a photographer's verified public portfolio. Use when the user asks to learn a photographer reference style from 500 or more works and apply it through AI Colorist MCP.
---

# 从作品集拟合统计参考 LUT

这是可选的高级流程。普通调色直接使用内置 LUT 或由模型编写照片专用配方，无需采集参考作品或训练。公开发行包不附带摄影师照片缓存和此前绑定私人原片的拟合文件；历史目录只作本地研究说明。

先读取 [photo-understanding](../photo-understanding/SKILL.md)、[color-strategy](../color-strategy/SKILL.md) 与 [style-matching](../style-matching/SKILL.md)，并直接打开原片。这里的“学习”是本地 OpenCV 对公开成片进行不成对统计拟合，不调用外部模型或 GPT API。

## 参考集门槛

- 每位摄影师至少 500 张可解码作品；用本人官网，或本人官网明确链接的公开作品集。
- 保存逐图页面、公开图像 URL、作者身份依据、尺寸和哈希。用官方 asset ID、文件/像素哈希及感知近重复检查；扫描收藏、他人艺术复制、导航封面和 logo 不能凑数。
- 公开可见不等于获得再分发许可。参考图片只作本地统计输入，不能随 LUT 对外打包；manifest 如实记录版权或开放许可。
- 已渲染网页 JPEG 默认只能按其明确 ICC 或经审计的 sRGB 条件使用。未知编码要写入限制。

## 拟合与执行

1. 调用 `learn_style_lut(source_image_path, reference_dir, style_name, strength)`。`reference_dir` 指向仅含参考图的 `images/`；`strength` 为 0–2。
2. 工具先分析全部 500+ 图，每图等权；彩色占主导时，从与当前原片低级色调/色彩结构相近的 40% 中选择全库约 10% 的高色彩完成度样本；黑白占主导时按明度结构匹配并选择低色度模式，不能让少量彩色离群图夺走黑白风格。返回值必须同时报告全库数与实际目标样本数。
3. 先看 1.0 的实际输出。用户明确要求强效果时可以比较 1.6 与 2.0；每次都从原片生成，不能串联 JPEG。
4. 把返回的 `lut_path` 传给 `apply_color_grade`，再打开整张成片，与原片等尺寸比较。检查亮部梯度、黑位、主体分离、肤色/重要颜色、天空断层、饱和度和色偏。
5. CUBE、profile 与拟合 manifest 保存在 `assets/luts/learned/<style>/`。保留源图 SHA、参考集指纹、OpenCV/NumPy 版本、选择规则、强度、数值 QC 与上游采集记录哈希。

## 命名与结论边界

- 使用“某摄影师公开作品集的统计参考”或“source-matched creative reference”。不得称为作者官方 LUT、原始调色曲线、精确复刻或作者背书。
- LUT 绑定生成它的源图。换照片时重新调用学习工具；不要把已有文件登记成任意照片通用预设。
- 500 张不成对成片不能分离题材、光照、相机渲染和后期，也不能学习局部 mask、天空选择、皮肤保护、颗粒、光晕或已经剪切的信息。
- 强度大只证明变化明显，不证明更接近作者。以实际成片是否改善为验收标准。

算法与可复现边界见 [方法说明](references/method.md)，已核验的摄影师和当前原片结果见 [摄影师目录](references/photographer-catalog.md)。
