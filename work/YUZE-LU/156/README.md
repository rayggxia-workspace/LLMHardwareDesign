# Issue156：双 S 外存供数与有限 DMA

任务：[Issue #156](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/156)，负责人 YUZE-LU。
审查：[PR #159](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/159)，base为`task/155-s-sram`。
分支 `task/156-external-memory`，接口冻结提交 `33d87f6868d98befe0aa01bf9c5725fe7ef47a40`。
PR同步了依赖分支的`4e062cd8`；其增量只有物理脚本／证据／属性，已核对所有回归消费源码SHA未变。
本任务不改 #155 源文件、不切换生产选择、不操作其他任务作业。

正式说明：[七宏数据搬运合同](../../../docs/EXTERNAL_MEMORY_V1.md)。
新硬件：[finite_dma.sv](../../../project/rtl/external_memory/finite_dma.sv)。
复现：[run.py](../../../project/experiments/external_memory/run.py)。

## 最终验证（2026-11-01，Asia/Shanghai）

最终接口回归是本地 WSL Ubuntu22.04 的 `run-11`，不是前面的诊断运行。
工具 Verilator5.042，实际字符串 `Verilator 5.042 2025-11-02 rev UNKNOWN.REV`。
标准单元 S 与 SRAM 接口各三次，参数 `(randReset,seed)` 为 `(1,156)/(2,156)/(2,157)`。
参数在 DUT 构造前解析，JSON 中读回核对；复位期间不采样未定义存储占用。

六次均成功退出；总计 **20,206,567 检查／4,250,814 拍**。每次覆盖四种外存配置及九组
路径／搬运测试；每种配置另有25个随机二维／整份 S 用例。输入、握手、计算响应背压
分别使用独立种子，四配置复用同样输入。DMA／外存队列峰值均4项，T峰值256字＝4KiB。

| 1拍响应、每拍最多接收1请求 | 标准单元S 总拍数 | SRAM接口S 总拍数 | 外存读B | 外存写B |
| --- | ---: | ---: | ---: | ---: |
| M 8×29×7 S8＋独立补料 | 476 | 553 | 1,280 | 512 |
| N Softmax257 | 2,171 | 2,435 | 1,584 | 1,056 |
| N Softmax8193 | 64,717 | 72,917 | 49,200 | 32,800 |
| R GDN256行 | 10,990 | 13,038 | 8,192 | 8,224 |
| R SSM256行 | 12,289 | 14,337 | 8,192 | 8,224 |

矩阵读流量包含 A512B、B256B、并发补料512B；S普通口等待实测标准版7拍／SRAM版4拍。
8193元素向量使用256字窗口，完整输入1025字，每字16B：三轮读、两轮写，包含尾字填充。
R表只统计状态和读出结果；参数仍是软件直接下发，不能宣称为完整层的外存流量。

31拍响应并随机拒绝一半请求时，N8193增至149,420／155,337拍，R GDN256增至30,460／32,098拍。
这些总拍数包含软件逐命令控制，不能当作 DMA 饱和吞吐或完整硬件 sequencer 性能。
保留现有 M/R 端口和 S/T 容量；当前证据没有要求加入 M/R 外存直达口。

原始回执：[rtl-final/result.json](rtl-final/result.json)；
[全部配置对照](comparison.json)；六份逐初态 JSON、实际命令、夹具、严格 DMA lint、
联合 lint／编译日志同在 `rtl-final/`。冻结 R/T 原有警告保留，新 DMA 严格 lint 无警告。
所有消费源码逐文件 SHA 在回执内，已在保存证据时重新与工作树核对。

## 综合映射

最终任务 **94564，yzl-i156-dma，COMPLETED 0:0，6秒**，只申请4CPU，实际 affinity34–37。
远端目录：`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-156/map-02`。
ORFS镜像SHA `49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a`；
Yosys0.68+post，Nangate45 typical Liberty SHA
`8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1`。

核对上传清单、三种初态真实通过回执及 DMA 源 SHA 后综合；`check -assert`通过，所有单元
映射到库，无残留内部 `$` 单元。**8,425 cells，其中814 DFF；综合单元面积12,745.922µm²**。
此面积不含布线／时钟树／填充；没有新的 DMA P&R、STA、门级功能或形式等价通过结论。

原始 [receipt](map-02/receipt.json)、[完整 map.log](map-02/map.log)、[Slurm终态](map-02/sacct.txt)、
脚本、输入 SHA、工具、内存准入和 Slurm 日志均保存于 `map-02/`。map输出SHA已按原回执重新核对。
`mapped.v/json`保留远端并在回执索引；最终回执直接绑定 `rtl-final/result.json` 的原字节SHA。

Slurm报告节点配置内存仅1MB，显式8GiB申请实际被拒绝，未获得作业号；最终入口据实际
`MemAvailable`要求至少4GiB，不声称获得内存保留。最终Yosys实际峰值83.61MB。
第一次映射94561用于早期诊断，保留 `map-01/`；最终以94564和修正初态后的回执为准。

## 诊断与修正

- 旧 Verilator4.038 拒绝原 N 数组循环非阻塞赋值；改用已有5.042的私有本地副本，未改 N。
- 非ASCII目录使生成 makefile 路径不可用；按原字节复制所需输入到私有ASCII临时目录。
- 初始矩阵夹具把 B 当行优先；按 M 真实列优先合同修正，原失败保留。
- 初态验证器原先在解析参数前静态构造 DUT，不能作为多初态证明；随后修正构造／析构顺序，
  并排除复位期间的占用采样。run09虽输出 passed，但进程析构失败，明确拒收；run10复位监测失败。
  **只有最终run11六次成功进程及读回的初态参数作为最终验收。**
- Windows生成上传SHA清单含CRLF，首次检查拒绝；改为精确LF字节重新检查后才提交。

关键原始诊断文件在 `failures/`。它们是历史失败，不能与最终通过回执混用。

## 接下来需要审查的边界

本次“最小搬运硬件”是已实现、已RTL验证且已综合的独立 DMA；S/T已有接口足以接入。
命令桥、普通口系统仲裁、参数装载和全局调度仍有软件／夹具职责，不把它们算成已有硬件。
DMA 有物理面积，不能靠 M11/M12 连线生成；最终放平台侧、固定控制区或受控 S/T 版本，
需要后续明确的物理验收。本次没有扩展成新芯片／全模型调度任务。

#155 的真实 SRAM宏生成／DRC／LVS／表征／完整S P&R独立验收，本次只使用其冻结接口及
显式仿真模型。后续接口变化时重跑这里的统一回归；不复制这些接口结果冒充真实宏物理证据。

规则 `rayggxia-project-collab1.0.0`；登记沿用management-hub PR#5的pending记录；
看板缺 `config/board.json`，未核验 Projects，事实unverified、同步pending。
审查人与管理员待指定，未自行合并或标done；[持久交接](../../../docs/handoffs/2026-11-01-issue-156-external-memory.md)。


## #162 复用审查更新

系统采用#162 D替代finite_dma；后者保留为已综合参考及独立M/N/R回归，不并列部署两套DMA。新增docs/EXTERNAL_MEMORY_CONTROL_INTEGRATION.md明确单位转换、所有权、信用、背压、错误排空、协调复位、T经S暂存后写外存再release，以及有状态逻辑的物理归属。软件描述符转换3组测试通过，不冒充RTL协议桥。run12双S各三初态全部通过：20,206,567检查/4,250,814拍，源与run11完全一致、映射源未变。证据work/YUZE-LU/156/rtl-control-review/index.json。SRAM仍为接口模型，#155完整S物理验收待完成；双S为两种替代实现，#162目前只支持实例0。R仅隔离回归，禁止据此在#162发射。D替代后的系统组合仍需#162自身验收，不借本轮通过授予资格。


## 2026-11-02T09:23:36.198753+08:00：D替代真实S接口验收

control-compat-03六次成功退出，标准单元S各19336 checks/4335拍，SRAM接口S各20368 checks/5236拍，合计119112检查/28713拍。实际消费#162 D/planner/read/write与原S/SRAM接口RTL，外存40bit AXI、1/15/16/17/255/256/257/1024字节、二维/4KiB/尾WSTRB/并发读写/非零实例拒绝/读写错误排空/完成背压均通过；新增已接受AXI在途下协调复位并重新LOAD/STORE实际S读回通过。完整原字节源快照、fixture、测试、构建日志和SHA在work/YUZE-LU/156/control-compat-final。没有修改其他工作树/任务。

本次闭合的是本任务RTL兼容交付，不是#162全部系统验收或#155真实SRAM物理资格。finite_dma仍保留run12的真实M/N/R路径与同源综合；#162系统使用D替代。R仅隔离回归，不开启系统发射。T释放及软件/夹具责任继续按集成合同执行。全部本轮检查通过，提交独立审查，不自行合并。
