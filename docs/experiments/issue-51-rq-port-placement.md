# E2a：减少宽传输是否值得固定近端重新量化

2026-10-23（Asia/Shanghai），Liangruizhi，[Issue51](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/51)，
[PR52](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/52)待审查合并，未done。
用户授权由仅本机扩展为服务器CPU并行；本次没有GPU或新模型下载。
运行源码`134838c71282f1a823cc99b3d857ebe3331b8d3b`，初版557cf21d保留为资源声明修正前记录。

## 实际执行

已有Qwen3-0.6B layer0 q_proj/down_proj，K1024/3072、N16；prefill16行与decode1行，W8A8、
完整K内部INT32累加、无bias、RQ8后送整数行和消费者。校准为原文前8行，不是独立模型质量评价。
8数值fixture×2RQ库存×2活动窗口×3消费者服务×2调度×2位置=384组织，192匹配位置对。
本机执行独立Fraction RQ及typed packet回放；服务器以8进程重放全部服务图，无科学框架依赖。

| 作业 | 用途 | 节点/CPU | 调度状态 | 实际运行 |
| --- | --- | --- | --- | --- |
| 89936 | 初版受控搜索重放 | node27，8CPU/8worker | COMPLETED，0:0 | Slurm 5秒；程序约3.460秒 |
| 89937 | 分开PE寄存器与SRAM后的正式重放 | node27，8CPU/8worker | COMPLETED，0:0 | Slurm 5秒；程序约3.457秒 |

程序秒数只说明软件搜索耗时，**不表示LLM推理或目标芯片速度**。两个作业均自然完成，未取消其他作业。
正式目录`/public/home/yuzelu/RuizhiLiang/issue51-rq-ports-20261023/run02`；
本地D:/Projects/Codex/rq-ports-20261023/local02及server-return02。source/input bundle SHA256
`61ddf3b811aad874b55c23c5a62ab91979eabe82e8782cd6371890110eb723ec`；
远端回传包221,411B，SHA256 `93c86dcebc5608f098c7edeec85b016f243b27885f7fb7c5eac2757e032af27d`，下载后核对一致。

## 固定资源与边界

每位置配对的计算、存储、物理端口和FIFO相同。RQ1/8 lane为两份不同库存，不混算位置收益。
64B header、64B payload对齐、128bit链路、1984B最大分片；单共享半双工bus，整包store-and-forward。
S8×32KiB各1RW；M：A两4KiB、W两8KiB、单口MC6KiB和并行PE累加寄存器2KiB，共32KiB；V16KiB单口。
RQ输入staging256B、V消费者scratch512B另计；M/V各两RX一TX、S各一RX一TX，每FIFO2KiB。
不能把PE内部每周期并行累加误当作MC单口SRAM提供的带宽；初版声明已修正并复跑，未改变数值或周期结果。

输入W/A按K128预打包、常驻S，初始外存/打包和浮点量化/scale生成在边界外；q_proj的16KiB权重可加载后复用，
down_proj的48KiB权重分块。四次重复tile是服务压力，不能称四段新模型输入。静态M/r一次加载，动态参数按tile传入。
RQ32标量延迟26、间隔28来自Issue33 RTL；8lane复制、矩阵服务128+M+N-2、消费者服务均未RTL/PPA校准。
消费者成本1/8/64、FIFO与critical-height调度是冻结敏感性，不能当真实芯片三种工作频率或全局最优策略。

## 结果与解释

按相同窗口/调度逐点匹配，192对中近端92更快、100更慢；最好周期降低0.5716%，最差增加34.97%。
最差点包含强制单窗口的生命周期串行化，**不能据此宣称近端硬件必然慢35%**。

为避免用不利运行策略贬低一方，另对同库存/数值/消费者下两边各自选择已有两窗口和两调度中的最好值。
这是冻结扫描后的描述性策略包络，不新增试验或事后接受阈值，也没有证明全局最优：

- 48对优化策略中，近端46更快、2略慢；最大周期降低0.5657%，最差增加0.0650%。
- prefill每tile INT32 payload1024B→INT8 256B；含header边界packet为1088B→320B，减少768B，
  四tile合计3072B。完整输入/metadata/消费者流量仍在，不能将边界节省70.6%称总吞吐提升。
- decode N16时，64B INT32与16B INT8都占一个128B packet，边界物理传输节省为0；
  private bank读写和持有时间仍可不同，因此总周期不必完全相同。
- 该局部模型的微小最佳差异受未校准矩阵/消费者、调度和私有RAM实现影响；目前不足以固定一个不可绕过的近端RQ边界。

当前建议保留完整K的INT32内部反馈、typed ACC32旁路与ACT8/16输出的候选能力；RQ放置继续条件化。
不因为字节较少就宣布近端获胜，也不根据强制单窗口的最差点否定它。M/A三遍attention、INT33 bias及R反馈
仍是后续不同实验，本次只完成E2a，尚未通过整个E2或端到端/物理资格。

## 验证、失败与复现

8项边界测试、1088个独立Fraction RQ值、完整K的INT64对照、两种位置实际packet代码/消费者一致。
384组织共981,312个服务节点、80,832个packet审计依赖、资源排他、bank容量、2KiB TX/RX credit和上下文lease；
6个完整trace见结果包。服务器384例cycles/busy/traffic/audit与本机逐项相等，这是同实现跨主机重放，不是第二套RTL。

开发阶段保留：padding负例原来修改了整倍数payload的有效数据，改为68B实际padding；
一次prepare在本地生产尚未结束时提前调用缺manifest，等待完成后重新导出，没有错误提交或覆盖。
资源声明审查分离2KiB PE寄存器，将MC8KiB改为6KiB以保持M总32KiB；严格容量重放通过，周期/数值不变。

源码与命令见[README](../../project/experiments/rq_ports/README.md)，[交接](../handoffs/2026-10-23-issue-51-rq-ports.md)。
先核小包SHA并解压新D盘目录，再运行verify.py，服务器参考无需权重或Torch；重跑完整本机run仍需继承的Issue33小捕获包。
每个输入、输出、源码和作业回执保留版本/SHA，登记/看板/审查状态以Issue/PR最终回执为准。

[归档索引](../../project/experiments/rq_ports/results/issue-51-run01/index.json)含432成员，evidence.zip=1,097,901B，
SHA256 `7972a74e37ede7df12818ef03cdd23b82b79013a2d6f0002537094326b4f98c3`。安全解压后独立整数/trace及服务器384项再验通过。

```powershell
python -B work/Liangruizhi/47/verify_delivery.py project/experiments/rq_ports/results/issue-51-run01/index.json --extract D:/Projects/Codex/rq-ports-20261023/review-new
python -B project/experiments/rq_ports/verify.py D:/Projects/Codex/rq-ports-20261023/review-new/local02 --server D:/Projects/Codex/rq-ports-20261023/review-new/server02/server-results --output D:/Projects/Codex/rq-ports-20261023/review-new-audit.json
```

## CPU模型实验的可行性实测补充

node27实际为Intel Xeon Platinum8488C，总RAM约503.53GiB；CPU flags含avx512_bf16、amx_bf16、amx_int8和avx512_fp16。
本次只分配8CPU，这不表示已获得整节点内存独占或96核配额。flags不是已验证AMX内核可用或吞吐证据。
计算节点Python3.6.8没有NumPy/Torch/Transformers，因此完整模型迁移尚需现代运行环境、权重及正确性pilot。
师兄仍需GPU吞吐/显存/真实GPU量化内核；已有GPU结果复用，CPU采集迁移不得重复未协调的任务。
