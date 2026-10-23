# Issue29 sim.cpp / generate.py 独立只读审计

2026-10-22；主工作树 `D:/Projects/LLMHardwareDesign-portrtl`，基础提交 `a3f8335287f6745bd96b9657a6279f12a142ac49`，被审代码当时为未提交的新文件。已读项目 AGENTS、协作 Skill 和真实 Issue29（负责人 Liangruizhi）。本次没有修改主树、GitHub、服务器或他人文件；没有执行 RTL 仿真，结论限于源码与已生成程序的独立检查。

审计期间主线程并行修订。以下为实际读取时测得的 SHA-256；首版发现保留为修复历史，不代表末版仍存在：

- sim.cpp：`ebd54c8cccaad736b6a56432b61ceb42ff7cd35078bb5c50d04547ca51dc0b65`
- generate.py 修订版：`bdd5315f069220294c6f3546497077b2eb073abfc1c5066c180d41abbbdc3b16`（初次发现的旧文本没有独立冻结SHA，不把该修订版SHA倒填为旧文本来源）
- 已生成 index：`43eff9e07ebdde28edf24adc096aa25df30b056dca60944b0a63f8ecb7279e04`

## 影响正式实验解释的事项

### 已修复 P2：公共 index.config 的 bank_ports 与多数案例不一致

`generate.py:69–87` 在循环中修改同一个 config；末尾 `result.config=config` 保存的是最后一次 `2RW`，但 cases 覆盖 mode0/1/2。case.mode 能恢复真实意图，但任何按顶层 config 作图/解释的下游会把1RW/1R1W结果误标为2RW。独立审计实际观察 public_config_bank_ports=2RW、actual_case_modes=[0,1,2]。

建议从公共 config 删除 bank_ports 并明确 per-case 派生，或保存每case配置；正式 runner 同时绑定 case.mode/depth/mask 与编译参数及 trace.config。

`.case` 仅包含 n、stalls、priority 和任务行，**没有模式/深度/连接掩码头**。程序跨 mode/depth 完全相同是正常且公平的，但不能单凭 caseSHA证明用了目标硬件。缺失的绑定应由正式 runner/结果 manifest 验证；目前仅审这两个文件，不能预称已有。

### 已修复 P2：程序输入检查允许非法bank在检查前访问 C++数组

`sim.cpp:128–134` 不检查 bank∈{0,1}、kind/write∈{0,1} 或 read version范围。`sim.cpp:156` 在进入 `Sim.tick` 之前用 bank 下标访问 memory，因此不能靠 grant 时的地址断言避免未定义行为。

具体反例保存为 `invalid-bank.case`：1个读task，ep0、bank2、offset0、bytes64、latency1、version−1、无依赖。它满足现有 task 入口断言，却在发起读时越界。未执行这一未定义行为负例；由代码路径确认。建议完整解析后先验证全表，再开始仿真；同时初始化 n/stalls 并在提取失败后先报错。正式生成的1872个case均没有这些非法字段。

### 已修复 P2：stress初始化没有watchdog

`sim.cpp:188–191` 初始化2048个bank行的 while 循环不受后面 `195` 行的stress watchdog保护。将DUT变为永不grant，或在初始化期间停止ack，会永久停在此循环。后面的随机阶段超时检测无法覆盖。

建议给初始化也加有限cycle上限，并让runner设置独立进程超时。这个缺口影响故障注入的可结束性，不表示当前正常RTL一定挂起。

## 关键时序与公平性检查

以下代码逻辑与当前生成程序中未发现失守；实际RTL运行仍需逐周期trace独立核验。

- **D源write**：151行条件与168行记录的 last_dma_write 按实际grant计时；新beat最早为上次grant+2。held请求stall不改变payload，不会因早期issue而绕过限制。契约是64B beat每两cycle，不能外推连续32B物理总线实现。
- **D读sink**：162–164行在原backpressure之外强制奇数cycle不consume读响应。tick结束已eval上升沿，下一次读取的rsp_valid/rsp_write是当前队首；该判断不依赖即将生成的新请求。
- **half duplex**：101行在实际write grant检查是否存在读响应valid，即使该响应同cycle将pop或stall，也拒绝碰撞。
- **任务完成**：169–170行仅在全部beat响应收到后done；active endpoint到此才释放。139行仅根据done释放依赖，所以后继不能在最后grant后、最后ack前提前启动。
- **read graph version**：156行在提出请求时检查，108–109行在实际grant再次检查；排队期间错误覆盖不应仅因issue时已检查而漏掉。
- **写入/读取事件顺序**：先检查/弹出旧响应，再为本cycle grant保存预期，随后上升沿更新DUT。same-row任何双grant被拒绝，因此不同endpoint循环顺序不会造成同址读写软件顺序偏差。
- **compute资源**：harness本身不锁compute engine，只依赖DAG；当前全部生成程序的同engine compute已被依赖闭包严格串行。以后接受任意DAG时应增加资源检查，不能把当前成立推广为通用调度器。
- **计数语义**：read_beats/write_beats是接受的64B传输beat数，traffic是逻辑有效字节；decode中4B状态仍消耗完整beat，两者不可混为有效payload吞吐。

独立脚本 `audit_programs.py` 不导入生产generator/graph，不执行RTL，直接解析1872个dev01案例并核对SHA、字段、因果闭包、地址范围、静态边、逻辑字节与优先级/程序等价：

| 检查 | 实际数量 |
| --- | ---: |
| case SHA /完整程序 | 1872 |
| task rows | 126360 |
| RAW闭包 | 52416 |
| WAR闭包 | 32760 |
| WAW闭包 | 32760 |
| 同engine compute串行对 | 59904 |
| 同phase/placement/policy/stalls的程序等价组 | 128 |
| 删除未用静态边的case | 720 |

结果：PASS_FOR_GENERATED_PROGRAMS，详细计数在 `program-audit-results.json`。这一检查不能替代实际RTL响应检查或算术正确性。

## 科学边界及后续负例建议

1. mask59移除V0，只允许p111；mask31移除D1，只允许O0。对于可行case，这些边都没有流量，匹配程序逐字节相同；应是零cycle效应对照。若出现周期变化，优先检查误配binary、mask影响或测量方法，不可把删未用边写成动态重路由加速。
2. `run_stress` 的一个全局RNG在held槽空闲时生成请求，grant不同会改变后续随机数分配与地址序列。所以同seed跨硬件不保证同一 offered traffic；可用于各自安全性压力测试，不应用其stress_requests比较硬件吞吐胜负。
3. `token`只返回8bit，严格满足 token(g+256,j)=token(g,j)。审计脚本已实际验证整beat碰撞。当前任务数小于100，不触发该具体重复，但不能声称token是无界精确generation证明。若以后扩展tile/task数量，应保存独立每byte generation owner或使用不会在支持范围重复的更宽签名并明确界限。
4. 当前scope明确为真实bankcontroller+synthetic M/V延迟。host生成写payload不依赖算术输入，只能验证存储/协议和预定DAG，不能证明FP32 attention结果，也不能将cycle外推整模型吞吐/PPA。
5. 建议对首次正式trace额外断言：每个case最后响应均已drain；每个request tag恰好完成一次；每个依赖task.end≤successor.start；D write grant间隔≥2；D read consume只在偶数cycle；所有endpoint读rspvalid时无writegrant。定向负例应包含过早done、删除WAR、read-held期间覆盖、错误mask binary、初始化永不grant。

## 计算节点启动补充

PR17固定b9c94ff的 job.sh 第3行：`export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"`，之后调用singularity。其记录明确旧probe01在计算节点PATH缺失时127失败，补此路径后probe02成功。因此可复用计算节点路径线索是 `/public/software/singularity-ce-4.3.4/bin/singularity`，不能只凭登录节点 `/usr/bin/singularity` 可用推断计算节点同路径存在。本审计没有连接服务器。

## 修订版复核与当前状态

- 当前 sim.cpp SHA-256：`d3cc0648e99df62a2d2e8dcf083263d297c32fd60faac65dd1cfdabf6b228f37`；generate.py：`bdd5315f069220294c6f3546497077b2eb073abfc1c5066c180d41abbbdc3b16`。只读副本位于 `harness-snapshot/`。该目录是修订版，不是最初被发现问题时的完整旧源码。
- 主线程已加入 case header 的 mode/depth/mask 并与实际编译宏一致性断言；公共config去掉bank_ports；bank/kind/write/read version检查；严格前向依赖；初始化10000cycle watchdog；外部数据共享间隔断言。
- 我在独立目录重新运行修订版generator得到1872可行/1584拒绝，再用独立parser复核全部1872个case，以上全部因果/字节/串行计数不变；新增逐case header核对通过。128个匹配组的**逻辑任务和优先级**相同，header按硬件参数正确不同，不能再称整个case逐字节相同。
- 修订版index SHA-256：`5323b4d7e372799fc221c964f3ea95474a6eb6c5b1ca43870e8424aaa439c015`；详细结果 `program-audit-results-v2.json`。初版dev01与修订版各自保存记录，不混作同一次输入。
- 剩余入口健壮性建议：128行头部及131行的局部整数在提取前未初始化，且只在整表末尾检查输入流。空/截断文件可能先使用未初始化变量；建议每次 `>>` 后立即 `need(bool(input),...)`，并初始化局部整数。这不影响本次全部合法生成程序的静态检查，但负例应以确定错误返回，不能依赖未定义行为。
- 未发现当前正式生成scope中可使科学对照失效的D源/目的限速、任务提前完成、版本依赖或同engine compute并发漏洞。实际编译/仿真和独立trace验收由主线程及对应审计agent进行，本报告没有冒充已执行。
