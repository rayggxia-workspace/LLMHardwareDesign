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
