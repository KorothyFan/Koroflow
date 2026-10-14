# 当前能力与限制

| Hypit capability | 海艺模型 | Provider 覆盖 |
| --- | --- | --- |
| @hypit/seedance@1#seedance-2.5 | volcengine / doubao-seedance-2-5-260628 | 文生视频、图生视频、参考图/视频/音频、首尾帧 |
| @hypit/gpt-image@1#gpt-image-2 | openai / gpt-image-2.5-flare | 文生图、图生图 |

Seedance 当前适配器的约束为 4–30 秒、480p 或 720p。GPT Image 使用 1K/2K/4K、最多十张参考图；画幅按 Provider 支持范围及海艺实时接口核对。海艺名称与 Hypit capability 是映射关系，不是同名模型性能保证。

Provider 管理素材上传、提交后的任务 id、轮询、下载与生成结果封装。Hypit 管理项目、调度和结果；跨 Build 复用由 Run Candidates 明确指定，不能将缓存存在当作自动复用保证。

FFmpeg/FFprobe 负责本地媒体处理；HTML Provider 和 Managed Chrome 用于合成与渲染。Chrome 是否已经准备就绪要以当前项目 `doctor` 或 Runtime 状态为准。模型需要海艺网络与账号；本地配置不包含离线模型。

海艺 TTS、音乐、视频增强等可以通过海艺原技能准备，再导入 Hypit；尚未作为此 Provider 的 capability。字幕、动效与声音编排也需要针对创作项目实际作者化，模板不自带所有效果。
