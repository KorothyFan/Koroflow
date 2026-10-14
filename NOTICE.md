# 来源与范围

本代码库为用户的 Hypit + 海艺集成工作流：统一 Skill、自定义海艺 Provider、配置模板与辅助脚本。

Hypit 上游：https://github.com/hypit-ai/hypit 。选定 commit：85e01c76716498e6ec5b8bdfb6b374ca67f0195a。© 2026 Hypit.AI。模板采用 Hypit 的公开作者接口，Provider 采用 Hypit 的公开扩展接口；完整 Hypit 核心不包含在此源码包中，setup --install 按 upstream.json 单独下载。随包保留上游许可证文本于 third-party/HYPIT-LICENSE。

海艺 OpenAPI 地址默认为 https://art.huya.info 。账号、Token、模型访问与费用由海艺服务管理，原海艺插件不包含在源码包中。没有重新分发或授予这些服务与插件的权利。

本包不宣称是 Hypit 或海艺官方联合插件；它是本地统一生产入口。上游工具与服务适用各自原有条款。
