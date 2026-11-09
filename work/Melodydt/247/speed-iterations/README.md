# Issue247 新周期速度迭代证据

负责人Melodydt；[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247) / [PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)，in_progress。最多四轮或主W8 decode512旧体系理想端口层达5 token/s；共享口并列，不授予原生四1RW或完整模型资格。SRAM不扩容，重大面积候选另备份。

## 第1轮：正式U NExp批处理

[实施与结果报告](../../../../docs/experiments/issue-247-speed-round1.md)、[机器摘要](round01-summary.json)。源码e6d72113a14c5a0772f01ff5851d630d5d6687fa；run16/101835 RTL 40秒、run17/101838旧模型2:52，均c64/node1/4核/COMPLETED0:0。主ideal3.49616888299→3.63678454238（+4.0220%）；shared3.23081074122→3.35052563236（+3.7054%）。prefill S16保留旧路径。

`index.json`为133份不可变原件和两个run的入口。原件超过24KB时用gzip+base64存储，index同时保留原SHA、存储SHA和编码。源码以每run单独tar快照保留，输入随payload精确归档；没有用后续当前源覆盖旧资格。全部大对象/二进制及完整output-files.sha256保留本人服务器run16/17。

## 本地核验和复跑

```bash
python -B work/Melodydt/247/speed-iterations/verify.py
# 只有当前源仍等于指定run时才额外加此项；后续修改源不得改旧SHA。
python -B work/Melodydt/247/speed-iterations/verify.py --current-run run16
```

上述只读检查实际通过133原件、89源成员、11输入、96选定输出SHA。run16所有273输出、run17所有87输出另有索引；未下载的原件明确留服务器。实验执行入口在project/experiments/rtl_iterations/round1和project/experiments/iterative_speed/round01。每次新建Slurm运行目录，不覆盖旧结果，先提交/读回代码，再打包绑定source_commit和SHA。

查看：登录yuzelu@10.129.166.172，根目录/public/home/yuzelu/Melodydt/issue247-area-speed；`sacct -j 101835,101838 --format=JobID,State,ExitCode,Elapsed,NodeList`；各run内 `cat results/result.json` 与 `tail -n 60 slurm-<job>.log`。两作业已终态，无自动监测。

本轮[5页PDF](../../../../docs/experiments/pdf/issue-247-speed-round1.pdf)已由正式报告完整生成，125内容单元及5页视觉QA通过；后续轮次继续按实际瓶颈和回执推进。登记PR5 pending、Projects unverified/同步pending、独立审查人待指定，未标done。
