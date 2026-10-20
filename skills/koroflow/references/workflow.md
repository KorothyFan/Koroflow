# 核心记录与执行

需要Python 3.11+和IANA时区数据。仓库入口为`python -X utf8 scripts/koroflow.py`；安装技能入口是本技能`scripts/workflow.py`。以下的CLI代指其中一个，`--workspace`必须放在子命令前。

## 初始化与新作

```text
CLI --workspace <现有视频工作空间> init
CLI --workspace <目录> create --manifest <作品.json>
CLI --workspace <目录> bridge --work <work_id>
CLI --workspace <目录> status --work <work_id>
```

init只创建`.koroflow/config.json`、quality/adapters/targets.json；已有配置拒绝覆盖，不创建虚构作品或恢复旧工程。项目文件夹先按用户既有规范准备。manifest见本技能的 [作品模板](../assets/templates/work.example.json)，project相对manifest文件定位；references中的asset按项目定位、responsibility明确素材职责。实际上传仍由执行器负责，不扫描整个资产库。作品编号是任意非空稳定字符串，不作为路径拼接。

create记录制作中；bridge可立即导出in_progress，结束/暂停后再bridge和运行用户已有统计刷新。新核心journal的每条事件是独立UUID文件，保存在`.koroflow/events`，sequence在独占锁内分配，不按UUID或文件时间决定先后。文件内容fsync后原子替换。日志序号缺失或重复会报错；异常遗留write.lock先检查owner和真实任务，不自动抢锁。

## 生成与质量

```text
CLI --workspace <目录> route --operation video.generate --adapter haiyi-hypit --requires reference_image native_audio
CLI --workspace <目录> prepare --work <ID> --task <本次独立请求键> --adapter haiyi-hypit --operation video.generate --request <真实请求.json> --requires reference_image native_audio
CLI --workspace <目录> record-task --work <ID> --task <键> --status submitted --remote-id <远程ID> --evidence <真实提交依据>
CLI --workspace <目录> record-task --work <ID> --task <键> --status succeeded --output <真实输出.mp4> --evidence <成功回执>
CLI --workspace <目录> register --work <ID> --revision v1 --file <选定文件.mp4> --provenance <真实生成或处理来源>
CLI --workspace <目录> review --work <ID> --revision v1 --report <检查记录.json>
CLI --workspace <目录> deliver --work <ID> --revision v1 --title-en <英文标题> --hashtags "#cute" "#funny" --evidence <实际交付依据>
CLI --workspace <目录> bridge --work <ID>
```

示例省略执行器实际提交/轮询步骤，不能直接虚填remote-id和成功。record-task在submitted之后才允许成功；prepared可转result_unknown处理丢回执。重生成另用任务键，仍属同work_id；同适配器的同远程ID不能登记成另一个任务。video.generate/video.edit成功分别计真实生成，image/audio/compose和register不计新视频生成。

review格式见本技能的 [检查模板](../assets/templates/review.example.json)。默认检查剧情/身份比例、画面连续性、声音与同步、纯净画面及实际编码；按本地项目可改quality.required_checks，具体标准来自Brief、角色偏好和规范。检查器保存人工/工具判断，不会自动识别画面或听声音。缺项、fail、not_checked均不能交付；当前没有自动豁免。无音频等不适用项在evidence明确说明并由实际检查者判断。模板默认未检查，不提供一键假通过。

修订用新revision_id，文件SHA256和检查记录绑定；同revision内容不可覆盖。交付保持同work_id并选择明确revision。重复相同交付会复用事件；发布文案改变也应按用户实际修订另建revision记录，不用重复交付键改历史。

## 发布、采用与每日统计

先用koro-operations的plan核对完整现有账号/品类/历史，再prepare发布任务，固定选版与account_id。新核心只对它登记过的分配去重，因此不能跳过旧任务历史检查。

```text
CLI --workspace <目录> prepare --work <ID> --task <发布键> --adapter manual-publication --operation publication.publish --request <文案请求.json> --account <稳定账号ID>
CLI --workspace <目录> record-task --work <ID> --task <发布键> --status submitted --remote-id <提交ID> --evidence <依据>
CLI --workspace <目录> record-task --work <ID> --task <发布键> --status published --evidence <真实作品页证据>
CLI --workspace <目录> state --work <ID> --action adopted --evidence <用户明确采用或符合约定的发布证据>
CLI --workspace <目录> report --date YYYY-MM-DD
```

发布状态不会自动触发采用；手工台账标记也不改事件。state支持paused/cancelled/resumed/adopted，后续bridge只导出真实发生的状态。targets分别配置weekday、weekend及date_overrides，角色数量和临时排期不写死在代码。report的三项数字分开：成功视频任务、首交付日的独立作品、回计首交付日的明确采用。当前制作中状态不是过去日期的历史快照。没有配置目标时remaining为null，不报虚构达标。

## 已有项目与统计兼容

旧项目继续由koro-operations和现有统计器管理，无需批量迁移。可从`check --hash`保存的完整JSON报告中显式导入一个可用交付：

```text
CLI --workspace <目录> import-legacy --inventory <旧检查报告.json> --work <原work_id> --project <原工程目录>
```

导入保留原work_id、选版、首交付日期及明确采用状态；未知日期继续未知，缺失文件/候选错误拒绝导入，不找旧文件兜底。导入不生成新交付/成功任务，也不补造质量验收；下一次新修订必须通过当前quality。历史只剩保留成片且无工程者，继续使用原台账，不恢复目录。

bridge只追加核心里实际发生的制作/交付/采用UUID事件，更新该作品发布信息，保留其他字段并去掉旧版迁移选版字段；不伪造生成任务，不写Excel手填字段，也不自动运行刷新/平台。重复执行不会复制事件。若部分写入后进程中断，可以重跑；已有相同事件ID但不同内容会报错，不能覆盖历史。新的核心report不能与原全量snapshot相加，它们可能覆盖相同作品。
