# KoroFlow 仓库维护约定

## 仓库和私人工作区

- 看 [README](README.md) 确认本次涉及的入口。[架构](docs/architecture.md) 管本地记录、适配器和实际执行器，[安装指南](docs/laptop-setup.md) 管新机配置。
- 制作任务从用户实际工作区开始。读取该处 AGENTS、当地现行规则、项目 BRIEF/TREATMENT/PROGRESS、当前 revision 和真实回执。这里的模板与示例仅提供可移植方法。
- 私人身份、资产、提示词、账号、路径配置、凭据、运行日志及成片留在用户工作区。发布源码包维护 [显式文件清单](scripts/bundle.mjs)，源自 Hypit 的部分保留 [来源声明](NOTICE.md) 和 [许可](third-party/HYPIT-LICENSE)。

## 维护制作流程

- [koroflow](skills/koroflow/SKILL.md) 负责完整流程。导演、海艺/Hypit、入库和发布分别从各自技能进入。通用规则收敛到[制作规范](skills/koroflow/references/production-standard.md)和[复刻执行流程](skills/koroflow/references/reference-production-runbook.md)，平台差异写入对应适配文档。
- 每版把用户要求和原片关键事件落实到替换方案、资产职责、实际请求及成片证据。按用户约定提供 [HTML 方案与审片](skills/koroflow/references/production-review-experience.md)，页面取当前所选版本及真实文件。
- 正式请求、实际附件、模型档位、参数、费用和授权按[提交预检](skills/hypit-haiyi/references/production.md)核对。已有明确范围继续执行。结果未知时先查原任务。离线检查只确认本地证据和参数。
- 修订沿用 work_id，保留首次交付日期、旧版和实际检查范围。候选、合格交付、用户采用、预约、发布各用对应证据。用户明确验收入库时沿用其选择，操作者独立检查状态照实保留。
- 核心在显式工作区的 .koroflow 保存事件；prepare 保存交接，bridge 导出真实事件。保持旧工程的显式导入和既有台账兼容，避免重新登记或回填虚构状态。适配器以实际支持的输入和模式为准。

## 验证与分发

- 改 Python 核心、预检、运营、安装或分发后，用 Python 3.11+ 运行 `python -X utf8 -m unittest discover -s tests -p "test_*.py" -v`。测试使用临时工作区。
- 改 Provider、执行入口或接入方式后，用 [upstream.json](upstream.json) 固定的 Hypit 执行 `node scripts/workflow.mjs verify`。这是离线 mock、Source 检查和 Run 计划验证。
- 改技能时检查各自入口、相对链接、安装副本和本机覆盖设置。插件元数据在 [plugin.json](plugin.json) 和 [.agents/plugins/marketplace.json](.agents/plugins/marketplace.json)。按源文件清单验证打包。
