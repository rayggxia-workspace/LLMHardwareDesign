# E2a：同资源的重新量化位置

Issue51，独立worktree D:/Projects/LLMHardwareDesign-rqports，分支task/51-rq-placement。
用户已授权本机及服务器CPU并行；不执行GPU、大模型下载或接管他人任务。
先`python -B scripts/check_project.py`，再`python -B project/experiments/rq_ports/test_model.py`。

```powershell
python -B project/experiments/rq_ports/run.py --output D:/Projects/Codex/rq-ports-20261023/local01
python -B project/experiments/rq_ports/verify.py D:/Projects/Codex/rq-ports-20261023/local01 --output D:/Projects/Codex/rq-ports-20261023/verify01.json
python -B project/experiments/rq_ports/prepare_server.py --local D:/Projects/Codex/rq-ports-20261023/local01 --output D:/Projects/Codex/rq-ports-20261023/server-input01.zip
```

正式运行要求干净且绑定commit；输出不覆盖。server.py支持Python3.6+标准库，在已分配Slurm节点以8worker重放384组织；
仅申请8核，20分钟限制，lrz-rqports。模型整数参考留本机，不依赖服务器安装PyTorch或下载权重。
服务器bundle含代码/输入SHA，worker不得超分配；每个完成case独立保存。verify.py可加`--server <已校验解压目录>`
与本机逐case比较cycles/busy/traffic/audit；同实现跨主机一致并非独立RTL证明。

## 固定边界与成本

- 无bias的Linear→完整K INT32→RQ8→整数行和消费者；全K1024/3072，N16，M1或16。不是完整attention或norm。
- 已有Issue33 FP32捕获；校准是同原文的前8行，评价prefill64行16:32及decode64。无独立模型质量主张。
- W每输出dyadic静态scale；A静态/当前行动态，输出scale校准2倍余量；M=2^30、r显式，RNE/Sat8。
  浮点校准/输入转换和M/r生成在计时边界外，仅支持固定计算语义的placement比较。
- 8数值fixture×2RQ库存×2活动窗口×3消费者服务×2固定调度×2位置。1/8RQ lane属于不同库存，分别配对，
  不将多7个乘法器的收益写成位置收益。RQ延迟26/间隔28来自旧RQ32 RTL，bank回压会延长；8lane复制控制尚未RTL校准。
- 每个128bit口一次服务16B；packet一个64B header、payload向64B对齐，1984B最大分片，整包TX/RX各2KiB，store-and-forward。
  单共享半双工bus；S8×32KiB各1RW；M的两A4KiB、两W8KiB和MC8KiB，共32KiB；V16KiB且1RW。
  A/W bank计算读和写串行，MC的acc/参数/RQ输出竞争一口；RQ输入双staging256B、V消费者scratch512B另计且两方案相同。
  每活动S的TX/RX FIFO、M/V两个RX和一个TX均固定；所有bank/端口与私有存储在每个位置配对不变，未做宏/PPA。
- K128输入已打包且常驻S；数据预处理、外存及初始S加载在计时边界外。q_proj权重16KiB可一次载入M后复用，
  down_proj权重48KiB需分块；四次重复tile是服务负载，不是四段新模型输入。A每tile重读，M累加上下文持有到完整K。
- 矩阵每K128服务128+M+N-2为理想outer-product假设，消费者每8值成本1/8/64为未校准敏感性；
  FIFO/list与critical-height是固定启发式，无全局最优、硬件Fmax或端到端收益结论。
- 旧测试曾错误地把64B整倍数payload的末字节当padding；改为真实68B payload的padding负例，未更改接收器规则。
