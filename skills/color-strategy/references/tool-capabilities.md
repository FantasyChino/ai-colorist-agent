# 当前 MCP 执行能力

以 `tools/pipeline.py`、`adjust_color.py`、`hsl_adjustment.py`、`tone_curve.py` 和 `lut_engine.py` 为准。

| 实际参数 | 行为 | 判断时的限制 |
| --- | --- | --- |
| `exposure` 数值 | 每个 BGR 通道加同一个 8-bit 数值，然后裁到 0–255 | 不是 EV、不是 RAW 恢复，正值可能剪切亮部 |
| `tone_strategy.contrast: medium` | 不改变对比 | 保留原片的有效基线 |
| `contrast: low` | 围绕 128 乘 0.8 | 黑变约25、白变约229，全范围压缩，会发灰 |
| `contrast: high` | 围绕 128 乘 1.2 | 约21以下/234以上会向端点剪切，应检查纹理 |
| `black_point: normal` | 不改变黑点 | 当前没有局部暗部控制 |
| `black_point: lifted` | 固定曲线将0变20，255保持255 | 不可调幅度；不是保留黑点的shadow recovery |
| `black_point: crushed` | 当前未执行特殊操作 | 不能声称已压黑 |
| `hsl_adjustment.COLOR` | `hue`、`saturation`、`brightness` 按 HSV 色域移动 | `brightness` 是 V，不是严格 HSL L |
| `lut` 路径 | 最后应用一个3D cube，RGB顺序，三线性插值 | 全强度；空间需匹配；会按8-bit输出裁域 |

HSL 的颜色键是 `red, orange, yellow, green, cyan, blue, purple, magenta`；`aqua` 不是当前有效键。
OpenCV H 范围为0–179，色相数值不是角度。操作是整图色相区域，不按语义/位置保护主体，相邻范围还存在边界重叠。
当前各色 mask 还要求 S>=50、V>=50；很多灰色道路和很暗的物体不会被选中。不能假设给 blue 增 brightness 就会打开全部道路；大幅调整硬阈值范围还需检查边界和渐变。

当前 Pipeline 不执行 `color_strategy` 下的温度、阴影色、高亮色和全局饱和度；也不执行 `highlight_rolloff`、`subject_protection`、纹理、grain、mask。这些只可作为未实现建议，不能传入后宣称成功。

LUT 修复保留 `load_cube(path)` 和 `apply_simple_lut(image, lut)` 接口：标准 cube 红索引变化最快；加载器校验size、行数、finite与DOMAIN。恒等LUT应保留原色和连续灰阶。1D/shaper cube不支持；输入必须为8-bit BGR。这里没有ICC转换、Log解码或HDR处理。

执行顺序是基础明度 → 对比/抬黑 → HSL → LUT。前置操作在8-bit域中量化并可能裁切；后置 LUT 不能找回前一步丢失的通道信息。因此不能先过量曝光或增反差，再声称靠 LUT 恢复层次。

## 示例：保留落日自然关系

```json
{
  "image_path": "demo/input.jpg",
  "strategy": {
    "exposure": 0,
    "tone_strategy": {"contrast": "medium", "black_point": "normal"},
    "hsl_adjustment": {}
  }
}
```

这是中性起点，不是成品风格。看原图后再决定必要的颜色改动或兼容 LUT；不能为“表现做了调色”而机械增加参数。

## LUT 试验强度

先调用 MCP `list_looks()` 查看实际库存、编码与许可，再调用 `prepare_look(lut_id, strength)` 生成派生 cube。也可使用 skill 的 `scripts/prepare_lut.py LUT_ID --strength 0.25`。它在 LUT 表值与恒等映射之间混合；`apply_color_grade` 本身没有 `lut_strength` 参数。这种编码域混合不等于物理曝光或场景线性混合。

把脚本返回的 `lut_path` 放进 `strategy.lut`，其他基础控制先保留，避免重复对比与饱和处理。从原片重新调用工具并看输出。派生 LUT 是变更后的授权作品，保留其 attribution/许可证及provenance sidecar。

