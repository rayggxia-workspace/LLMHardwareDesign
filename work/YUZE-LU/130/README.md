# Issue130：M/S 供数修改与实际验证

任务：https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/130 。负责人：YUZE-LU。2026-10-29，Asia/Shanghai。

正式合同见 [BLOCK_FEED_V1.md](../../../docs/BLOCK_FEED_V1.md)；测试源为 `project/experiments/block_feed_v1/`，硬件为 `project/rtl/block_feed_v1/`。当前为RTL／映射阶段交付，**不是最终布局布线结果**。草稿 [PR132](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/132) 待审查。

## 已实际运行的证据

| 模型 | 采用的原始运行 | 每初态检查／周期 | 说明 |
| --- | --- | --- | --- |
| 新M | run07/m | 191485／160639 | 128数值案例，四profile、8行、4块、尾块、完整K、S128失败保留、RNE、背压、双bank |
| 新S | run10/s | 844896／29378 | 全容量独立scoreboard、24000次随机调度、读写冲突、保持、复位；256次宽读256拍 |
| 真实S→M→T | run10/pair | 128972／63250 | 32随机案例；649次A/B同拍、360个结果字交T；有限队列、重用B、双bank和复位 |
| 随父支同步的V | run12/v | 566999／414906 | 接口未改；父支V group同步后重新执行三初态 |
| 旧R | run11/r | 379979／178456 | 原RTL不变；240递推＋100卷积；真实三初态测试夹具适配 |
| 旧T | run07/t | 2839953／224032 | 242租约，384字连续消费384拍 |

每项各运行三次：`rand+reset=1, seed=130`、`rand+reset=2, seed=130`、`rand+reset=2, seed=131`，18次均通过。这里只改变硬件初态，测试用例自身随机数种子固定，不能把它描述成三倍不同数值输入覆盖。M/S/pair严格lint通过；pair只允许旧transaction6k原有WIDTH警告，原日志保留。V/R/T基线警告在原构建中保留。

原始证据在 `validation/rtl/{m,s,pair,v,r,t}/`。每目录含receipt、原结果文件及其SHA；V/R额外保存生成夹具及适配记录。父支4a0b04e只更改了被测V group；run12替代run11/v，结果计数和周期相同。旧V收据与旧源档案完整保存在 `validation/history/pre-parent-4a0b04e/`，不改写旧结果。

`*-original-summary.json`保留完整原运行摘要，其中的其他旧结果被上表选择取代，不当作当前S/pair最终结果。

`validation/source-binding.json`把各次真正测试的文件SHA绑定到当前硬件和固定源提交。原收据的 `source_commit` 是当时输入参数，测试中工作文件以收据逐文件SHA为准，未倒填成后来提交。`tested-source-bytes.zip`保存21个源快照的精确字节，含旧版runner和V/R生成夹具；只允许Git文本换行的显式比较，不覆盖旧runner或修改原结果。

纯证据复查（无需EDA）：
```powershell
python -X utf8 project/experiments/block_feed_v1/verify_evidence.py
python -X utf8 project/experiments/block_feed_v1/test_inspect.py
python scripts/check_project.py
```
三项已通过。验证器确认26项源绑定、18份原始RTL结果和远程原始文件SHA；这不签发物理资格。

## 本地复现环境

实际运行路径：`D:/Data/LLMHardwareDesign-issue130-runtime/`；WSL Ubuntu22.04路径为 `/mnt/d/Data/LLMHardwareDesign-issue130-runtime/`。Verilator5.042来自本项目授权服务器现有安装的任务内副本，g++构建；版本、工具SHA、affinity和命令在各原始summary／receipt中。未修改系统安装或全局配置。

例如最终S/pair回归，在ASCII副本中执行：
```bash
export VERILATOR_ROOT=/mnt/d/Data/LLMHardwareDesign-issue130-runtime/tools/share/verilator
python3 /mnt/d/Data/LLMHardwareDesign-issue130-runtime/src/project/experiments/block_feed_v1/run.py --verilator /mnt/d/Data/LLMHardwareDesign-issue130-runtime/tools/bin/verilator --models s pair --workers 2 --build-jobs 4 --source-commit 4d2e9b61e4418f8161b1754576390480f400e2b7 --out /absolute/fresh-results
```

输出目录必须不存在。完整运行六项可设 `--models m s pair v r t --workers 3 --build-jobs 4`，总构建核数不超过实际affinity。当前runner只为V/R生成“参数解析之后构造DUT”的副本，父任务原测试保持原字节。

早期失败保留在任务自有 `.local/issue130/run01..run05`：较老编译器不支持旧V部分语法；中文路径生成Makefile失败。临时 `/tmp` 输出未持久化的run06不作为验收证据。旧Yosys0.9不支持当前SystemVerilog，未以它取得综合结论。

## Nangate45 实际映射与独立接收

| 作业 | 实际结果 | 证据边界 |
| --- | --- | --- |
| 93225 | 自然FAILED | RTL前检查及ABC已执行，脚本漏读Liberty导致后检查失败；未算通过 |
| 93230 | 自然FAILED | 新共享读地址的M/S完成实际ABC与Yosys后映射连接检查；M收据通过，S解析器误把两个无连接scope元信息当硬件 |
| 93233 | 自然COMPLETED，0:0，45秒 | 校验当前RTL与93230源SHA一致，核对原映射文件SHA；**重新**执行读Liberty、读实际映射Verilog、层次与连接检查；仅允许无连接scope元信息，其他未映射硬件继续拒绝 |

接收结果：M196088标准单元／867个信号pin-bit；S467658标准单元／966个信号pin-bit。Liberty典型角单元面积分别350564.326、1065777.412µm²，**不是宏占地，也未包含后续CTS／修复／物理单元**。S实际结构为四个256×128、各RD1/WR1的存储bank，未保留多余的第二套读树。

所有任务是Issue130自己的独立作业；各4CPU，两个独立综合检查并行运行。Slurm把节点RealMemory声明成1MiB占位，首次48G请求无法分配，未启动作业；随后记录实际MemAvailable并要求≥32GiB，保存memory-admission。没有停掉、重启或调整父任务的作业。此处没有把父任务的6×16队列改成4CPU。

镜像SHA：`49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a`。

最终独立接收目录：
```
/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue130-m-feed-r3-20261029/results/receive-01/
```
原映射网表／JSON／结构JSON（大文件留在授权项目存储，接收summary记录路径及SHA）：
```
/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue130-m-feed-r2-20261029/results/mapping-01/mapping/{block_feed_m,block_feed_s_macro}/
```
本地原始回执、会计终态（accounting-raw.zip为原始输出，accounting.txt仅去除显示行尾空格）、输入manifest、镜像与内存记录：`validation/remote-receive/`。`index.json`逐项列出18个抓取文件的服务器位置、本地位置与SHA，失败与新接收分目录保存。

重跑接收命令（通过sbatch，输出目录须新建；`SOURCE_ROOT`含与归档SHA一致的源）：
```bash
sbatch --output=NEW_RESULT/slurm-%j.log project/experiments/block_feed_v1/remote_mapping.sh SOURCE_ROOT NEW_RESULT PREVIOUS_ROOT/results/mapping-01/mapping
```
省略最后参数则实际重新综合，不是接收旧网表。不要在登录节点运行重EDA。

## pin 压力诊断与未完成项

`validation/pin-pressure/summary.json`绑定映射、Liberty和技术假设；`declared-strip-plans.zip`保留完整声明几何。按原四方向、8µm步距、全部接口同时引出边缘的规则：M最低边长3010µm、S3210µm；单元面积／40%目标推导边长为980／1680µm。对应占地比例9.43／3.65倍，**不是已经选择的新宏尺寸**。

这一结果揭示原全端口引出规则对新宽接口的成本。原算法的声明几何检查通过并不意味着原生布线或独立GDS检查通过；宏内二维落点与相邻S/M局部连接尚待设计和实际验证。

仍未完成：新M/S布局布线、真实接点/负载RC、300MHz setup/hold与cap/slew、最终网表功能和严格LEC、完整独立DRC；真实M→V→R组合和生产命令调度。四M扩展、完整模型或第二种实现不在本轮范围。旧物理结果不被新源继承。

协作：登记沿用[管理中心PR5](https://github.com/rayggxia-workspace/management-hub/pull/5)，本轮读回仍open、pending；缺 `config/board.json`，看板unverified／同步pending，管理员与独立审查人待指定。交接见 `docs/handoffs/2026-10-29-issue-130-m-feed.md`。
