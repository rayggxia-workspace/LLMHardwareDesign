# 固定16KiB P：真实1RW bank并发候选

本目录仅为Issue247的隔离实现交付，生产集成由root负责。未扩容SRAM，不使用虚构1R1W宏，不改变M数值运算，也不提供64B读+64B写的合同。四个真实256×128 1RW bank合计仍为16KiB。工程默认 `ENABLE_BANK_RW=0`，保留原普通事务/feeder分相；开启参数才启用本候选。

## 接口与所有权

`block_feed_s16k_bank_rw.sv` 保留原 `block_feed_s16k_sram` 的窄128位/宽512位端口。每个bank每拍只有一个读或写。普通访问占用至多一个bank，wide gather首拍读取其余可用bank，无冲突时仍同拍读取全部四bank。若缺一个bank，下拍优先补齐；普通访问可以使用该补拍未占用的bank。每bank独立选地址，因此普通访问可针对另一行。

普通端口保留两槽有序响应，容量计入在途操作；wide只接受一个gather/持有响应，支持旧响应接管时接受后继。消费者背压不丢失响应，两个响应通道分别保留，不互相占用队列。wide累积寄存器只在真实读返回时更新对应128位切片；完整响应有效期间保持。普通端口每次写仍返回零载荷ACK（local配置），不能把请求接受当作写完成。

同bank冲突按有界选择处理：新wide与普通请求冲突时轮转；已开始且缺bank的gather优先补齐。无响应阻塞时，gather至多两次物理发射完成，固定响应等待另计。每个gather从首拍到最后数据capture保护整512位目标行，禁止该行ordinary写；读取同一行可以串行执行。没有在真实1RW宏上声称同址同时读写的未知语义。

`local_s_p_candidate.sv` 是交给root合并的local候选，名字避免与生产冲突。root负责将其内容接入正式 `local_s_p`，保留 `wide_req/ready/valid/take/wide_data` 等信号名供整体P测试追踪。参数为 `ENABLE_BANK_RW=0` 和 `ENABLE_REUSE_A=0`。后者只传给root负责修改的 `block_feed_loader`，开启后rows0是显式B-only，且reuseB必须为0。默认rows0仍非法。

local在接受LOAD前仍等待普通响应全部退休，新LOAD在空闲边界优先。LOAD活动后bank模式可恢复普通请求，但**整个LOAD输入范围均租用保护到done ACK**：A保护tiles×(rows>4?8:4)个128位word，B保护tiles×(b_wide?8:4)word；保护范围含512位布局的填充。rows0时A为空；reuseB时B为空。同范围ordinary WRITE保持ready=0直到LOAD完成确认，其余普通读写可继续。不能由policy把LOAD当前或后续输入槽当成可覆盖空间。

root拥有 `pu_p_store_control` / `pu_p_group` / `block_feed_loader` 的正式修改；policy agent拥有新的普通请求arbiter。两者仍须保留：LOAD边界先drain先前ordinary，活动LOAD可接收新ordinary；完成依赖feeder done与A/B真实hold empty；最终事务写ACK后才释放输出槽。此目录不重复实现上述上层策略，不改变ACK定义。

## 验证入口

将后端放正式 `project/rtl/s_sram/block_feed_s16k_bank_rw.sv`；local候选由root合并正式local文件；本目录bench/runner放 `project/experiments/p_native_opt/`。runner直接测试**正式** `local_s_p` 参数，不测试私有替代顶层。源依赖：两个SRAM后端、正式local_s_p、正式block_feed_loader和固定真实bank。

在root已获授权的Slurm/container环境执行：

```bash
python3 source/project/experiments/p_native_opt/run_memory.py \
  --repo source --out results/memory --workers 4 --manifest inputs.json
```

要求实际Slurm核数，最多4核；5个variant逐个构建：backend模式0/1，local参数(0,0)/(1,0)/(1,1)，各运行1:143、2:143、2:144三种rand配置。`--only backend`或`--only local`可作独立阶段，完整验收使用默认all。输入manifest必须包含真实source_commit和实际源SHA；结果持久保存命令、退出码、工具/宏/源/脚本/日志SHA及每case cycles。

真实bank固定为 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v`，SHA `6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7`。Verilator固定5.042路径，同既有实验。

backend bench以逐事务参考内存和两套响应scoreboard检查随机/有向顺序、整行快照、独立响应背压、reservation满、同时物理bank操作、同bank公平、复位无陈旧响应；计时比较相同64窄事务+32宽读，共192物理bank操作。local bench检查A/B数据与metadata、整LOAD A/B范围保护、默认rows0拒绝和显式B-only、done持有/ACK、持有数据复位；计时比较同一LOAD与64个不相交普通写，给出LOAD owned期间实际写接受数。

本地仅准备源码、AST和静态审查；**没有执行EDA lint/编译/仿真/综合/STA**。容量固定与结构可核对，性能结论必须等待真实服务器回执。bank模式可能因冲突补拍增加某些LOAD延迟；不能预设每种工作负载都加速。整体P与第1/3项的组合周期由root的同输入同结果native测试另行验收，不能拿后端局部数字替代token/s或物理资格。
