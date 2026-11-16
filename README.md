# KoroFlow

KoroFlow 用于持续制作、复刻和修订视频。它把本次委托、实际生成请求、成片检查和选定版本留在同一个项目里。换聊天、机器或制作平台时，可以沿原作品接着做。

仓库包含四个 Codex 技能、离线预检与记录工具，以及海艺/Hypit 适配器。私人素材、声音、偏好、运行记录和账号由各自工作区管理。

[开始使用](#开始使用) · [制作与审片](#制作与审片) · [工具入口](#工具入口) · [开发与验证](#开发与验证)

## 开始使用

已发布版本为 [v0.7.4 源码与技能包](https://github.com/KorothyFan/Koroflow/releases/download/v0.7.4/koroflow-v0.7.4-source.zip)。当前源码可包含发布包之后的更新。换机器时按[安装与迁移指南](docs/laptop-setup.md)恢复对应项目与配置。

先准备 Git、Node.js ≥22.15 和 Python ≥3.11。Windows 环境缺少 IANA 时区数据时可安装 `tzdata`。

```powershell
git clone https://github.com/KorothyFan/Koroflow.git
cd Koroflow
node scripts/workflow.mjs install-skill --core-only
python -X utf8 scripts/koroflow.py --workspace "D:/my-video-workspace" init
```

`init` 创建 .koroflow 初始配置。已有作品恢复原工程和 work_id，按[旧记录接入方法](skills/koroflow/references/workflow.md)核对和按需导入。

| 技能 | 进入时机 |
| --- | --- |
| [koroflow](skills/koroflow/SKILL.md) | 完整制作、已有作品续作、跨平台协作 |
| [video-director](skills/video-director/SKILL.md) | 参考片分析、角色替换方案、剧本和分镜。可用 `install-skill --director-only` 单装 |
| [hypit-haiyi](skills/hypit-haiyi/SKILL.md) | 用户已选择海艺/Hypit，需要准备并执行真实制作 |
| [koro-operations](skills/koro-operations/SKILL.md) | 检查既有项目、入库、产量统计和发布预检。可用 `install-skill --operations-only` 单装 |

## 制作与审片

开始时读工作区 AGENTS、最新本地规则及项目 BRIEF/TREATMENT/PROGRESS。继续制作时定位当前选定版本和远程任务状态。可用一句话限定当前工作，例如「用 $koroflow 分析这段参考，做替换方案，先给我看方案」。

| 阶段 | 留下的依据 |
| --- | --- |
| 原片与方案 | 原片来源、看听范围、开场与遮挡、关键动作因果、反应和结尾。本版角色职责、状态、声音和元素替换 |
| 资产 | 核准的身份、开场、道具或状态图，明确各自负责的内容和检查结果 |
| 请求和提交 | 实际附件号位、文件 SHA256、最终提示词、模式、精确模型与价档、输出参数、报价和本次授权。提交后保留真实任务号与回执 |
| 成片与修订 | 保存原生文件。检查实际画幅和解码，按原片事件看完整动作，实际听声音并核对口型。针对偏差做最小修订 |
| 交付与运营 | 当前 revision、实际文件、检查范围和用户决定。候选、交付、采用、预约与已发布各有证据 |

使用[复刻执行流程](skills/koroflow/references/reference-production-runbook.md)和[批次交接表](skills/koroflow/assets/templates/reference-production-batch.md)。用户需要 HTML 时，从[空模板](skills/koroflow/assets/templates/production-plan-review.html)建立方案与审片入口，更新真实原片、现版、旧版与检查范围。按[方案与审片协作约定](skills/koroflow/references/production-review-experience.md)在同一版本里追踪每项要求。

[制作路径](skills/koroflow/references/production-paths.md)包括原视频参考、解读复写、场景资产驱动、原音轨保留、声音修订、连续漫画与外部成片。涉及持久状态、遮挡或道具归属时使用[状态资产方法](skills/koroflow/references/production-paths/state-and-prop-continuity.md)。各路径按本次素材、接口和委托组合使用。

## 工具入口

### 本地记录与请求预检

```powershell
python -X utf8 scripts/koroflow.py --workspace "D:/my-video-workspace" --help
python -X utf8 scripts/migration.py --config "<本地机器配置.json>" --request "<请求检查单.json>"
python -X utf8 scripts/operations.py --help
```

- [核心记录](skills/koroflow/references/workflow.md)保存 work_id、素材、任务状态、文件指纹、修订和质量检查。route 和 prepare 在本地检查能力与准备交接。
- [请求检查单](skills/koroflow/assets/templates/request-preflight.example.json)可引用待提交的实际 payload 文件。预检按本地配置核对画幅、原生音频、参考模式、附件槽位和文件指纹。启用对应规则后还可查上传 URL 的一致性，以及完整替换图是否有匹配指纹的审查记录。检查结果给出实际 payload 的内容指纹。
- [运营 CLI](docs/operations.md)核对旧工程、账号、既有统计和发布历史。实际发布和预约使用已连接的执行工具，完成后记录平台证据。库存、统计与 Excel 刷新可沿用本地流程。

离线预检能发现参数和证据不一致。上传远端归属、模型能力与价格仍依真实回执或接口查询，成片质量由实际结果检查。

### 海艺/Hypit 制作

采用仓库 [upstream.json](upstream.json) 固定的 Hypit 版本。已有依赖时在仓库运行：

```powershell
node scripts/workflow.mjs setup --hypit-root "D:/tools/hypit" --ffmpeg "D:/tools/ffmpeg/bin/ffmpeg.exe" --ffprobe "D:/tools/ffmpeg/bin/ffprobe.exe"
node scripts/workflow.mjs install-skill
node scripts/workflow.mjs info
```

缺少 Hypit 时可按[接入指南](docs/haiyi-hypit.md)使用 `setup --install`。制作时先用 check / plan 预检，按需要查询 pricing，再在本次授权内执行 build。查[实际适配能力](skills/hypit-haiyi/references/capabilities.md)确认支持的模型、档位和参数。直连海艺的请求与 Hypit 的 Source / Run 按各自实际执行路径存证。

### 数据位置

| 位置 | 内容 |
| --- | --- |
| `skills/` 与 `docs/` | 通用工作流、技能入口、适配与记录文档 |
| `packages/provider-haiyi/` | Hypit 对接海艺的 Provider |
| `templates/` | 新 Hypit 工程示例和通用表单 |
| 私人项目与 .koroflow | 素材、实际请求、回执、媒体、审片、交付和事件 |
| 仓库 .local | 工具路径与本地安装配置 |

## 开发与验证

```powershell
python -X utf8 -m unittest discover -s tests -p "test_*.py" -v
node scripts/workflow.mjs verify
node scripts/bundle.mjs "<临时源码包.zip>"
```

测试覆盖本地记录、请求预检、旧记录、隔离安装和分发。verify 使用固定版本 Hypit 运行 Provider mock、Source 检查与 Run 计划。两者均不提交媒体生成。修订源码与技能请按[仓库约定](AGENTS.md)。

[架构](docs/architecture.md) · [完整制作规范](skills/koroflow/references/production-standard.md) · [更新记录](CHANGELOG.md) · [来源与条款](NOTICE.md)
