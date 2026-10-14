# H3 提示词技能与可选海艺路径

本页只在用户选择 H3、请求 H3 格式提示词或比较模型路线时读取。日常 Seedance 复刻使用 [通用提示词设计](prompt-direction.md)，不为它加载整套 H3 交互流程。

## 安装与范围

外部技能应位于当前技能目录的相邻位置：`h3-prompt-writing`、`minimax-h3-creative-director`、`minimax-h3-multishot-planner`、`minimax-h3-text-video-prompt`、`minimax-h3-reference-video-prompt`、`minimax-h3-keyframe-video-prompt`、`minimax-h3-prompt-reviewer`。

来源为 [社区仓库](https://github.com/unknowlei/minimax-h3-opencode-skills)（本次检查 commit `2e2096fe39ef9b5ddd5998cdcf422c6534065115`，MIT）及 [MiniMax 官方技能](https://github.com/MiniMax-AI/MiniMax-H3/tree/d21241f0a4b3acbb34c97dae47fa417b7065e438/skills/h3-prompt-writing)。社区包不包含官方依赖，安装时需要另取。统一源码包只提供结合说明，不复制或自动安装这七个外部技能；缺失时文字创作仍可按本工作流进行，不能声称 H3 格式技能已安装。

这是一组提示词指导，不包含模型、额度、MiniMax API 连接器或 Hypit H3 Provider。原版交互导演有逐镜提问与确认规则；用户明确选用原版交互创作时按其约定处理。统一流程可沿用已确定的 Brief/分镜并直接使用官方格式指导，只澄清实质缺口，不把原版交互步骤变成所有 Seedance 项目的固定审批。

## 提示词路径

读取 `../h3-prompt-writing/SKILL.md`（相对本统一技能根目录的相邻技能），按实际输入选择其 base-en 或 ref-en 指导。参考视频、角色图片和声音构成的复刻通常需要全参考格式。用户请求原版入口或专门审查时读取对应外部技能和其引用的文档；遵循当前宿主工具的实际能力与用户已有约定。

外部技能中的模型输出时长、标签、提示词长度与素材限制仅适用于对应 H3 产品/执行路径。官方格式负责文本语义；海艺实时模型配置负责海艺接口的字段、选项和限制，采用能同时满足要求的请求。不能把提示词格式规范当成已经验证的编辑效果。

## 海艺路径的已知配置

2026-10-14 使用既有海艺账号只读查询，列表包含以下 `provider=minimax`、`type=image2video` 模型；执行前重新查询当前配置：

| 模型 id | 本次查询的入口 | 主要参考字段 |
| --- | --- | --- |
| `minimax-h3` | 全能参考 | `imageUrls`、`videoUrls`、`audioUrls`；`prompt`、`duration`、`resolution`、`ratio` |
| `minimax-h3-frame` | 首尾帧 | `key_frames.start` / `key_frames.end`；`prompt`、`duration`、`resolution` |
| `minimax-h3-max` | 首尾帧、极速版 | 同类 `key_frames`，分辨率选项与大小写须按该模型配置 |

海艺当时的输出时长选项为字符串 `5` 至 `15`。全能参考配置允许最多 9 张图、3 段视频、3 段音频；视频/音频单段 2–15 秒。还需满足官方格式/产品的组合限制，不以某个字段未列总量为无限制。全能参考的计费说明按“参考视频总时长 + 输出视频时长”计算；首尾帧入口按输出时长。额度、报价与最终支持以实时服务为准。

当前自定义 Hypit Provider 仍只路由 Seedance 与 GPT Image。H3 生成可通过原 `haiyi-aigc` 技能的明确模型调用完成，采用其实际可用 Python 环境与 requests 依赖；素材上传和生成仅在本项目授权范围内执行。取得实际视频后，按 Hypit 作者指导作为已存在素材编排，记录海艺任务 id、素材路径与角色版本。不能把 `workflow.mjs build` 中的 Seedance 模型名简单换成 H3，不能宣称已有自动 H3 Provider、成本 plan 或原生调度集成。

本次验证覆盖技能文件/依赖和海艺只读配置查询，未提交 H3 付费生成；原生画面、声音、严格角色编辑和成片效果均未实测。
