# Hypit + 海艺视频工坊

统一的 Codex 视频生产技能和代码库：海艺负责图片/视频素材生成，Hypit 负责分镜、时间线、素材复用和成片渲染。已安装的两个基础插件可以保留；从 `$hypit-haiyi` 统一进入工作流。

## 提供的内容

- `skills/hypit-haiyi/`：可安装统一技能，自动匹配视频制作请求，写入默认海艺流程与跨任务使用约定。
- `packages/provider-haiyi/`：TypeScript Provider，直接连接海艺 OpenAPI，覆盖 Seedance 2.5 和 GPT Image 2.5 Flare。
- `templates/project/`：图片、四秒视频、Runtime Profile 模板。
- `scripts/workflow.mjs`：复用/安装固定版本 Hypit、配置 FFmpeg、安装技能、新建独立项目、检查/计划/生成命令。
- `scripts/bundle.mjs`：仅按白名单打包源码、技能和文档。

整合提升工作组织、连续性与可编辑性，不改变模型基础画质。TTS、音乐及增强等尚未绑定到 Provider，可以通过海艺原技能获取素材再导入。此仓库是集成源码与技能，不是离线模型或完整独立二进制安装包。

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

新机器先准备 Git、pnpm 10.33.0、FFmpeg/FFprobe，将第一条改为 `setup --install`。脚本固定 Hypit 版本到 `upstream.json` 指定 commit，不会重置其他版本的已有 checkout。详细步骤见 [安装与调用](skills/hypit-haiyi/references/setup.md)。

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

下载源码与技能包：[v0.1.0 预览版本](https://github.com/KorothyFan/hypit-haiyi-workflow/releases/tag/v0.1.0)。这是首个配置与 mock/plan 验证版本，尚未执行真实付费生成验证。

代码库包含源码、技能、模板、安装脚本和来源说明。本机配置、运行时数据库与账号凭据均不上传；安装脚本也不会发布 GitHub 仓库或插件市场条目。这里提供本地统一 Skill 入口，原基础插件保留。

## 来源与条款

Hypit 上游为 [hypit-ai/hypit](https://github.com/hypit-ai/hypit)，固定版本见 `upstream.json`。它使用带附加条件的许可证，原文见 [third-party/HYPIT-LICENSE](third-party/HYPIT-LICENSE)；本仓库不重新授权 Hypit 核心或海艺服务。归属说明见 [NOTICE.md](NOTICE.md)。
