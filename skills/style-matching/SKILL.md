---
name: style-matching
description: Choose or compare photographic looks from the image, a reference, and user intent. Use for natural, film-inspired, cinematic, matte, or black-and-white grading without assuming every scene needs a preset.
---

# 风格服务照片

由当前 Codex 模型直接看图。使用原有光比、黑白关系、色彩分离和用户意图判断，不把某个场景强制映射成某个 LUT。

- 有参考：提取可观察的对比曲线、黑位、亮部、色彩关系，区分调色与照明、布景、镜头或运动效果。
- 无参考：保留原片光线，以自然方向或一个明确创意候选比较。强风格应有理由。
- 胶片不等于灰黑、低对比或统一暖色；电影不等于青橙；黑白也需要主体灰度分离。
- 风格名称表达方向，不能承诺复刻真实胶片、某位摄影师或某部电影的成像过程。不同肤色和不同照明不能套统一橙色。
- LUT 名称不证明适用性。对比输出中的主体、亮部、黑位与重要色彩后再选择；没有提升时保留原片方向。

按照照片需要读 [风格场景决策](references/style-decisions.md)：自然风光、落日/蓝调、城市夜景、人像、高调、低调、纪实、matte、黑白。场景表是取舍框架，不是固定配方。

现有 `knowledge/styles/` 仅为审美参考，不能用其中未经核实的 LUT 名称或参数作执行承诺。实际可调用控制见 [执行能力](../color-strategy/references/tool-capabilities.md)，实际库与使用条件见 [LUT 目录](../color-strategy/references/lut-catalog.md)。

若用户要求从某位摄影师的大型作品集提取方向，读取 [style-learning](../style-learning/SKILL.md)。只把结果称为“该公开作品集的源图相关统计参考”；不能写成作者官方风格、本人配方或从成片反推出的原始 LUT。

用简洁的“方向 → 图像证据 → 应保留内容 → 拒绝信号”说明选择，再交由 [color-strategy](../color-strategy/SKILL.md) 执行和复核。不要编造概率置信度，也不以风格强度代替质量。

