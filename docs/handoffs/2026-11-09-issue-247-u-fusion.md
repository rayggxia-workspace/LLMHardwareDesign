# Issue247 U融合与流水重叠接续

## 运行更新

run07：源码1e6e10a7618f3d37542d1f22dd51af6ad1958eb8，101720/mdt-u-overlap，c64/node1/4核，21秒COMPLETED(0:0)，108项RTL测量及满/复位通过。结果results/result.json SHA e8aa9c641b299ed4c43b6dcea6583cfb77fad7220c1de783190fe2150f37d860。run08同源101721/mdt-u-fusion，91秒FAILED(1:0)：prefill四输入E被实验模型错误的三输入FIFO guard拒绝；decode旧结果已回归，不能算完整通过。所有现场位于上述ownroot对应run目录；回收归档SHA分别7148460ed8853ce24879c42c26ebd100f604a0e966fa01af8fb670bfe479af75、fb0bffd5ace7be52b3708242e2c8b5b577c3b0480d7fa8aa13425123436c2c46。

修正边界：实际串行模型仍执行全部输入、融合边与region事件；只有反事实FIFO回放在任一packet输入超过768B或输出超过256B时冻结整region串行，不扩大预算。下一次模型运行使用run09；本段更新时尚未提交，暂无活动作业。后续源码commit与作业号以新回执为准。

run06：源码31bbc96bc71b735967aebc4dbe2ff069aca2225b，作业101712/mdt-u-fusion，c64/node1/4核/UNLIMITED，2026-11-09 20:44:16开始，22秒后FAILED(1:0)。原生RTL对照通过；旧check_kernels.py写generated/kernels.json时目录缺失，未取得全模型性能结论。现场保留于/public/home/yuzelu/Melodydt/issue247-area-speed/run06，日志slurm-101712.log，局部结果results/native/result.json。源码修复仅新建generated目录及隔离旧回归环境；下一次模型作业使用run08，FIFO实验使用run07，启动后补真实作业号。

本次新增隔离的136位/项FIFO与调度实验，深度1/2/4；一个原N/E/S，生产RTL不变。A被E接管时FIFO槽释放，E活跃槽保持到写回ACK。source-overlap.json独立锁定；run06失败不抹除，旧功能源与原生结果仍可追溯。

2026-11-09 Asia/Shanghai；负责人Melodydt，规则rayggxia-project-collab1.0.0。[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247) / [PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。

用户授权详细研究连续算子融合与生产消费流水重叠，沿task/242-r-load-bounds继续。接续基线2f875d2f5cdd76c6eb17187bf6d836de1248b466；326个PR文件Git blob与本地逐项一致。非Git源码快照位于D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/242/r-load-bounds/repo；不称为本地checkout或pull。通过本人GitHub连接及ref租约上传，保留旧成果和无关变更。

正式源project/experiments/u_fusion_study；子任务独立目录为外层work/Melodydt/247/fusion-model、fusion-audit、fusion-contract，仅root整合正式文件。当前准备条件架构对照及原生N→E公平RTL bench，没有提交新仿真。生产RTL保持不变，SRAM扩容不实装。

验收先完整回归run05，再单独比较融合、有限缓冲重叠和联合模式，记录实际S访问/DDR/算术工作和有限寄存器预算。单E/N资源不得免费复制，已有canonical寄存器复用不得重复计收益。原生RTL位宽/流水合同与条件S32模型分开，重叠收益必须有可执行调度证据。

恢复第一步：核对最新Issue/PR和源码head、读取本目录最新运行回执；检查是否已有实际作业后再决定启动，避免重复提交。新工作在/public/home/yuzelu/Melodydt/issue247-area-speed的新run目录，Slurm名字mdt-*、分配核数内运行、UNLIMITED。当前无新增活动作业，未配置自动监测。

管理检查通过；后续模型/RTL/物理尚未执行。独立审查人待指定。登记management-hub PR5读回open/unmerged为pending；缺board.json/Projects条目能力，看板unverified/同步pending，管理员待指定。PR已有CI失败仍待核实，不改workflow绕过；Issue研究in_progress，不done。
