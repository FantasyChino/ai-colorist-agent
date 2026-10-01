# AI Colorist 项目工作约定

当用户要求分析、调色、挑选风格或使用 LUT 时，先读取 `skills/photo-understanding/SKILL.md`、`skills/color-strategy/SKILL.md`；需要风格选择时读取 `skills/style-matching/SKILL.md`。这些项目 skill 与其 references 是调色判断依据。

当用户要求从摄影师作品集学习风格或生成统计参考 LUT 时，再读取 `skills/style-learning/SKILL.md`。学习结果是对当前源图有条件的统计近似，不能称为摄影师本人 LUT 或通用预设。

由当前 Codex 多模态模型直接打开原片、决定可执行策略，使用已有 AI Colorist MCP 工具；不要求 analyze_image、不另建 Agent、不调用 GPT API。先看原图，再看实际输出。LUT来源、授权、编码条件与使用候选见 `assets/luts/catalog.json`。

编辑实现时保持当前 MCP → Tools → OpenCV 架构。不要为调色操作重写现有算法；只有已复现的明确错误才作必要修复，并验证原接口。输入图片保留，候选从原图生成。开发任务不自动触发图片处理。

