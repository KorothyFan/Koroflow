# 本地配置与调用

Python 3.11+运行检查器，Windows若缺少IANA时区数据需安装tzdata；本机可使用Codex捆绑Python并加`-X utf8`。管理模块不依赖Hypit、海艺凭据或Python第三方表格库。实际生成、Excel重建和平台操作分别需要相应工具。

在代码仓库中可使用简短入口：

```powershell
python -X utf8 scripts/operations.py init --config .local/operations.json --workspace "D:/my-videos"
python -X utf8 scripts/operations.py doctor --config .local/operations.json
python -X utf8 scripts/operations.py check --config .local/operations.json
```

init只创建路径配置且拒绝覆盖。默认路径适配现有中文工程布局，安装者应按真实目录修改；配置相对路径基于配置文件所在目录。统计快照的旧输出子目录也可替换，不能假定每台机器相同。

配置格式为`koro.operations@1`，包含`timezone`和`paths`：

| 路径字段 | 用途 |
|---|---|
| projects | 原始视频项目根目录；check检查其下的项目文件/发布信息.json |
| production_rules / creative_preferences | 本地制片规范与角色偏好，由AI按任务读取 |
| production_targets | 制作需求配置；独立于发布账号清单 |
| statistics_snapshot | 现有统计工具生成的data.json；snapshot不执行刷新 |
| publishing_accounts | 本地发布账号注册表，含accounts数组 |
| account_snapshot | 可选登录观察快照；usable_accounts、excluded_accounts及checked_at |
| publication_tasks | 本地发布历史JSON目录，重复检查依赖记录完整性 |

账号需提供稳定`account_id`，或云机`device_ip`+`container_id`，或`tiktok_username`。云机自动ID为`cloud:<device_ip>:<container_id>`；窗口简称不作为唯一身份。可配置`enabled`、`status`、`timezone`、`role`及`allowed_roles`。当前用户名不应替代已确定的稳定账号ID。窗口同名但设备不同时分别保留。

`accounts`输出用于定位和匹配，可能包含本地设备地址与账号信息，不应直接用于公开演示。账号观察快照不是实时授权证明。未登记的历史账号不会影响无关作品；若计划涉及同一作品/指纹而历史账号无法匹配，必须先核对历史身份。

仓库安装方式：

```text
node scripts/workflow.mjs install-skill --operations-only
```

它只安装管理技能，不要求Hypit、不安装生成依赖、不修改制作数据。完整install-skill同时安装管理技能。插件市场安装的技能亦可直接使用自包含检查器，配置路径通过参数指定。

现有统计刷新、成片打包和平台连接不随本模块复制；按用户配置定位。生成模块仍使用原setup流程。移动仓库后重新安装技能以更新本机路径索引。
