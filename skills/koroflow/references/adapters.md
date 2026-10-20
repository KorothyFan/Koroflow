# 制作与发布平台接入

平台只负责具体执行，同一作品的编号、版本、质量要求、首交付日期和统计口径不随平台变化。查询 `adapters` 看本机声明，`route --operation video.generate --requires reference_video native_audio --adapter haiyi-hypit` 核对能力；不会自动选平台或提交。

## 当前适配

| 适配器 | 实际能力 | 执行入口 |
|---|---|---|
| haiyi-hypit | 已实现的Seedance参考生成、GPT Image图片生成 | 原workflow.mjs的check/plan/pricing/build；需原setup与授权 |
| haiyi-skill | 海艺原技能的编辑、音频等外部路径 | 实时查询模型、上传和提交；不是统一Provider已实现的额外路由 |
| hypit-local | 已有本地时间线、音轨和渲染 | Hypit实际Source/Run/Runtime |
| manual-publication | 人工完成即时或预约发布 | 明确账号、选版、实际结果证据 |

`implemented`表示仓库有对应外部执行实现，不表示核心CLI会调用，也不证明本机登录、模型价格或运行时可用。`external`表示交接现有外部技能/工具；`manual`表示人工；`unconfigured`不参与可用路由。transport区分api/mcp/browser/cli/manual。所有能力声明都要对照实际接口核实。

## 添加平台

复制本技能的 [适配器模板](../assets/templates/adapter.example.json)，填写独立id、transport、status，以及operations内的capabilities与handoff，加入本地`.koroflow/adapters.json`。文件不含密钥、服务器地址或账号；这些由用户实际工具的授权配置管理。没有验证连接时保持unconfigured。MCP名称和工具名应记录在本地handoff，不在公共示例假设某服务存在。

制作操作包括video.generate、video.edit、image.generate、audio.generate、video.compose；发布包括publication.publish和publication.schedule。核心按照请求明确要求的capabilities核对，不自动降低要求或换服务。视频时长、画幅、模型、原生声音、首尾帧、素材大小、额度与取消能力仍由执行器提交前核实，通用声明不替代实时模型参数。

无限画布可以承担素材组织、节点编排或生成；仅登记其实际支持的操作。画布节点成功不等同视频成功，必须取回真实输出及任务依据。

## 执行交接契约

1. prepare写入work_id、task_key、适配器、操作、输入请求路径与SHA256；不把请求正文或凭据复制进事件。发布同时固定已交付revision与文件SHA256、完整稳定account_id，并保存本地占用。
2. 执行器提交前重核请求和文件指纹、账号/平台身份、历史记录与授权。只执行一次。将远程ID及时record-task为submitted；数字ID会归一为字符串。
3. 轮询/下载由对应工具负责；record-task记录running、succeeded、failed或result_unknown。成功生成/处理要有真实本地output文件，费用只有明确amount和unit时记录，不猜币种或退款。
4. 响应丢失且没有远程ID时可由prepared直接记result_unknown，原本地占用继续保留；先查平台，不新建任务碰运气。已预约或已发布要有实际列表/作品证据，scheduled不自动变published。取消仅记录已核实结果，不假称核心取消了远程任务。
5. 失败、跳过、取消才释放该任务的发布占用；新task_key仍需既有授权。独立账号各有分配，同账号同作品或同指纹的非释放任务阻止新分配。

核心只串行管理自己的日志，无法让外部平台提交与本地写入形成跨系统事务。执行器必须保存实际回执，网络不确定性作为独立状态处理。当前没有内置通用HTTP/MCP调用器、自动登录器或自动发布机器人；现有实际工具照常使用。
