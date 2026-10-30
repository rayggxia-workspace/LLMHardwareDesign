# 原生 M10 仅经 via 接入的有限布线修复

2026-10-27。原120独立DRC有23项M9/M10间距，131实际只读扫描全部定位。尝试限制接入方式，保持既有A/C pin XY/大小、原CTS输入、10ns约束、driver/load、预算与M1–M10技术文件；不移动已冻结的产品底座。本版尚在预制修复阶段，没有冻结合格宏。

## 实际接入证据

132/92204在同一16CPU allocation内两路各8CPU并行读取113封存的实际保护CTS。baseline与`-via_access_layer metal10`均通过，源ODB/SDC前后SHA不变。两路分别203.216秒/208.265秒，整组3:35、TotalCPU53:58.362、MaxRSS1726008K，按已分配16核计算CPU利用率约94.1%。这证明该实际输入上的接入选项可用，不证明完整布线/DRC改善，也不证明C策略已独立通过相同接入测试。

证据：`work/YUZE-LU/121/results/run132-terminal/index.json`。安装版`detail_route.tcl` SHA256为`a21fd34d5104533a865f2e138c9fed546416ac6a37b1457baa8c0715537e0ba0`，与官方固定[64939f3源码](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/64939f3717ad7c694199ba04cb98924b98022868/flow/scripts/detail_route.tcl)精确LF字节一致。

该脚本设置`DETAILED_ROUTE_ARGS`时会替换默认`additional_args`，不能只填一个新flag。111实际`do-route.log`中的原命令是via-in-pin bottom/top均metal10、64次迭代、verbose1、每5轮报告。新候选精确保留这些参数，再增加via-access metal10。`native_reroute`绑定132两项实际通过、安装脚本SHA、111原成功回执/实际log SHA；make读回完整参数，route后再核实际命令完整后缀。禁止无意丢失原via包围约束或缩短迭代。

## 执行与资格

133拟采用同一32CPU allocation内A/C两路各16CPU完整route/final，保持计划已有的两种pin策略，不引入新的计算阵列或数值合同。实际可用内存至少64GiB时两路并行，否则串行；一个失败不取消另一条。A接入探针只证明A与公共工具选项可用，C必须在本次完整实际流程中证明自己。

原20/40 cap、5ps hold及原保护配置四种后缀与已发布cb89511逐字节比较保持一致；新的正例与丢via包围约束、缩短迭代、错接入层、实际命令缺flag、关闭LEC五反例控制通过。它们仅资格配置接收，完整物理效果尚未执行/接收。

新候选所有修复/保护/负载/面积必须全额计价；独立完整DRC/STA/PG/RC、实际最终网表功能、同源宏边界仍分别验收。原120失败和131定位不改写，不将DRT自身零违规代替完整原生deck，也不以这次有限尝试替代完整P0–P6。

## 实际启动

2026-10-27 11:45 CST：133/92206已在node22/32CPU运行，A/C两个完整T6K预制route/final子任务各16CPU并行，均实际make读回原native M1–M10、RCX、LEC及cap40/hold5ps、原输入保护和完整via-only参数；源码5bf5b4d0e74b2132cc7d8b1eb392f7fe8c2e1e61、归档05a956018f53186e2521e375d181adc7b58f5d9af9c7617a2ff12f2c9e2caf13，148成员/983040字节。尚无完整候选或独立接收终态。128 C8两路已过placement、正在CTS；当前本任务7个allocation，其他成员未动。134依赖128两路成功且尚无job。正式物理Block、一般多网分布RC/拼接、共同底座、两产品和参数库仍未验收。

首轮索引：`work/YUZE-LU/121/results/run133a-first/index.json`、`run133c-first/index.json`；父组索引保存真实job92206，子任务为同一allocation内进程，不能当作额外Slurm作业计数。132实测node22 MemTotal503.5GiB、MemAvailable495.0GiB，133启动仍重新读取内存并记录，不把历史可用量当作当前余量。

## 后续同节点完整资格

135准备同一64CPU allocation内四路各16CPU：A/C各自完整原生物理接收、A/C各自精确最终网表三初态功能。以旧T6K实际约20GiB峰值为参考、每路32GiB加20%余量选择4/2/1并发；不能把该参考当作135实测峰值。每路保留独立回执；一条失败其余继续。三个声明stub控制实际通过，包含四进程重叠、单一物理接收失败时三条同组任务完成、低内存降为两路；不证明真实CPU利用率或EDA资格。135尚未部署/运行，须依赖133完整结束成功。即便一条失败，也保留其他通过叶块供后续按其真实直接回执接续；组失败不能把其他叶块已通过的事实改写为失败，反之也不能用同组其他通过豁免本条。

## 部署回执

2026-10-27 11:49 CST：135四路完整T6K物理/最终功能资格已不可变部署，源码11505a8286b9abbeeedc25c42832d38765c480bc、归档b4b5392f1c8daf73c7062f6ed9df5e93c5e33476a0338b9177e399819079a30a，149成员/983040字节；依赖133 A/C组完整成功，尚无Slurm job。134也未提交，依赖128两路。133/92206仍实际运行；128两路placement完成，CTS接近本阶段报告输出，未有完整回执。当前7个本任务allocation；完整目标仍未完成。

`work/YUZE-LU/121/run135-deployment.json`与`stage131-manifest.json`绑定本次部署；不会因等待依赖自行重复sbatch。登记管理中心PR5本轮仍open/未合并，pending；缺board.json/Projects能力，看板unverified、同步pending；独立审查人与管理员待指定。
