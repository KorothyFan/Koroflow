# Hypit + 海艺视频工坊

统一的 Codex 视频生产技能和代码库：导演与剧本模块负责前期创作，海艺负责图片/视频素材生成，Hypit 负责分镜、时间线、素材复用和成片渲染。已安装的两个基础插件可以保留；从 `$hypit-haiyi` 统一进入工作流。

## 提供的内容

- `skills/hypit-haiyi/`：可安装统一技能，自动匹配视频制作请求，写入默认海艺流程与跨任务使用约定。
- `skills/video-director/`：可独立使用的导演与剧本技能，产出创作方案、剧本、分镜、连续性锚点和素材计划；统一工作流默认调用。
- `packages/provider-haiyi/`：TypeScript Provider，直接连接海艺 OpenAPI，覆盖 Seedance 2.5 和 GPT Image 2.5 Flare。
- `templates/project/`：图片、四秒视频、Runtime Profile 模板。
- `scripts/workflow.mjs`：复用/安装固定版本 Hypit、配置 FFmpeg、安装技能、新建独立项目、检查/计划/生成命令。
- `scripts/bundle.mjs`：仅按白名单打包源码、技能和文档。

整合提升工作组织、连续性与可编辑性，不改变模型基础画质。TTS、音乐及增强等尚未绑定到 Provider，可以通过海艺原技能获取素材再导入。此仓库是集成源码与技能，不是离线模型或完整独立二进制安装包。

## 与海艺 Skill、Hypit 的关系

**本仓库是整合层，不包含海艺原 Skill 或完整 Hypit 工具。** 它提供统一技能、海艺 API 适配器、项目模板和配置脚本，将两个工具组织成一套视频生产流程。只下载本仓库，还需要准备下列依赖；其中一部分可由脚本下载或补装，不必全部手动下载。

| 组件 | 是否需要 | 如何准备 |
| --- | --- | --- |
| 本仓库的统一技能 `hypit-haiyi` | 统一工作流入口 | 随本仓库提供，运行 `install-skill` 安装 |
| 本仓库的导演技能 `video-director` | 前期策划，可单独使用 | `install-skill` 一并安装；只写剧本可用 `install-skill --director-only` 独立安装，无需先 setup |
| Hypit 执行工具 | 必需，负责项目编排和渲染 | 已有指定版本时用 `setup --hypit-root` 复用；没有时用 `setup --install` 联网下载指定版本并安装依赖 |
| Hypit 原技能 `hypit` | 完整工作流使用其创作与制作指导 | `install-skill` 会从已准备的 Hypit 工具目录补装缺失的技能；已有技能则保留 |
| 海艺原技能 `haiyi-aigc` | 用于海艺登录及语音、音乐、增强等补充功能 | 本仓库不会下载或安装它；需要这些功能时，请从海艺原插件/技能的提供渠道单独安装 |
| 海艺账号与有效 Token | 云端生成必需 | 使用自己的账号授权；设置 `HAIYI_API_TOKEN`，或复用海艺原技能已保存的登录凭据 |
| Node.js、FFmpeg、FFprobe；从零准备 Hypit 时另需 Git、pnpm | 本地运行依赖 | 单独安装，再按下方步骤配置 |

当前 Provider 已直接实现海艺图片和视频 API 调用。因此，如果只用本仓库已支持的图片/视频模型，并且已取得有效 Token，可以不安装海艺原 Skill。需要通过原技能登录，或使用 TTS、音乐、视频增强、字幕擦除等功能时，仍需单独安装海艺原 Skill；使用它时也需按其说明准备 Python 环境。

建议首次使用者按以下顺序准备：本地运行依赖 → Hypit 工具（可由脚本下载）→ 统一技能和 Hypit 原技能（由脚本安装）→ 海艺账号授权；需要补充功能时再安装海艺原技能。已经安装好的组件可以复用。

Hypit 原项目与安装说明见 [hypit-ai/hypit](https://github.com/hypit-ai/hypit)。安装 Hypit 技能本身不等于已经安装 Hypit 执行工具，也不会提供海艺账号或生成额度。

## 导演与剧本模块

Hypit 原技能已有 Brief/Treatment、脚本与语义时间、图像/视频导演、表演与声音、素材依赖等创作指导。本仓库额外提供可独立调用的导演入口，将这些制作约定接到我们的海艺流程；不是购买一个新的生成模型，也不保证仅靠安装技能提高画质。

完整流程为：**创作目标 → 导演方案 → 剧本与分镜 → 素材计划 → 海艺生成 → Hypit 编排与渲染 → 成片检查**。适用于广告、短剧、叙事短片、讲解视频；沿用已有项目的正式方案，修改时只调整相关部分。

- 只写剧本：说“使用 `$video-director` 写一支 30 秒产品广告的剧本和分镜，暂不生成。”
- 完整制作：说“使用 `$hypit-haiyi`，从导演方案开始制作视频。”实际云端生成按已接受的付费范围执行。

只需要文字策划时，克隆代码库后运行 `node scripts/workflow.mjs install-skill --director-only`。此模式只需 Node 与可用的 Codex 环境，不要求 Hypit、FFmpeg、海艺技能或账号；也可以将 `skills/video-director` 文件夹直接安装到用户技能目录。

剧本草稿和分镜保存到视频项目，正式采用后 Hypit Author Source 的 `<script>` 是唯一正式台词来源；分镜引用片段 id，避免多份台词改稿不同步。仅请求剧本或分镜不会提交付费媒体生成。

## 视频复刻与角色替换

复刻换角色是统一工作流的专门分支，和原创制作共用工具与账号，无需另建代码库或安装第三套生成引擎。导演模块此时用于拆解原片、建立角色映射和迁移表演/镜头关系，不默认重新创作故事。

**原视频分析 → 原角色/目标角色映射 → 镜头与动作记录 → 角色一致性参考 → 逐镜编辑或重建 → Hypit 重组 → 对照原片检查。** 只要求替换角色时，剧情、台词、节奏和声音关系先继承原片；用户要求其他变化再调整。

| 制作选项 | 目标 | 当前边界 |
| --- | --- | --- |
| 原片角色编辑 | 尽量保留原背景、动作、运镜与时间，只改变目标角色 | 需要实际服务支持视频编辑或角色替换；参考视频输入不等于已提供严格编辑功能 |
| 参考原片重建 | 按原片剧情、镜头和动作关系，用新角色重新生成 | 可用视频/图片参考或关键帧辅助；背景细节、动作、表演和时长可能变化，需要检查实际结果 |

当前 Seedance Provider 已映射参考视频、参考图片和首尾帧，GPT Image 支持图片编辑；这些是制作输入能力，**没有经过真实角色替换成片验证，也不保证无损换人或精确动作复制**。专用海艺编辑能力要查询实时模型/工具配置；可经原海艺技能完成已可用的操作再导入 Hypit。如果严格编辑不可用，会说明实际缺口和重建取舍，不能把重建宣称为只改变角色。

准备原视频，以及目标角色的清晰参考图片；多人替换说明“原角色 A → 新角色 X，原角色 B → 新角色 Y”。资产可按现有公共资产库与项目文件夹分类，不必把所有素材搬到同一目录。参考片分析与目标制作文件分别保存，方便同一原片复刻多个角色版本。

使用示例：

- “使用 `$hypit-haiyi` 复刻这段视频，把主角换成我提供的角色，保留剧情、镜头顺序、节奏和原音轨。先分析原片和制作路径，暂不提交生成。”
- “使用 `$video-director` 拆解这段视频，给我角色映射、分镜和替换素材计划。”

制作时会重点检查跨镜头身份、身体/服装、遮挡后恢复、多人互动、道具接触、倒影、背景及音画同步，而不是仅替换脸或检查首帧。小样和重试仍属于付费生成，只在已接受范围内执行。详细约定见 [角色替换制作](skills/hypit-haiyi/references/character-replacement.md)。

### 多版本委托的提示词结构

推荐按“原片 → 独立版本数 → 原角色识别 → 各版映射 → 视觉风格 → 必须保留的剧情/笑点 → 允许改动 → 逐角色台词与音频 → 模型偏好 → 并发与预算”组织委托。可复制 [多版本复刻委托模板](templates/replication-brief.md)，只填写本次实际需要的内容。

工作流将长委托拆成每版、每镜的具体模型请求，避免角色或声音串用。剧情中的发型变化等笑点单独记录，不因“一致性”要求被固定掉。台词、字幕和参考声音按说话回合绑定；指向同一回合的互斥要求先澄清。音频路径需对应当前机器可用文件。

独立成片数量与并发请求上限分别记录；并行制作仍受素材依赖、Runtime/工具能力和账号限流约束。当前 Provider 不含 Wan3，可保留用户备选偏好，但需要核实海艺服务是否实际可用并选择对应执行路径，不能把失败自动当成版权问题或沿用不兼容参数反复提交。详细规则见 [多版本复刻委托](skills/hypit-haiyi/references/multi-version-recreation.md)。

## 可选 MiniMax H3 技能与 Seedance 方法复用

[minimax-h3-opencode-skills](https://github.com/unknowlei/minimax-h3-opencode-skills) 提供六个导演、规划、提示词与审查技能，另依赖 MiniMax 官方的 [h3-prompt-writing](https://github.com/MiniMax-AI/MiniMax-H3/tree/d21241f0a4b3acbb34c97dae47fa417b7065e438/skills/h3-prompt-writing)。目录结构可供 Codex 使用；安装时应放到当前环境的技能目录。它们是提示词指导，安装不提供模型额度或生成服务。可请 Codex 安装社区仓库 `skills/` 下的全部六个技能，并另外安装官方依赖。本仓库的 `install-skill` 不自动安装这些可选依赖，源码 ZIP 也不包含它们。

统一流程吸收的通用方法是：明确每份素材的职责；记录保留、修改与剧情中必须发生的变化；逐镜描述构图、动作过程与结束状态；台词、字幕和声音按角色/事件绑定；提交前检查矛盾与时间可行性。Seedance 默认使用这些约定，保留自己的模型提示词和接口格式。不会将 H3 六段结构、标签、输入限制或原版逐镜确认流程硬套到 Seedance，也不重复询问已确定的分镜。详见 [通用提示词设计](skills/hypit-haiyi/references/prompt-direction.md)。

2026-10-14 的海艺只读查询列出 `minimax-h3` 全能参考、`minimax-h3-frame` 首尾帧与 `minimax-h3-max` 极速首尾帧入口。用户选择 H3 时，可按当前海艺参数配置，通过原海艺技能生成素材，再导入 Hypit；当前自定义 Provider 尚未加入 H3 原生路由。模型列出不代表已实测严格编辑、声音控制或成片效果。全能参考配置的计费说明包含参考视频时长与输出时长，生成前仍须核对实时价格与预算。详见 [H3 可选路径](skills/hypit-haiyi/references/h3-integration.md)。

只想使用外部原版交互导演时，可显式说“使用 `$minimax-h3-creative-director` 编写 H3 提示词”；日常复刻仍从 `$hypit-haiyi` 进入。H3 技能与通用方法可同时存在，不会因安装它们而切换已有账号或默认模型。

## 哪些环节需要付费

根据固定版本的 [Hypit 说明](https://github.com/hypit-ai/hypit/blob/85e01c76716498e6ec5b8bdfb6b374ca67f0195a/README.zh-CN.md)，Hypit 不按人头或渲染次数收费，也不添加水印；模型服务费用由所选服务方收取。

| 环节 | 费用来源 |
| --- | --- |
| 导演/剧本/分镜指导、本地项目编排和渲染 | 没有单独的 Hypit 技能购买费或渲染费；使用本机计算资源 |
| 在 Codex 内创作剧本和操作项目 | 按所用模型/平台的订阅、额度或 API 计费方式，不由 Hypit 另收导演费 |
| 海艺图片、视频、配音、音乐、增强等云端任务 | 按实际功能、模型和账号的海艺额度/价格计费，不能假定所有处理免费 |
| HypiHub 或其他外部模型服务 | 如果另外接入，由相应服务方收费；我们的默认流程不切换到这些服务 |
| 本地运行的渲染、音频处理或本地模型 | 本地处理不产生 Hypit 云端推理费；可能需要额外工具、硬件或存储 |

因此不能说“所有 AI 功能都免费”。当前流程使用你的海艺账号做已支持的云端生成，提交前按实时价格核对；不在文档中承诺固定价格或无限额度。Hypit 的多租户托管/SaaS 和商业再分发场景另受其 [许可证附加条款](third-party/HYPIT-LICENSE) 约束，不能把个人本地使用的收费结论扩展到这些场景。

## 快速使用

需要 Node.js >=22.15。已有 Hypit 和 FFmpeg 时：

```powershell
git clone https://github.com/KorothyFan/hypit-haiyi-workflow.git
cd hypit-haiyi-workflow
node scripts/workflow.mjs setup --hypit-root "D:/tools/hypit" --ffmpeg "D:/tools/ffmpeg/bin/ffmpeg.exe" --ffprobe "D:/tools/ffmpeg/bin/ffprobe.exe"
node scripts/workflow.mjs install-skill
node scripts/workflow.mjs info
node scripts/workflow.mjs init "D:/videos/my-ad"
node scripts/workflow.mjs check "D:/videos/my-ad/haiyi-text-video.svml" --project "D:/videos/my-ad"
node scripts/workflow.mjs plan "D:/videos/my-ad/haiyi-text-video.svrun" --project "D:/videos/my-ad"
```

新机器先准备 Node.js >=22.15、Git、pnpm 10.33.0、FFmpeg/FFprobe。克隆本仓库后，将上面 `setup --hypit-root ...` 那一行替换为：

```powershell
node scripts/workflow.mjs setup --install --ffmpeg "D:/tools/ffmpeg/bin/ffmpeg.exe" --ffprobe "D:/tools/ffmpeg/bin/ffprobe.exe"
```

再继续执行 `install-skill` 等后续命令。`setup --install` 会从上游另行下载 Hypit，固定到 `upstream.json` 指定 commit，不会下载海艺原 Skill，也不会重置其他版本的已有 checkout。详细步骤见 [安装与调用](skills/hypit-haiyi/references/setup.md)。

新任务直接说：**“使用 $hypit-haiyi 制作视频。”** 自动匹配保持开启，但具体选择仍取决于任务描述；显式指定最稳定。安装脚本也给已安装的两个基础技能补充视频路由说明，原文备份到 `.local/skill-backups`，其余内容保留。基础插件更新后可重新运行 install-skill 补回入口说明。

Token 使用环境变量 `HAIYI_API_TOKEN`，或已有海艺登录凭据文件。凭据不会写到仓库。环境示例 `.env.example` 仅用于说明，脚本不会自动加载 `.env`。

完成创作并确认付费范围后：

```powershell
node scripts/workflow.mjs pricing "D:/videos/my-ad/haiyi-text-video.svrun" --project "D:/videos/my-ad"
node scripts/workflow.mjs build "D:/videos/my-ad/haiyi-text-video.svrun" --project "D:/videos/my-ad" --follow
```

**build 会提交真实海艺生成任务并产生费用。** setup、install-skill、init、verify、check、plan 均不提交生成任务。

## 配置与项目分离

全局可发现技能保存统一流程和代码库路径；每个视频项目单独保存 Brief、Treatment、Progress、Sources、Runs 和 Results。工具安装与 Provider 在项目间共用。新会话通过技能与项目文件恢复工作，不依赖旧聊天内容。不要把海艺账号设置当成无限生成预算。

机器路径存在被忽略的 `.local/config.json`，安装技能时另写本机 `local-setup.json`。移动目录后重新 setup 和 install-skill。Git 与打包不会收录这些文件、node_modules、运行时数据库或 Token。

## 验证

```text
node scripts/workflow.mjs verify
node scripts/bundle.mjs
```

verify 编译 Provider、运行 mock tests，在临时独立项目里检查图片/视频 Source 和 plan，最后删除临时项目。plan 使用占位凭据验证路由与参数，不读取真实账号。它不证明真实云端生成、API 可用性或成片质量；这些只有在获准执行真实任务后才能验证。

当前经过 Windows + Node 24 环境验证。入口使用跨平台 Node API，但 macOS/Linux 尚未实机验证。固定版本升级时重新核验模型映射和参数。

## GitHub 代码库

公开源码：[KorothyFan/hypit-haiyi-workflow](https://github.com/KorothyFan/hypit-haiyi-workflow)。

下载源码与技能包：[v0.5.0 预览版本](https://github.com/KorothyFan/hypit-haiyi-workflow/releases/tag/v0.5.0)。此版本吸收 MiniMax 提示词方法用于 Seedance，并说明可选 H3 技能/海艺路径；本地安装与 mock/plan 验证通过，H3 配置只做了只读查询，尚未执行真实付费生成或角色替换成片验证。

代码库包含源码、技能、模板、安装脚本和来源说明。本机配置、运行时数据库与账号凭据均不上传；安装脚本也不会发布 GitHub 仓库或插件市场条目。这里提供本地统一 Skill 入口，原基础插件保留。

## 来源与条款

Hypit 上游为 [hypit-ai/hypit](https://github.com/hypit-ai/hypit)，固定版本见 `upstream.json`。它使用带附加条件的许可证，原文见 [third-party/HYPIT-LICENSE](third-party/HYPIT-LICENSE)；本仓库不重新授权 Hypit 核心或海艺服务。归属说明见 [NOTICE.md](NOTICE.md)。
