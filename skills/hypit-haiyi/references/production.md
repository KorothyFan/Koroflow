# 执行、复用与交付

制作前使用已安装 Hypit 的对应参考：

- 项目边界与跨会话记录：`references/creation/project-files.md`。
- 图片方向：`references/playbooks/craft/image-direction.md`；视频方向：`references/playbooks/craft/video-direction.md`；连续角色与道具：`references/playbooks/craft/generated-dependencies.md`。
- Source / Run：`references/production/authoring.md`、`runs.md`；检查 `plan` 后仅执行所需生成。
- 付费范围、Build id、超时及失败恢复：`references/production/builds.md`。
- 本地程序准备：`references/environment/local-tools.md`；Provider 调整：`references/environment/model-and-provider.md`。
- 渲染、看成片与编辑预览：`references/production/rendering.md`、`review.md`、`studio.md`。

`PROGRESS.md` 至少保留项目根目录、Source/Run 路径、Runtime Profile、当前 Build id、已接受 Output 的名称及对应 Result、剩余工作与授权范围。不要写入凭据或带签名的私有素材 URL。

执行脚本不自动重试生成。观察超时后查询 Runtime/Build，不能再调用 `build` 来“继续等待”。处理失败时保留成功素材，将要复用的 Output 写入新的 Run Candidates，再检查剩余请求。已经提交的请求若无法确定状态，先查询海艺任务记录。

交付前观看并听完真实最终文件；留意人脸/手/产品变形、镜头间一致性、跳帧与音画同步、字幕遮挡、响度和时长。生成结果需修复时，先用可编辑 Source 或本地处理解决适合的问题；模型重生成按已授权预算执行。现有 mock/plan 验证不等于画面或声音质量验证。
