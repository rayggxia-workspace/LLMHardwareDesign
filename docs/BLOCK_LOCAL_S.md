# 每个 Block 独立仲裁的私有 S

设计入口为[文档 PR #176](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/176)；实现任务为 [Issue #177](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/177)。本轮由 huangpingyang04-lgtm 在独立分支实施，基线 main `4b1df2c7cbdaa0fa6f9f468f2b5b854cec875609`。

## 改变后的行为

每个物理 Block 拥有一个 `block_local_s_macro`，里面有自己的存储、仲裁状态和返回归属。客户端编号只在本块有效，接口不提供远端 S 地址选择或全局客户 ID。外部数据通过本块 RX 客户端写入；TX 通过本块客户端读取。局部控制器负责请求时序、地址生存期和 feeder 命令，不与母控共同驱动 RAM 端口。

| Block | CLIENTS | 本地客户槽，按编号升序 | feeder |
| --- | ---: | --- | --- |
| P | 4 | M 结果/访问 helper、G helper、RX、TX | 本块局控专用 M feeder |
| U | 4 | N helper、E helper、RX、TX | 无 |
| C | 5 | R helper、G helper、E helper、RX、TX | 无 |
| F | 4 | G helper、E helper、RX、TX | 无 |
| J | 4 | E helper、T helper、RX、TX | 无 |

这些槽是块内适配器边界，不是原生计算宏直接接受的新协议。实验的客户端由独立协议 peer 驱动，未实例化完整 M/N/E/G/R/T、母控或网络。

## 请求、真实确认与公平性

`req_valid/req_ready` 只表示请求已进入该 Block 的有限命令寄存器。仲裁器同时保存写位、10bit 字地址、128bit 数据及 owner；此后源可改变输入，不影响在途请求。每块普通口最多一笔在途，状态为 `IDLE → SEND → RETURN → IDLE`。

`SEND` 等待真实 S 接受请求；`RETURN` 仅向 owner 发布 S 的真实响应。写返回携带实际写入的数据，客户端必须等该响应才发布 stored ACK。返回背压期间 S 持有数据，owner 保持，其他客户不会拿到这笔响应。

普通客户按轮转选择；所有客户持续请求且响应可消费时，每轮每人一次。某客户一直不接收自己的返回，会阻塞同一 S 的后续普通事务，这是首版单在途合同；不会锁住其他 Block 的 S。客户端取消需通过本块同步 reset，不能撤销已经完成的 RAM 写入。

`busy`反映普通事务在途或feeder正在运行；feeder完成包仍可能保持。局控必须同时检查`done_valid/load_ready`及返回消费，不能仅凭`busy=0`重装程序或认定所有完成事件已退休。

P 中真实旧 feeder 与普通事务共享原四个 1RW bank。新增一位本地优先状态，在双方可服务时交替授予宽读和普通事务；没有增加存储端口。宽读响应停顿而不能接受新请求时，普通口仍可前进。持续无法接收 A/B 的客户端不获得无限缓冲。

## 有限状态及物理归属

- `block_local_s_arbiter`：请求寄存器139bit、owner、轮转指针、三态状态机；均属于本块。
- `block_local_s_macro`：上述仲裁器、1bit普通/宽读选择状态、真实 `block_feed_s16k`；P 另含真实 `block_feed_loader`。
- 存储 payload、普通/宽响应寄存器和 feeder 有限队列保持原源码语义。没有新增全局张量缓存或隐藏第二份工作 RAM。
- 同步 reset 屏蔽握手、放弃尚未完成的命令和排队响应、清本块仲裁/feeder；不清 RAM。已写数据保留，局控必须用自身对象/epoch 状态决定是否有效。

两份基线源码 `project/rtl/block_feed_v1/block_feed_s16k.sv`、`block_feed_loader.sv` 未修改；原 `block_feed_s_macro` 及其原资格也保持。新增局部包装的组合资格不能从旧叶宏推导。

## 本轮容量边界

本轮专门验证局部仲裁，因此每个 S 都保留真实16KiB、四个256×128bit bank、普通128bit和宽读512bit接口。测试池为 `P0/P1/P2,U0/U1,C0,F0,J0/J1` 九个独立实例，共144KiB payload、36个真实存储 bank。它不是文档 PR #176 中 P.S32KiB/工作S192KiB 的完整模型资源配置。

32KiB地址链、紧凑S16打包、对象/epoch管理、完整局控及三个LLM执行另有实施边界。本轮不把客户端协议测试写成模型质量或完整控制系统通过，也不修改 #162 等现有控制分支。

## 运行与结果

正式代码在 `project/rtl/block_local_s/`；集成fixture、独立C++记分板、服务器runner和Slurm脚本在 `project/experiments/block_local_s/`。实际作业与结果见[任务记录](../work/huangpingyang04-lgtm/177/README.md)。

在允许的新任务目录内按Git原始字节准备8份输入及 `source_binding.json`，然后在Slurm分配的资源内运行：

```bash
python3 -B project/experiments/block_local_s/run_server.py --out /absolute/new/output-directory
```

运行器会核输入SHA，执行真实集成lint、Yosys层级/存储清单、1/4/5客户仲裁器综合及九组RTL验证；完整命令由 `job.sh` 给出。旧输出目录不能复用；失败日志保留。debug分区按服务器规则最多30分钟，常规分区可用脚本默认无限时；本次实际分配以回执为准。

测试检查全部1024个字地址、跨块同地址隔离、持续争用公平、单块响应停顿时其余块前进、随机背压、真实A/B供数所有格式、B复用、独立复位与正常复用。原RTL阶段之后，P4/N4/N5三种16KiB局部S叶宏已分别完成实际布局布线、300MHz全端点时序/电气、完整DRC、实际最终网表功能及严格LEC，六文件/图按SHA实收，见[物理报告](experiments/issue-177-local-s-physical.md)。P.S32KiB、完整计算Block/模型、M11/M12和制造签核仍未实施。
