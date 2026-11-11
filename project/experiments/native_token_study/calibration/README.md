# Issue247：新版条件 token 模型的原生 RTL 周期校准

仅在本隔离目录编写校准工具；不修改生产 RTL，不在本机执行 EDA。由主任务集成、锁定源码并在授权 Slurm 作业执行。关联现有 Issue247 / PR243，不新建任务，不改变在线状态。

## 文件与调用

- `run_calibration.py`：server-only runner；两种后端配置，各三种随机初始化；保存实际命令、版本、源/宏/输出 SHA 和逐事件 JSON。
- `generate_bench.py`：只复用正式 `tb_popt_group.sv` 的端口实例，生成独立 `tb_token_timing.sv`。
- `timing_body.sv.inc`：实际 P 的操作/整数结果检查与观察器，保持实际四个 1RW SRAM 宏。
- `timing_contract.py`：独立控制路径递推和已完成 run10/run11 数值检查。它是源推导的预测，不是另一项 RTL 实测。

```sh
python3 -B project/experiments/native_token_study/calibration/run_calibration.py \
  --repo "$REPO" --out "$RUN/results/calibration" \
  --manifest "$RUN/manifest.json" --workers 4
```

实际集成目录可变，四个文件应保持在同一目录。manifest 使用已有 `source_commit` / `code_sha256` schema，必须覆盖 runner 所列的 14 个生产 RTL 文件，以及父任务锁定的新增工具。真实 bank 固定 SHA `6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7`。要求 `SLURM_JOB_ID` 与 `SLURM_CPUS_PER_TASK`，最多四核；runner 不负责远程提交。

## 校准条件与精确计时边界

所有计时均为没有其他 P 客户端竞争、没有 M/外部消费者背压的串行程序。记录接受边编号、首个完成信号有效的边编号，并另核对相邻接受间隔。接受边记 0；完成当拍只是可见，下一边才消费，不能把它与释放后的下一命令接受混淆。

1. 原生 M leaf 的 `q=tiles*digits(A)*digits(B)`，S8 为 1 digit，S16 为 3 digits。第 0 行首个 ISSUE 边 `s0=1`；后续 `s_r=max(s_(r-1)+q+1, f_(r-2)+5)`（无 r-2 时忽略），`f_r=max(s_r+q+2, f_(r-1)+4)`（首行忽略后一项）。最终 `L=f_last+8`。单行 `L=q+11`。这是双 S40 partial bank、四对 scale 流水与原子 S64 提交的结果，不能用 rows 倍单行或理想 MAC 数替代。
2. P 外层不写 S 的命令：首个 cmd_done 延迟 `L+2`，相邻命令最早接受间隔 `L+4`。op4 scale、op3 raw、op14 release 的 leaf `L=0`，所以各占 4 拍；op5 final 的 leaf `L=3`。
3. 通过 P m_writeback 真实写一次 128b S 并等待 ACK 的命令：cmd_done 延迟 `L+7`，连续命令间隔 `L+9`，故 op5 store 为 12 拍间隔。计时截止不是发出写请求。
4. 单个外部 ordinary128 端口：接受到 rsp_valid 4 拍，连续读写接受间隔 6 拍。实际走 pj_mem_port、arbiter、SRAM 响应和回程，不可直接按 16B/拍赋费。
5. LOAD 源推导（本轮新服务器测试必须核验）：group 接受到首次 load_done，A3rows / B8 为 `6T+7`，A3rows / B16 为 `6T+9`；B-only / B8 为 `2T+5`，B-only / B16 为 `4T+5`。`T=ceil(K/8)`，1..4。LOAD 自身再次受理至少另加 2 边。LOAD 与 M 是不同入口；新控制器若从已观察完成转入 M，可在下一边接受 M，但应对实际程序的 dispatch/间隙统一收费。

LOAD 上述推导保留 pj_feed_hold 的 **II=2**，真实 wide-S 请求与返回、B 优先的逐 tile 顺序、两条有限 A 队列和一条 B 槽。没有把它替换成一拍一个 A/B 的理想直连。银行与消费者策略在本串行程序里没有竞争，不应凭启用参数获得速度收益。

## 已有证据可用与不可用之处

- run10 原 M K32/N8/M8 的 `53/114/114/306` leaf latency（四种 S8/S16 组合）与上述递推精确相等。候选对旧命令输出逐字段一致。
- run10 的 1/2/8 contexts、每配置 44 cases 是直接 M A/B 接口，不经过 S、LOAD、P wrapper。它覆盖 K1/7/8/9/31/32/33/65/255/256/257、四种格式、scale、RNE、溢出和生命周期；**不能据它宣称 A3rows/B16 完整 P LOAD 周期已测**。
- run11 完整 P 只测 S8、N5、每段一个 tile、K11/K59。bench 显式保持 LOAD 完成，full LOAD 到下一 M 接受为 14 拍，B-only 为 12；M 命令间隔 16，16 次 final store 共 192，8 次 release 共 32。因此完全复现：`16*30+192=672`、`2*30+14*28+192+32=676`、`64*30+192=2112`、`8*30+56*28+192+32=2032`。
- 上述 14/12 含旧 bench 的人工保持；本新 bench 不人为保持 done。不能一边采用新程序最短 LOAD 边界，一边宣称逐拍复现旧完整程序。

## 新测试覆盖

实际 A 为三个 S16 行（1、2、3）与一个真实 padding 行；B 分别为 S8/S16 的 1。12 cases 为 B 两格式 × K1/7/8/9/31/32，N 为 1/5/8。先实际 LOAD + op10 rows3，读回每个 S64 结果；再八 contexts，每个执行 op4 shift0/15/30 与对应 sourceArow 的三次 op13，首组 full LOAD，其他组实际 B-only LOAD。8 个 context 都保持到 raw 数值校验、两个 final RNE store 的真实 ACK 后，再执行 release；随后从外部 S 读回全部输出。

每次 RTL run 产生 108 个 LOAD、288 个 op13、96 个 release，以及配置/raw/final 命令；外部连续四写四读核对数据和 6 拍间隔。两种配置（原后端/无优先、bank 后端/消费者优先）× 三种初始化，串行观察值必须完全相等。

## 未覆盖与模型资格

此测试**不实现或测量** S32→balanced15 的三个 limb 转换器、完整张量重排、外部 S96 合并/RNE、动态 S32×S32 的九项 scratch RMW、DMA/DDR、真实整模型数值或 300MHz 时序。相关新服务必须保留条件模型标签、明确真实 S 读写/命令成本、独立数值 oracle 和费用敏感性；不能由本校准获得硬件实现或物理资格。

完整 A 生命周期仍由程序确保：每条新 LOAD/M 命令的 operand bank 检查不等于跨命令 A 引用计数。实际 bank 后端合计最多四个 128b 1RW 操作/拍，不是两条独立 64B 读写口。

## 本地验证状态

已完成四文件静态阅读、三个 Python 文件 AST、本地纯算术已测点核对与 bench 文本生成；没有执行本地 EDA，没有执行服务器仿真。新校准成功与否以父任务即将运行的实际日志为准，当前所有新 LOAD/rows3 表为源推导待测。

本机默认 `git.exe` 因 Windows DLL 重定位报错无法查询；本子任务不写正式 repo、不上传、不改变分支或在线状态，源锁与最终 commit 由父任务核验。
