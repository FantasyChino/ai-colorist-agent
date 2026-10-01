---
name: color-strategy
description: Plan and execute photographic color grading with AI Colorist MCP tools and licensed LUTs. Use for photo correction, creative looks, LUT selection, or revising a grade after visual feedback.
---

# AI Colorist：判断、执行与复核

由当前 Codex 多模态模型直接观察照片、决定策略，再调用已有 `apply_color_grade`。不要求 `analyze_image`，不另建 Agent、不调用 GPT API。以用户意图和照片本身为依据。

## 从原片建立判断

- 先打开原图，说明主体、主光、原有冷暖关系与应保留的明暗结构。统计量只能辅助，不能替代看图。
- 区分技术问题与摄影意图：落日剪影、低调阴影、高调白背景不自动等于曝光错误。
- 用一句可验收目标描述这次调整，例如“保留天空亮度与建筑黑位，增强暖冷分离”，并指出可能受影响的区域。
- 没有明确风格要求时，以保留原片自然光色为起点；有参考时提取光比、黑白端点、色彩关系，不能只套“胶片/电影/日系”标签。
- 首次接触照片或处理发灰、层次、过曝问题时，读 [底层逻辑](references/grading-foundations.md)。需要选择风格时，读 [风格决策](../style-matching/references/style-decisions.md)。
- 处理本项目的 `demo/input.jpg` 或检查上次发灰问题时，读 [城市晚霞案例](references/case-sunset.md)，避免重复已经失败的控制。

## 把视觉目标映射到真实工具

先读 [执行能力](references/tool-capabilities.md)，只传已经实现的参数。

- 当前 `exposure` 是 8-bit 数值加减，不是摄影 EV；`contrast=low` 同时抬黑、降白，不是局部提亮或软肩。
- 胶片感不自动要求抬黑、去饱和；低反差也要保留密度和主体分离。
- HSL 选择色相，不认识天空、人物或建筑。共享色相的区域可能一起改变。
- 不把无效字段当已执行：全局温度、分离色调、高光恢复、mask、grain、halation 目前没有对应执行能力。
- 工具不足以完成目标时，采用更小的可实现改动并说明限制；不要把全局操作描述成局部保护。
- 当前流程在曝光/HSL 等前置操作中已裁到8-bit；后置 LUT 不能找回前一步制造的剪切，不能靠 LUT 补救过量控制。

## 有条件地使用 LUT

LUT 是候选映射，不是根据场景自动匹配的滤镜。

1. 读 [已下载 LUT 场景目录](references/lut-catalog.md)，查询项目根的 `assets/luts/catalog.json`。
2. 检查来源、授权、输入/输出空间与校验状态。普通 JPEG 不能直接使用 Log-to-display LUT；sRGB 与 Rec.709 编码不能混同。
3. `family_assumption`、相机专用或空间不确定的候选必须先预览，不宣称精确胶片再现。不把技术转换混弱来补救空间错误。
4. 可用 `scripts/preview_luts.py` 从原片生成低强度 creative 候选和对比图；看实际结果后再选，不仅看文件名。
   低强度是试验起点，不是最终强度；没有清楚改善时，重新判断目标、候选和必要的基础调整。需要时比较更高强度的实际响应，但不能仅靠加大强度制造变化。统一25%的多张预览不能替代针对照片的调色。
5. 先用 MCP `list_looks` 查看库存；用 `prepare_look(lut_id, strength)` 烘焙派生 cube，再把返回路径传给 `strategy.lut`。也可使用 `scripts/prepare_lut.py`。`apply_color_grade` 本身没有 `lut_strength` 参数；派生过程会保留来源与授权。
6. 没有候选胜过原片时，不使用 LUT。一次使用一个 look，不叠加滤镜弥补错误输入。

若已确认视觉目标，而现有基础控制过粗、库存 LUT 又不合适，可制作照片专用 creative CUBE 资产并通过已有 `strategy.lut` 应用，保持执行算法不变。记录生成方法、输入假设与来源；借用表值时保留原许可，不编造 catalog ID。专用 LUT 也必须验证黑白端点、灰阶和实际照片，不能冒充局部 mask、准确胶片模型或通用场景预设。

从至少 500 张已核验摄影作品拟合时使用 [style-learning](../style-learning/SKILL.md) 和 MCP `learn_style_lut`。该工具输出位于 `assets/luts/learned/`，并绑定当前原片与参考集指纹；换原片应重新拟合，不能把生成的 CUBE 当作通用摄影师预设。

命令用项目虚拟环境 Python 执行（Windows `.venv/Scripts/python.exe`，macOS/Linux `.venv/bin/python`）；脚本路径相对本 skill，输入路径相对项目根。

内置通用候选无需训练，见 [Ready Looks](references/ready-looks.md)。用户认可的四张独立调色案例见项目根 `docs/showcase.md`。这些案例使用模型为各照片编写的专用 LUT，不能用它们证明通用预设在所有照片上的效果。

## 执行与验收

- 每版从原始输入生成；不要用上一版 JPEG 连续叠效果。原片保留，当前工具会覆盖项目根 `output.jpg`。
- 未改变的控制可从 `exposure: 0`、`tone_strategy: {"contrast":"medium","black_point":"normal"}` 出发，这只是中性基线，不是所有照片的最佳方案。
- 在 MCP 中调用 `apply_color_grade(image_path, strategy)`，再打开实际输出，与原片以相近尺寸比较。
- 检查黑位锚点、亮部梯度、主体分离、肤色/重要颜色、天空断层与噪声。数值变化或 `success` 不代表审美成功。
- 按最初目标指出输出中可见的具体改善：哪个区域的什么关系改变了。在同尺寸整图与局部对照中都无法清楚辨认收益时，不得称“已调好”；保留结构也不等于所有基础控制保持无变化后直接交付。
- 用户反馈“看不出变化”时，核对实际控制是否全为中性、是否只混入低强度LUT，再重新看图。坦白记录未达标；不能用像素差、许可检查或协议通过证明调色质量，也不通过差值放大图夸大正常观看的效果。
- 若只增加灰雾、削白或造成重要细节/光色损失，回到原片减量、换候选或放弃 LUT。不因改变大就判“更好”。
- 告知实际执行的控制和原因、输出路径，以及尚未实现的目标。用户对风格的反馈优先于预设名称。

