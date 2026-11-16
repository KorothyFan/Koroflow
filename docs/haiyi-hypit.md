# 海艺与 Hypit 接入

从 [KoroFlow README](../README.md#海艺hypit-制作) 安装。换机器使用[迁移指南](laptop-setup.md)，具体配置项见 [适配器安装说明](../skills/hypit-haiyi/references/setup.md)。此页说明实际执行器、工作文件与命令。

## 环节和依赖

| 环节 | 用什么 |
| --- | --- |
| 策划 | [video-director](../skills/video-director/SKILL.md) 交付剧本、分镜和参考拆解，可单独安装使用 |
| 生成 | Provider 将 Hypit Seedance / GPT Image 请求映射为海艺图片或视频 API。可直接使用本机合法账号授权。当前覆盖见[能力表](../skills/hypit-haiyi/references/capabilities.md) |
| 补充媒体 | 海艺原技能提供单独登录、直连模型及语音、音乐、增强等按需入口。需要时按原技能实际能力运行并将文件导入工程 |
| 编排 | 仓库 [upstream.json](../upstream.json) 固定的 Hypit 管 Source、Run、Candidates、Build 和本地渲染。准备 Node、FFmpeg/FFprobe 及所选依赖 |

制作策略从用户工作区和当前委托读取。参考复刻先按[统一执行流程](../skills/koroflow/references/reference-production-runbook.md)确定职责、保留内容、原片与必要资产，再按[提示词设计](../skills/hypit-haiyi/references/prompt-direction.md)写实际内容。选择原音轨、台词或字幕属于本次方案。可选的 [H3 指南](../skills/hypit-haiyi/references/h3-integration.md)说明如何单独验证与接入该模型。

## Hypit 工程

从已经 setup 的仓库初始化一个新目录：

```powershell
node scripts/workflow.mjs init "D:/videos/my-video"
node scripts/workflow.mjs check "D:/videos/my-video/haiyi-text-video.svml" --project "D:/videos/my-video"
node scripts/workflow.mjs plan "D:/videos/my-video/haiyi-text-video.svrun" --project "D:/videos/my-video"
```

示例项目用于检查结构和计划。真实制作先按本次需求更新 Source、Run、Runtime 和依赖，已有工程沿用原目录。BRIEF 保存用户约束，TREATMENT 保存制作方案，PROGRESS 保存当前采用文件、Build、状态和剩余授权。正式台词由采用的 Source 保存。

用 check / plan 核对实际素材、模型参数与请求数量。如需实时报价，运行 pricing。按[执行预检](../skills/hypit-haiyi/references/production.md)记录费用和范围。已有明确范围内可执行：

```powershell
node scripts/workflow.mjs build "D:/videos/my-video/haiyi-text-video.svrun" --project "D:/videos/my-video" --follow
```

**build 可提交真实生成并产生费用。** 本地渲染、云端模型和 Codex 各按所用服务或设备计费。参数、价档与费用以实际路线的校验和报价为准。等待窗口结束后继续查原 Build，回执保存在项目。采用已核准输入时在 Run 的 Candidates 明确选择。

## 配置和验证

配置在仓库 .local 与安装技能的 local-setup.json。环境变量 `HAIYI_API_TOKEN` 或既有海艺安全存储提供凭据，使用方法见[适配器安装说明](../skills/hypit-haiyi/references/setup.md)。`.env.example` 是变量说明，应用读取进程环境。项目分别保存素材、原生结果与检查。

`node scripts/workflow.mjs verify` 编译 Provider，运行离线 mock，再于临时项目验证图片和视频 Source / Run。真实链路工作状态依实际执行回执与成片检查。

来源为 [hypit-ai/hypit](https://github.com/hypit-ai/hypit)。分发与服务用途见[来源声明](../NOTICE.md)和 [Hypit 许可](../third-party/HYPIT-LICENSE)。
