# Issue247 新周期速度迭代证据

## 第三轮RTL与旧体系评估通过，候选未超第二轮（2026-11-10，Asia/Shanghai）

Issue247/PR243，Melodydt，in_progress。run20/101872（源a3149d69a23f52efb808dbbb46b5558dffce4df7）41秒；run21/101878（源010ae8d0d8839967f96b94227d2224fade0edf37）6:06，均c64/node1/4核COMPLETED0:0。RTL六run×66场景、有限控制299064周期比对及实际S数值通过；模型24case/8精确回归/8fallback、192篡改及原测试通过。R3双buffer主ideal3.66041657326/shared2.75864978939，低于第二轮；当前最快仍3.66958239533/3.37834376557，未到5。

第三轮5页PDF、134内容单元及全部页面视觉QA通过，当前完整交付3/4轮。报告固定809f9820cc13157077e4399a789779aac52925db，PDF SHA00b0b6c2d6c44829808d316cb3e6658c378d8bf51e5cb7632320e790e969940d。大面积候选独立备份task/247-m-k16-area-initial@a3149d69a23f52efb808dbbb46b5558dffce4df7与前态备份均读回；S仍16KiB。run20结果SHA87842b59e42fb0773eedb82dce4981614432868fa12218c3aa15166b0b839eff，run21结果SHAbccd917afba10bb9c3f65f62b26b1eab588a85d73c364a4b4d54962b5197afb8。

服务器本人/public/home/yuzelu/Melodydt/issue247-area-speed/run20、run21持久保存source/、slurm-job.log与results/；62大raw另有retention SHA索引，不声称Git内含所有raw。追踪sacct -j 101872,101878 -X --format=JobID,State,ExitCode,Elapsed,NodeList。全部终态，无自动监测。第四轮在隔离目录实施R2基础op12四EXP lane；1KiB A缓存受DDR上限约束，仅保留方案。恢复第一步核对最新PR head/本轮报告，继续第四轮源审查、Slurm实测和旧体系复评。非Git本地快照work/Melodydt/242/r-load-bounds/repo仅根整合，R4子任务各隔离目录；远端task/242-r-load-bounds未合并main。

登记pending、Projects unverified/同步pending（缺board.json及工具能力）、审查人/管理员待指定；GitHub CI此前失败原因未核实，未绕过。当前候选不具备完整P/DMA、原生整图生成或新物理资格。

## 第二轮RTL与评估通过（2026-11-10，Asia/Shanghai）

Issue247 / PR243，负责人Melodydt，in_progress。R2源码863492081f0f512fc64fb73c787fcdcaf145a6b4，31文件blob读回通过。run18/101852/mdt-r2-nexp-rtl，2:37；run19/101854/mdt-iter2-nexp，2:53；均c64/node1/4核COMPLETED0:0。R2实际费用[7,7,9,9,16,16,18,18]，默认/DIRECT0兼容、数值、持久状态及完整U通过。16旧体系case/8默认精确回归、2prefill fallback、128篡改及profile/CLI负例通过；独立复核完成。

主W8 decode512 ideal3.66958239533（比R1+0.90184%）、shared3.37834376557（+0.83026%）；Dot224.101536667ms占82.2359%，未达5。run18结果SHAfb0b4d0d1251140655feea5bd671c196e5ae13b1fd47066dc22d6e1e1a2eac78，run19结果SHAb16ff9a0209add1227177d1899bbf9928ae7e83d724a0c113469e7c860c97098。两run在/public/home/yuzelu/Melodydt/issue247-area-speed/，源码、日志和结果持久保存；追踪`sacct -j 101852,101854 -X --format=JobID,State,ExitCode,Elapsed,NodeList`，查看各目录results/result.json。所有作业终态，无自动监测。

第二轮4页PDF及110内容单元、全部页面视觉QA完成，当前2/4轮完整交付。PDF源文档固定e531a9944ff1ae4bc55e3b6e204be48f425af1a3，PDF SHA1c28b2f2ee7a736b92d4e84308e6a067a6ec761976e78d547310248ac9850a66。第三轮在隔离目录研究/实施S32/S96 M有限供数；正式生产未改R3。恢复第一步核对PR最新head，审查R3真实buffer/nextK/commit/ACK与旧模型收费边界，并在新增大面积候选前创建独立备份。SRAM不扩容；大面积候选另备份。登记pending、看板unverified/同步pending、审查人待指定，未合并main。

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
