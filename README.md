# KoroFlow · 可复用的视频生产与运营工作流

将**质量规范 → 创作与制作 → 检查与修订 → 整理交付 → 每日统计 → 发布与回填**连成一套可复用流程。每个独立作品有稳定的 `work_id`；跨平台生成、改声音、换版本、重新交付都沿用它。

制作平台可以是海艺、无限画布或其他生成服务；发布可以通过实际可用的 API、MCP、浏览器或人工执行。KoroFlow 保存素材职责、文件指纹、质量结果、任务证据和状态，平台执行通过适配器交接。现有海艺 / Hypit 路径保留。

当前分支为 **0.7.0 开发版**。已经发布的下载版见 [GitHub Releases](https://github.com/KorothyFan/Koroflow/releases)，下载旧 Release 不会自动包含本分支的新能力。

## 当前能做什么

| 环节 | 当前实现 | 使用边界 |
| --- | --- | --- |
| 导演与制作规范 | Brief、分镜、角色/声音映射、参考职责及质量清单 | 沿用用户当前规范；严格复刻不改写原剧情 |
| 制作 | 海艺图片/视频 Provider、Hypit 编排与本地渲染 | 需要相应工具、账号与额度；编辑/音频可通过海艺原技能交接 |
| 版本与质量 | SHA256 绑定修订及检查记录，未完成必检项阻止交付 | 检查结果来自真实人工或工具检查，核心不会自动看画面或听声音 |
| 整理与统计 | 独立作品、首交付日、生成/交付/采用分开；本地事件日志 | 不由文件存在推断交付，不把修订重复算产量 |
| 兼容原工程 | 旧记录预检、显式导入、幂等导出统计事件及发布信息 | 不搬迁原工程；原 Excel 仍由既有刷新器维护，手填字段不改动 |
| 发布 | 账号与历史预检、文件/请求固定、本地任务占用、状态与证据记录 | 尚无内置社交平台发布执行器；准备任务不代表上传成功 |
| 扩展平台 | API / MCP / browser / CLI / manual 的能力声明与交接契约 | 新平台需配置并验证真实执行工具；声明能力不代表已经接通 |

同一账号的同一作品或相同文件已有占用时，核心阻止重复分配；提交结果未知时保留 `result_unknown`，先核实远程结果。`prepared`、`submitted`、`scheduled` 和 `published` 分别记录，发布状态也不自动冒充用户采用。

## 四个技能如何配合

| 技能 | 职责 |
| --- | --- |
| `koroflow` | 统一入口，协调规范、平台选择、制作、检查、交付、统计与发布 |
| `video-director` | 剧本、分镜、参考片拆解与角色替换方案 |
| `hypit-haiyi` | 海艺 / Hypit 的具体制作路径 |
| `koro-operations` | 读取既有工程、账号及统计快照，发布前核对历史 |

新任务可以说：“使用 `$koroflow`，按我的制作规范推进这个视频。”指定其他平台时保留选择，不自动切回海艺。只做前期文字方案不会提交媒体生成。

## 先安装独立工作流核心

需要 Node.js ≥22.15 安装技能、Python ≥3.11 运行本地记录核心。Windows Python 如缺 IANA 时区数据，安装 `tzdata`。这一部分无需 Hypit、海艺账号或 FFmpeg。

```powershell
git clone https://github.com/KorothyFan/Koroflow.git
cd Koroflow
node scripts/workflow.mjs install-skill --core-only
python -X utf8 scripts/koroflow.py --workspace "D:/videos" init
python -X utf8 scripts/koroflow.py --workspace "D:/videos" adapters
python -X utf8 scripts/koroflow.py --help
```

`init` 在指定工作空间创建 `.koroflow`，保存本地配置与 UUID 事件，不搬迁素材或视频工程。已有工作空间拒绝覆盖。按本地需求编辑其中的 `quality.json`、`targets.json` 和 `adapters.json`；公开示例不预填私人账号或每日目标。

新作品先在独立工程目录准备 Brief 和素材，用 [作品清单](skills/koroflow/assets/templates/work.example.json) 填写真实路径、角色及参考职责，再 `create --manifest`。输出用 `register` 登记版本，实际检查后 `review`，满足必检项才能 `deliver`；`report --date` 查看该核心日志覆盖的统计。完整命令与旧工程衔接见 [工作流使用说明](skills/koroflow/references/workflow.md)。

已有工程继续由原管理工具读取。需要纳入核心时先生成 `operations check --hash` 报告，再显式 `import-legacy`，保持原编号和首交付日期；不能重新登记为当天的新作品。历史只有成片、没有工程的文件继续由原台账管理。

## 接上海艺 / Hypit 制作

本仓库提供整合技能、Provider 和安装脚本，**不包含完整 Hypit 工具、海艺原 Skill、离线模型、账号或额度**。

```powershell
node scripts/workflow.mjs setup --hypit-root "D:/tools/hypit" --ffmpeg "D:/tools/ffmpeg/bin/ffmpeg.exe" --ffprobe "D:/tools/ffmpeg/bin/ffprobe.exe"
node scripts/workflow.mjs install-skill
node scripts/workflow.mjs info
```

没有 Hypit 时可用 `setup --install` 下载 `upstream.json` 固定版本；还需 Git、pnpm 及本地媒体依赖。默认 `install-skill` 安装上面的四个技能，并按原逻辑准备 Hypit 技能；海艺原 Skill 仍从其提供渠道单独安装。只用 Provider 已支持的图片/视频接口且已有有效 Token 时，可以不安装海艺原 Skill；登录、音频、音乐或其他补充能力可能需要它。

`HAIYI_API_TOKEN` 或海艺原技能的登录凭据留在本机。提交前通过原制作工具检查参数、模型、价格与授权范围；`build` 会提交真实付费任务。详情见 [海艺 / Hypit 安装与制作](docs/haiyi-hypit.md)。整合改善流程与检查，不改变模型基础画质，也不保证严格复刻必然成功。

## 添加其他制作和发布平台

复制 [适配器示例](skills/koroflow/assets/templates/adapter.example.json) 到工作空间 `adapters.json`，填写能力与实际交接方式。接入顺序：核实真实 API/MCP/浏览器工具 → 配置凭据于本机 → 验证输入输出和任务查询 → 声明已验证能力 → 按真实回执登记任务。未配置平台不参与路由，缺少所需能力时不会偷偷降级或改模型。

本地核心的 `route` 与 `prepare` 只检查并保存交接记录，**不会执行网络请求**。现有真实生成由海艺/Hypit 工具执行，新制作平台与发布平台也需各自执行器。不要把适配器 JSON 里的 `external` 或 `implemented` 状态当成实时登录/连接证明。见 [适配器契约](skills/koroflow/references/adapters.md) 与 [架构与边界](docs/architecture.md)。

原账号/设备工具和统计刷新器可以继续使用。[运营模块](docs/operations.md) 的 `plan` 核对已有完整历史，核心 `prepare` 再保存新任务占用；两者配合，不能只查新日志就忽略旧发布记录。

## 配置、隐私与分发

源码、工具安装、公共资产、每条视频工程和本地记录分开。`.local` 保存本机工具路径，用户工作空间的 `.koroflow` 保存工作记录；凭据、账号注册表、设备信息、素材、成片及本机路径索引不进入 Git 或源码 ZIP。安装技能不会迁移生产数据，也不会启动历史任务。

插件目录采用根 `plugin.json` 和 `.agents/plugins/marketplace.json`。`scripts/bundle.mjs` 按白名单生成源码与技能 ZIP；为兼容，压缩包内顶层目录仍叫 `hypit-haiyi-workflow`。单独安装导演或运营技能仍支持 `--director-only` / `--operations-only`。

## 开发验证

```powershell
python -X utf8 -m unittest discover -s tests -p "test_*.py" -v
node scripts/workflow.mjs verify
node scripts/bundle.mjs
```

Python 测试在临时工作空间验证质量门槛、修订/统计、未知任务、发布查重、旧记录兼容及独立安装/ZIP。`verify` 编译 Provider、运行离线 mock，并检查固定版 Hypit 的 Source 与 plan；不提交付费任务，不证明云端实时可用或成片质量。当前以 Windows 环境验证，macOS/Linux 未实机验证。

变更见 [CHANGELOG](CHANGELOG.md)。Hypit 上游是 [hypit-ai/hypit](https://github.com/hypit-ai/hypit)，固定版本见 `upstream.json`；许可证原文与附加条件见 [HYPIT-LICENSE](third-party/HYPIT-LICENSE)，归属见 [NOTICE.md](NOTICE.md)。本仓库不重新授权 Hypit 或各平台服务，不是官方联合插件。
