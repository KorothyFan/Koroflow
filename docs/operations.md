# KoroFlow 制作、统计与发布管理

0.6.0内部第一版将现有生成技能与作品管理连接。可安装为技能，也提供根plugin.json及仓库市场目录。它不是开箱即用的云手机发布器：生成依赖、现有统计工具、魔云腾/比特连接及账号授权由本地环境提供。

## 当前可执行能力

| 命令 | 做什么 | 结果边界 |
|---|---|---|
| init | 创建本地路径配置，拒绝覆盖 | 不创建或迁移视频工程 |
| doctor | 检查目录和本地账号注册表 | 不检查平台登录 |
| check / check --hash | 检查作品元数据、真实事件、选定版本；可加指纹 | 只覆盖具备发布信息的工程，不替代历史台账 |
| accounts | 输出稳定账号ID及最近观察 | 本地快照可能过时 |
| snapshot --date | 读取原统计汇总及更新时间 | 不刷新，不重新定义生成/交付/采用口径 |
| plan | 核对作品、账号、品类、指纹、历史任务及预约时间 | 不占用、不上传、不预约、不写回台账 |

实际制作继续使用`hypit-haiyi`及导演技能。真实发布与回填通过用户环境已有工具执行；本版把步骤和证据约定固化为技能参考，没有内置云手机API执行器或Excel写入引擎。

## 安装与本地使用

需要Python 3.11+；若Windows Python缺少IANA时区数据，可安装tzdata。仓库安装命令另需Node.js >=22.15。仅安装管理模块不要求海艺、Hypit或FFmpeg：

```powershell
node scripts/workflow.mjs install-skill --operations-only
python -X utf8 scripts/operations.py init --config .local/operations.json --workspace "D:/my-videos"
python -X utf8 scripts/operations.py doctor --config .local/operations.json
python -X utf8 scripts/operations.py check --config .local/operations.json
python -X utf8 scripts/operations.py snapshot --config .local/operations.json --date 2026-10-20
python -X utf8 scripts/operations.py accounts --config .local/operations.json
```

按真实目录修改生成的配置，并补上本地创作偏好、账号状态快照等路径。路径相对配置文件定位。`templates/operations/`提供脱敏示例；示例账号和未来时间不可直接当成实际排期。

将选好的work_id、稳定account_id、文案、封面与带时区时间写入本地请求：

```powershell
python -X utf8 scripts/operations.py plan --config .local/operations.json --request .local/publication-request.json
```

输出为JSON，返回码0/1/2分别表示本地无错误、有记录错误、调用失败。plan通过不能证明账号能发布，也不会阻止两个并发执行器同时提交；实际执行层须在提交前持久化任务占用并串行核对。请求和检查报告保留本地，不直接提交公开仓库。

## 插件分发

仓库根`plugin.json`是portable Agent Plugins入口，包含三个技能：hypit-haiyi、video-director、koro-operations。`.agents/plugins/marketplace.json`提供仓库市场来源。参考[官方打包说明](https://developers.openai.com/plugins/build/plugins)。

可用支持插件市场的客户端注册本仓库：

```text
codex plugin marketplace add KorothyFan/hypit-haiyi-workflow
codex plugin add koro-workflow@koro-workflow-plugins
```

开发分支测试时指定实际分支`--ref <branch>`。再按客户端插件目录流程安装并在新聊天测试。市场登记、客户端安装和UI激活是分别验证的步骤；manifest和离线测试通过不代表已完成客户端安装验证。

源码ZIP由`node scripts/bundle.mjs`生成，按白名单收录插件元数据、技能、脚本、测试、模板和归属说明。没有MCP连接文件或密钥占位执行器；本地授权不包含在包里。

## 数据约定

- work_id是独立作品身份，修订共享，原始生成任务另计。路径和SHA256用于选版与去重，文件夹名不等同发布证据。
- 制作目标与发布账号注册表分别保存；本次只发一条或账号退出不自动改变制作要求。
- 生成、交付、采用保留原口径。历史人工完成下限仍来自原统计快照，管理检查器不伪造工程补齐它。
- 已预约、已发布、结果待核实底层状态分开；预约能否在台账显示已发布按用户配置，不能抹掉实际时间与证据边界。
- 用户手填发布字段按稳定记录编号保留；Excel行删除、排序或筛选不应改变作品关联。
- 同一账号同作品/文件已有非失败任务时先核实，不能因连接丢失自动重发。

完整执行约定见技能的[作品与统计](../skills/koro-operations/references/records.md)、[发布与恢复](../skills/koro-operations/references/publication.md)。

## 验证与下一阶段

```text
python -X utf8 -m unittest discover -s tests -p "test_*.py" -v
node scripts/bundle.mjs
```

隔离测试覆盖修订去重、选定文件丢失、目录不等于采用、预约时区、退出账号、历史重复及未知结果等。分发测试验证独立安装、ZIP白名单和解压后运行。CI在Windows/Linux进行离线测试，实际平台操作尚未由这些测试证明。

本版源码ZIP还通过了隔离配置下的Codex CLI市场注册与插件安装，三个技能均被识别；未验证桌面UI激活或真实平台执行。

下一阶段按日常真实委托接入正式平台执行器、跨进程任务占用和台账回填适配器，再增加自动选片与发布后数据观察。现有只读检查可以先用于真实项目；发现记录不完整时报告，不自动修订历史数据。
