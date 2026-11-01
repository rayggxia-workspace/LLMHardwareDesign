# C/D 与块旁适配器模型（Issue162）

任务 [#162](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162)。按用户要求，先在已有 SystemC PR146 提交本模型，再从六宏 main 建独立 RTL/P&R PR。

## 当前实现和证据边界

`include/control/{abi,sequencer,dma,modules}.hpp` 是新增代码，不改变原七宏数值模型。

- C：256×64 程序、16×32 标量、8×40 地址、四层循环、16×256 描述符、32 事件、16 排他租约；一条指令/模型步，WAIT 不阻塞完成入口。完成和输出分别由有界 SystemC FIFO 承担背压。
- D：两项描述符队列、两项在途突发、16 beat 上限、32 word 保留信用、40bit 地址/128bit 数据的地址规划；切分 4KiB 边界、计算尾部写掩码、按 S 的整128bit写入检查 padding。出错停止新突发，等待其余在途确认。
- 命令收包：32bit×8 flit，收满保留，消费前不能覆盖；对应后续块旁适配器的控制入口。
- 真实 `control::C`、`control::DModule` 为 `SC_THREAD` 时钟进程，使用非阻塞 FIFO 调用，完成入口持续排空。

**尚未实现**：D 的 AXI 五通道和数据 FIFO 载荷；D 的读写并发两组信用；完整端点两项任务/两项完成队列；M/N/E/G/S/T 的新硬件适配器状态机；host AXI-Lite；八模型程序生成与实数据三组合。当前 D 保守地只在队首描述符发突发，总计两项在途，不能据此声称实现“两读＋两写同时在途”。这些是后续 RTL PR 的必做项目，不能由本测试替代。

原 `blocks/` 七宏模型仍是冻结旧合同的**无时钟事务模型**。新增 C/D 是时钟推进的**控制合同模型**；它们不是 RTL 拍数、带宽、面积或布局布线的证据，不自动使原七宏模型跟随 main 新实现。后续 RTL 拍数由实测另行记录。

## 接口编码

指令64bit：`op[63:56],rd[55:52],ra[51:48],rb[47:44],flags[43:40],aux[39:32],imm[31:0]`。操作码按 `Op` 枚举从0递增：NOP、MOVI、ADD、SUB、AND、OR、SHIFT、SET_ADDR、ADD_ADDR、LOOP、END_LOOP、BRANCH、DESC_WRITE、SUBMIT、WAIT、WAIT_ALL、LOAD_META、FENCE、END。

标量加减按32bit环绕；地址加法按40bit检查且立即数为有符号32bit。SET_ADDR 的 aux 为高8bit。LOOP 使用 ra 对应的非零计数，四层以外报错，END_LOOP 重复循环体。BRANCH flags=0 无条件，否则 ra 非零跳转，imm 是绝对 PC。DESC_WRITE 将 ra 寄存器写入 rd 描述符的 aux 字。代码装载仅在停止且无在途任务时允许。

SUBMIT 从 ra 描述符创建任务，将事件 tag 返回 rd；flags bit0 可启用 aux低4位对应的排他租约。没有共享读租约优化，编译器须 WAIT 后再申请相同租约，否则会停住；不能生成互相等待的资源依赖环。WAIT 消费 ra 的 tag，将完成 result 写 rd。WAIT_ALL/FENCE/END 排空在途任务后消费完成槽。END 表示程序结束。R endpoint=7 未启用。LOAD_META 当前保留并报 Illegal，不能假装直接读主机内存；后续应通过真实 DMA 元数据读命令＋WAIT 回填标量实现，并补充模型和验证。

任务256bit：W0 `tag[31:16]|flags[15:12]|endpoint[11:8]|opcode[7:0]`，其余 W1..W7 是类型相关载荷。完成64bit：`result[63:32]|flags[31:24]|status[23:20]|endpoint[19:16]|tag[15:0]`。tag=`generation[10:0]<<5 | slot[4:0]`；槽只在消费完成后释放，重复或错源完成拒绝。generation回绕要求链路无跨2048轮滞留包；系统复位必须同时排空/复位所有端点和链路。

故障停止新指令，已发出的任务仍须接收完成。`reset_idle()` 只能在无输出包且无 Pending 时调用，清故障、完成槽、租约和标量/地址，保留程序/描述符与 generation，不能用复位偷掉 DMA 在途响应。事件错误状态需要显式恢复，不提供自动回滚外存承诺。

DMA typed descriptor（`DmaDescriptor`）现提供`pack/unpack`，与PR163的RTL线编码一致：W0 tag16/flags4=0/endpoint4=0/op8（0load/1store）；W1 external低32；W2低8 external高8、[11:8]S实例、[25:12]S字节偏移；W3低24行字节数；W4低16行数/高16 S步距；W5外存步距；W6/W7及其余保留位必须为0。首版仅S实例0，其他值在发AXI之前拒绝，不能别名到同一S。外存及S基地址/步距按16byte对齐；行尾在 S 中占完整16byte，外存写用 last_strobe，外存读尾需在真实数据通道清零 padding。S范围检验包含全部行尾padding。调用方须提供合法外存padding分配。

WAIT拒绝高16bit非零的伪tag；PC=255的非BRANCH/END指令在执行前报Bounds，与RTL的8bit PC溢出检查一致。此处仍是合同模型，RTL实际AXI载荷、N长窗口三遍回放及三组合证据在PR163，不追认本模型已具有完整AXI通道仿真。

## 验证

在真实 Accellera SystemC3.0.1、GCC10.3、CMake3.27、C++17 下，以 `-Wall -Wextra -Werror` 和 UBSan 编译：

```bash
cmake -S project/systemc -B .systemc-build-162 \
  -DCMAKE_PREFIX_PATH="$PWD/.systemc-deps/install" \
  -DCMAKE_BUILD_TYPE=Debug -DBLOCK_SANITIZE=ON
cmake --build .systemc-build-162 -j4
ctest --test-dir .systemc-build-162 --output-on-failure
```

新增 `control_contract` 759 检查（原723项加36项DMA线编码/保留位/未接S实例检查）：满事件槽、未消费完成槽不复用、稳定背压包、重复完成、WAIT收完成、40bit越界、第五层循环拒绝、程序/描述符边界、未合格R拒绝、DMA九种行长（1..4096）、4KiB切分、两项在途/两描述符限制、S容量与padding、错误排空、真实SystemC时钟模块通信。原524425数值断言、系数来源和Softmax例程仍通过，合计4/4 CTest。不是 AXI 协议或最终RTL验证。
