# 双 P 控制顶层候选

Issue #179 / PR #180，负责人 Melodydt。用户授权本分支尝试实现顶层后形成此候选。顶层使用当前 64 bit 母控、两个固定 ID 的局控和 PR214 的实际 `pu_p_group`。本模块属于控制集成，沿用已有 P 数据通路。

## 固定结构

`dual_p_control_top` 包含一个 MC、两个 `p_control_endpoint`、一个 `two_local_link`、一个 `p_word_link` 和一个 `p_stored_ack_guard`。每个 endpoint 包含当前 LC、原生计算/传输适配器以及一个实际 P 组。P0/P1 的 ID 分别为 0/1，各有 16 KiB 私有 S，128 bit 字、10 bit 字地址。块内选择 S 回放，M→G 直送端口保持关闭。

控制程序沿用已验证的 P16 控制 ABI `0x01790160`、拓扑 `0x01790161`、容量 `0x17630001`，三份镜像均为 v2/64 bit。这里使用该控制 ABI 的命令合同，实际数据通路由独立叶宏 P 组提供。P0 的六条执行记录和 P1 的两条执行记录分别驱动计算、预约和交接。

## 外部接口与运行

配置及 PM 信号均按三端打包：索引0为母控、1为P0局控、2为P1局控。各端独立的 release、cfg、PM 请求/响应保留现有控制器协议。128 bit PM 数据总线、14 bit 字节地址按索引拼接，地址须16 B对齐。正式程序存储器/配置总线桥接在顶层外，测试台使用 network_pm。

1. 公共复位异步置位、两级同步释放，`reset_ready_o` 后装载三份镜像。各端逐字写入、读回并准备。
2. `deployment_ready_o` 由三端 PREPARED/运行状态及 poison 决定。外部给出匹配的 deployment generation 后进入READY。
3. `host_req_*` 通过每颗P的外部存储客户0预装/读回数据。START优先于新host请求；存在未消费host响应时禁止START。作业活动期间不接收host数据访问。
4. 母控先调用P1预约/接收，再调用P0计算/发送。返回消息通过独立512 bit寄存槽，结果在主机背压期间保持。
5. 结果消费后可读回私有S、预装下一笔数据并启动新任务。故障保留未完成义务，恢复采用整个同域顶层的协调复位和新世代完整重装。

## 数据、身份与确认

前向固定 P0→P1，一次一字。`p_word_link` 保存128 bit数据、10 bit目的地址和128 bit身份；身份来自P0实际LC服务请求的job、epoch、task sequence、service sequence。只有目的端已预约匹配地址时才发出写请求。

目的S实际写响应握手产生 `store_commit`。链路随后保持反向身份回执，由保护器核对当前请求且已提交后发布完成。P0收到该完成才消费源S读响应。固定边的源/目的身份由连线确定。`link_pending_o` 覆盖数据槽与确认保护器的全部未完成义务。

这些数据、身份和ACK已经接入DUT。错误身份注入仅用于测试；测试核对源S响应保持、无源释放、故障隔离和复位后新任务。生产M11/M12的分帧、几何和寄生仍需按这一实际位宽落实。

## 复现

输入采用 `control_frontend_v1/upstream-lock.json` 固定的 native-p staging 和真实 SRAM bank 模型。`NATIVE_STAGE` 指向 stage.py 生成的 `native-p` 目录。

```bash
NATIVE_STAGE=STAGED/native-p SRAM_BANK=BANK VERILATOR=verilator BUILD_JOBS=8 \
  bash project/control_dual_p_top_v1/run.sh results/top
python3 -B project/control_dual_p_top_v1/check.py \
  --candidate STAGED/native-p/design/pu_p_group.sv \
  --verilator verilator --yosys yosys --jobs 8 --out results/check
```

功能场景为正常、PM背压、连续任务、在途复位和错误身份隔离/恢复。正常读回 P0.S[8]=`0xFFFFFFF600000006`、P0.S[14]=5000、P1.S[20]=5000；母控统计48 B确认写入，其中跨块传输16 B。每场景同时检查host访问互锁和结果背压保持。

独立字链路检查覆盖未预约/错地址、过早ACK、目的背压、ACK身份保持、复位及新身份。结构综合把P组边界作为黑盒；完整P数据通路在上述功能仿真中执行。结构综合不授予完整顶层物理或时序资格。

## 验收边界

这是可综合且可执行的RTL候选。[通过情况及SHA](../../work/Melodydt/179/native-control-and-top-validation.json)与[七项绑定](bindings.json)供接续使用。初版部署互锁依赖了部署后的image_valid信号，已改用PREPARED状态以消除组合循环；单元夹具的组合信号采样等待也已修正，失败档案保留。

A1可据此固定RTL实例、控制端口、私有S选择、块内路线、前向数据、反向身份ACK及三端镜像。正式PM后端、真实M10/M11/M12端点映射、时钟/复位物理实现、同版宏视图和完整组合验收仍待落实。独立P组含局控的旧物理包不能直接替代当前控制顶层的重新实现。候选尚未标记为生产合格。
