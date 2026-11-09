# Issue247 / 阶段2：两槽弹性馈入候选（尚未执行）

本目录仅为父代理准备阶段2。父代理须先完成阶段1，再把冻结源码提交到自己的Slurm新目录运行；本代理没有运行仿真、SSH、在线操作或改生产文件。不要把以下期望写成已取得结果。

## 设计合同

`pj_feed_elastic.sv`保持原WIDTH/valid/ready/data接口，增加`empty`。输出是payload寄存器；第二槽是尾部寄存器；输入ready只由寄存器count和reset决定，不经过下游ready组合反馈。正常count=1时同时pop+push，可持续1beat/cycle；count=2时先消耗一拍再开放输入，故没有隐含第三信用。复位期间ready/valid均为0、empty为1，时钟复位清count；无效payload无需复位，禁止复位时捕获输入。

两WIDTH为135/517；相对原单槽，payload寄存器增加652bit/P，另有两组2bit计数及控制。不是扩SRAM。真实面积须综合，不能把位数当mm²。时钟、路由、关键路径及物理资格均未验证。

原`pu_p_group`把源ready当empty。两槽中ready表示not-full，必须改为`feeder_done && a_empty && b_empty`，保持LOAD完成晚于所有操作数被M接收。`render_group.py`对三个上游源做SHA守卫，生成独立baseline/candidate目录，只换两个hold并修改empty完成门控；M、SRAM、数值、外部接口和ACK语义不改。变体保持模块名，必须分别编译，不可同一binary同时读两份pu_p_group。

## 独立link对照

`bench_compare.sv`各实例有自己的合法源与reference queue：因ready不同不能逐周期比较两个输出。覆盖真实135/517位、持续吞吐、满/空与满后复苏、随机valid/ready、payload背压稳定、源协议、活跃状态复位、复位取消和队列守恒。下游ready在两时钟边沿之间翻转，以检查输入ready不随其组合变化。

一次256拍预热后测量，**期望**旧单槽128 beats、新两槽256 beats；这只是link吞吐，不是整P或token/s翻倍。`load_completion_case`让A/B各保留一beat时两源ready都为1而empty都为0，必须挡住LOAD完成；再分别释放A、B，二者都退休才允许完成。

```bash
# 在阶段2已分配Slurm节点执行；NEW_OBJ/NEW_LOG均使用新目录。
verilator --binary --timing --assert --timescale 1ns/1ps --top-module bench_compare --Mdir NEW_OBJ -j 4 \
  FROZEN_REPO/project/rtl/pu_leaf_base/pj_feed_hold.sv \
  pj_feed_elastic.sv bench_compare.sv
NEW_OBJ/Vbench_compare > positive.log 2>&1
set +e
NEW_OBJ/Vbench_compare +NEGATIVE_READY_EMPTY > negative.log 2>&1
negative_exit=$?
set -e
python3 -B check_logs.py --positive positive.log --negative negative.log --negative-exit "$negative_exit"
```

负例必须非0退出，且同时含`EXPECTED_NEGATIVE_READY_AS_EMPTY_DETECTED`及`LOAD_COMPLETION_BEFORE_OUTPUT_RETIREMENT`；不能接受任意崩溃当负例通过。正向须四个case及LOAD门控完成回执齐全。父运行器另外记录正向真实退出码、工具版本、源码/日志SHA及分配资源。脚本命令未执行。

## 端到端P组

```bash
python3 -B render_group.py --repo FROZEN_REPO --out NEW_STAGE
```

可分别用`NEW_STAGE/baseline/pu_p_group.sv`与`NEW_STAGE/candidate/pu_p_group.sv`运行未改的`NEW_STAGE/tb_pu_p_group.sv`。公共依赖沿原`pu_leaf_base/smoke.sh`的P分支选择：`pu_p_store_control`、`pj_mem_port`、`pj_sram_client`、`local_s_p`、`block_feed_s16k_sram`、`block_feed_loader`、`block_v2_m`、`block_v2_g`及原真实256×128 SRAM bank模型。baseline用原`pj_feed_hold`，candidate用`pj_feed_elastic`，禁止同时加入两份P组。

另生成`tb_pu_p_group_timed.sv`，仅给原bench增加总周期计数器和`final`输出`P_GROUP_CYCLES`，原检查逐字保留；分别编译此计时版可比较同一完整P组程序的周期数。必须同时取得原PASS及正常退出，不能把失败时final打印的周期当有效性能结果。

原bench覆盖两个K段、真实S写回、非法命令、gated SiLU、直连等价及复位；两个版本均应保留原PASS。原bank输入来自授权环境，身份和版本须由父代理冻结；本目录没有复制或读取外部物理包。端到端周期改进须额外实测，不能从独立link的2倍直接推断。

没有删除/弱化原检查，没有改其他成员目录；SRAM扩容、M宽化、U流水化均不在本阶段实现范围。

## 父运行器接续

`run_elastic.py`和`job_elastic.sh`预期合入正式`project/experiments/area_speed_study/elastic/`，默认repo根为`HERE.parents[3]`，也接受显式`--repo`。job在本人的新run目录、source-files.sha256校验后运行，4核、c64/c96、UNLIMITED，固定Verilator5.042。只有`--stage1-result`真实文件的`passed`为true才允许阶段2；父代理必须先核验阶段1作业实际COMPLETED0:0，再复制其完整结果到runroot/stage1-result.json，runner记录该文件SHA。不得制造通过标记。

公共P源从冻结`pu_leaf_base/smoke.sh`的common和slot2解析，不执行该脚本。父package须包含12个公共/原variant源、原P bench、smoke.sh以及**project/rtl/block_v2/block_v2_g_tables.svh**；候选七文件也须包含。真实bank固定源及SHA在runner中，任何漂移立即失败。

独立link按三种原rand配置`1:143/2:143/2:144`分别验证四实例，定向负例一次；该build不使用`-Wno-fatal`。baseline/candidate P组各三种rand，同原smoke对既有公共RTL保留`-Wno-fatal`，不更改或删除上游检查；新elastic已在独立bench严格编译。`results/result.json`保存命令、退出码、日志SHA、工具版本、输入/源码身份、每例总周期及真实比较。失败同样写passed=false后非0退出，不以JSON存在代替通过。

若容器PATH存在Yosys并有原Nangate45 Liberty，额外综合同一135/517配对link，映射并输出cell types、Liberty area单位与比例；不进行P&R/STA，不声称mm²。缺工具/库记not_executed，未知commit填待核实。父runroot/inputs.json应提供真实source_commit。job不依赖聊天/SSH存活；未启动、未配置监测。
