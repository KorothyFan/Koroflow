---
name: koro-operations
description: 核对既有视频工程、作品版本、入库、产量统计、发布账号与台账。用于收录已选作品、查看实际产出和规划或回填发布。完整制作由 koroflow 统筹。
---

# KoroFlow 作品与发布管理

从工作区 AGENTS、运营配置和本次涉及的真实项目记录进入。沿用 work_id、首次交付与当前 revision。入库、统计及发布在各自授权范围操作。

## 按用户要求执行

| 请求 | 作法 |
| --- | --- |
| 用户明确验收并要求入库 | 处理本批实际选中的文件。沿原 work_id 更新 revision、采用依据和本批清单。复用已有身份与检查，文件被替换或版本不清时局部核对。用户验收和操作者检查状态各按证据记录 |
| 统计、整理或核对旧工程 | 按[作品与统计](references/records.md)使用真实版本和刷新入口。成功生成按任务号去重，独立交付按 work_id 去重。统计快照带更新时间，人工字段按稳定编号保存 |
| 挑片、预约、发布或回填 | 按[发布与恢复](references/publication.md)核对选定文件、账号身份、完整历史与待处理发布。用实际授权执行器完成后留平台证据。待发、预约、已发和结果未知按事实记录 |

桌面目录与硬链接用于定位/分类。移动、改名和复制按相同文件与作品记录追溯。制作目标、账号配置、用户采用及发布证据使用各自的数据源。

## 本地核对工具

Python ≥3.11。配置优先取 `--config`、KORO_OPERATIONS_CONFIG 或 `references/local-setup.json` 指向的本机文件。安装与配置见[说明](references/setup.md)。

```text
python -X utf8 <本技能>/scripts/operations.py doctor --config <本地配置>
python -X utf8 <本技能>/scripts/operations.py check --config <本地配置>
python -X utf8 <本技能>/scripts/operations.py snapshot --config <本地配置> --date YYYY-MM-DD
python -X utf8 <本技能>/scripts/operations.py plan --config <本地配置> --request <发布请求.json>
```

check 按记录核对，必要时加 --hash。它们是离线读操作，实际列表、预定和发布需要现有执行器。需要接入核心时按 [KoroFlow 工作流](../koroflow/references/workflow.md)显式导入与 bridge。用户已有的本地入库和刷新入口按其适用范围使用。
