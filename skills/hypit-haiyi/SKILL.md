---
name: hypit-haiyi
description: 海艺与 Hypit 的视频制作适配技能。用于已选路线的参考复刻、生成资产、Source/Run 编排与渲染。跨平台制作和运营由 koroflow 统筹，单独海艺媒体操作使用 haiyi-aigc。
---

# 海艺与 Hypit 制作

## 找到实际执行器

从 `references/local-setup.json` 定位仓库 `scripts/workflow.mjs`、Hypit 安装和海艺技能。缺配置读[安装与调用](references/setup.md)。沿用用户已选路线、账号和价档。适配器支持范围见[能力](references/capabilities.md)，当前平台参数与报价以所用入口核实。对海艺的其他工具使用实际安装的 haiyi-aigc。

读取本地制作 AGENTS、适用规则和项目 BRIEF/TREATMENT/PROGRESS、采用的 Source/Run、已选 Candidates 与 Runtime 状态。新 Hypit 项目用 init 放在本次工作区，工具和 Provider 共用，项目数据各自保存。

## 从方案到本版实际输入

- 参考复刻用[角色替换工作流](references/character-replacement.md)和[提示词方向](references/prompt-direction.md)。原片负责已有动态，图负责其获准的身份、外观或状态。原片、参考图和真实首尾帧按当前能力绑定。各版本逐人适配比例、材质、肢体、接触和发声。
- 新制作按需要接续 video-director 的方案；按已安装 Hypit 的相关创作与模型参考写 Source。具体资产按本次需求上传。复用已接受素材时在 Run 中明确选择；参考图不合格先处理。
- 用户或本地规则选择指定项或 HTML 时，把对应修订贯穿实际图、素材槽位、最终正文、参数和当前结果。H3 专用规则只看 [H3 可选路径](references/h3-integration.md)。

## 预检、执行、核对

1. 按[执行与复用](references/production.md)检查最终 Source/Run、真实附件映射、模型档位、原生画幅/声音和范围。使用 check、plan，以及所需的 pricing 或 doctor。已有最终 payload JSON 时用 koroflow 的离线检查单引用该文件，按实际媒体字段核对。音频依当地约定，`generateAudio: true` 在需要原生声音的 Seedance 请求上显式生效。
2. 在本次已授权范围执行 build 或所选平台提交。保留真正的请求、Build/任务号和回执。等待窗口关闭或结果未知时查询原任务；凭据或 Worker 需要调整时先确认活动任务。使用本机安全存储的凭据。
3. 保存原生输出。按实际看听范围核对完整动作、声音、口型、标题/字幕政策和最终编码。只按授权处理修订或本地渲染，沿同一 work_id 更新 PROGRESS、当前 revision 与审片入口。

`verify` 运行离线 Provider mock、Source 检查与计划。作品记录、入库和发布按 koroflow / koro-operations 的现有配置执行。
