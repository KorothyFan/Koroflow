# 来源与范围

本代码库为用户的 Hypit + 海艺集成工作流：统一 Skill、自定义海艺 Provider、配置模板与辅助脚本。

Hypit 上游：https://github.com/hypit-ai/hypit 。选定 commit：85e01c76716498e6ec5b8bdfb6b374ca67f0195a。© 2026 Hypit.AI。模板采用 Hypit 的公开作者接口，Provider 采用 Hypit 的公开扩展接口；完整 Hypit 核心不包含在此源码包中，setup --install 按 upstream.json 单独下载。随包保留上游许可证文本于 third-party/HYPIT-LICENSE。

海艺 OpenAPI 地址默认为 https://art.huya.info 。账号、Token、模型访问与费用由海艺服务管理，原海艺插件不包含在源码包中。没有重新分发或授予这些服务与插件的权利。

本包不宣称是 Hypit 或海艺官方联合插件；它是本地统一生产入口。上游工具与服务适用各自原有条款。

可选提示词资源：unknowlei/minimax-h3-opencode-skills（commit 2e2096fe39ef9b5ddd5998cdcf422c6534065115，MIT）及 MiniMax-AI/MiniMax-H3 的 h3-prompt-writing（commit d21241f0a4b3acbb34c97dae47fa417b7065e438）。本包结合说明引用其公开方法与官方格式入口，没有包含这七个外部技能或 MiniMax 模型；需从原仓库另行安装，适用各自原有条款。本集成中的通用 Seedance 指导不宣称 H3 语法可跨模型直接使用。
