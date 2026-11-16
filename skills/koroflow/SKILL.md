---
name: koroflow
description: 统筹视频制作、参考复刻、跨平台续作、审片、版本交付和发布记录。适用于从委托推进到成片或接手已有作品。单独剧本用 video-director，单独平台操作用实际平台技能。
---

# KoroFlow 视频生产

## 恢复本次委托

从用户指定工作区读取当地 AGENTS、现行制作规则和本次 BRIEF/TREATMENT/PROGRESS。接手时定位已有 work_id、当前 revision、实际请求与原任务状态。能够在旧工程接续时沿用旧工程。核心记录缺失时按[旧记录接入](references/workflow.md)核对并按需导入。

以本次用户要求决定做到哪里。找素材、分析、写稿、生产、修订、入库和发布各按委托范围推进。已有授权覆盖的制作继续执行。准备新机器时用相邻 `scripts/migration.py` 和[配置模板](assets/templates/machine.example.json)检查路径、工具与核准资产。

## 依据本次工作推进

| 工作 | 入口和完成依据 |
| --- | --- |
| 策划与参考复刻 | 从[制作路径](references/production-paths.md)选实现方式。复刻用[执行流程](references/reference-production-runbook.md)和[批次交接表](assets/templates/reference-production-batch.md)，逐版固定原片因果、角色职责、状态触发、元素和声音。调用已安装 video-director 准备原创或分镜 |
| 准备资产与实际请求 | 按[制作规范](references/production-standard.md)核对本版必要资产、真实槽位和最终正文。落实本地画幅、声音、进度、档位和费用。使用实际接口或[适配器](references/adapters.md)，海艺/Hypit 交 hypit-haiyi。可用[离线检查单](assets/templates/request-preflight.example.json)引用最终请求文件 |
| 提交与恢复 | 在本次授权内按依赖提交，立即保存请求、真实任务号和回执。结果未知先查原任务。纯图重建用[多图方法](references/production-paths/image-reference-rebuild.md)，参考为外观绑定时按实际能力描述 |
| 审片与修订 | 保存原生结果，对齐原片事件和用户指定项。用真实成片分别验证技术、完整动作、听审、口型和画内元素。未查项留 `not_checked`。按问题做最小修订并保留旧版 |
| 交付与运营 | 明确当前实际文件、revision、检查范围和用户采用。整理/统计/发布按本地流程和 koro-operations，沿用原 work_id 与真实事件 |

用户或工作区选择 HTML 时，按[方案与审片协作](references/production-review-experience.md)填[空模板](assets/templates/production-plan-review.html)。每项指定变更在方案、素材、实际请求、成片和现版页面里对应。只有材料、方案或候选时，页面显示实际状态。只交接制作方法可用[轻量模板](assets/templates/reference-task-handoff.md)。

## 命令与记录

`python -X utf8 scripts/workflow.py --workspace <实际工作区> --help`。配置也可由 KOROFLOW_WORKSPACE 指定。核心在 .koroflow 保存本地事件。route 是能力查询，prepare 保存请求或发布交接，record-task 记真实执行，register/review/deliver 管实际文件、检查与交付，bridge 导出工作区真实事件。范围与数据格式见[记录与执行](references/workflow.md)。

质量交付核对实际文件指纹和必检证据。可按用户要求提供候选并保留未完成项。采用与发布沿用用户选择和平台证据。已有汇总、手工字段、私人偏好和平台凭据继续由当地配置管理。
