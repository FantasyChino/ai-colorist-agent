---
name: photo-understanding
description: Visually assess a photograph before editing, separating exposure or color problems from intended lighting, composition, and mood. Use for photographic critique and preparation for AI Colorist grading.
---

# 直接看图形成摄影判断

分析者是当前 Codex 多模态模型。先打开用户原始图片，不需要调用 `analyze_image` 或外部视觉 API。不能只根据统计标签决定调色。

观察并形成简洁结论：
- 主体与视觉焦点：哪些区域讲述照片，哪些颜色或明度在分散注意力？
- 构图与深度：前景、主体、背景靠什么分离？远景灰雾是否是大气透视？
- 光照：受光面、背光面、光源和反射；剪影、逆光与暗区是否有意？
- 色彩关系：现场暖冷、混合光、相邻色；是否有无意偏色，哪些光色值得保留？
- 信息边界：云、皮肤和白衣是否还有渐变；深阴影是否有纹理？JPEG 中已丢失的数据不能承诺真实恢复。
- 媒介与编码：已渲染 JPEG/PNG、RAW、Log 与 HDR 需要不同流程；未知 ICC/编码应说明不确定性。

给出：观察证据、需修正的问题、应保留的结构、可解释的风格方向与风险。不要从“落日/人像/夜景”直接推出固定参数，不强迫直方图填满两端。

调色前阅读 [color-strategy](../color-strategy/SKILL.md)；涉及黑位、高光、灰雾或曲线时阅读其 [底层逻辑](../color-strategy/references/grading-foundations.md)。已下载 LUT 的验证不能代替对主体和整张照片的观察。

