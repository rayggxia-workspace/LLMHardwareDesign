# 固定 SRAM 的面积换速度研究（Issue247）

[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247)，负责人 Melodydt，沿用户指定 `task/242-r-load-bounds` / PR243。研究顺序为多部分和 A 分块复用、P 输入弹性缓冲、S 端口并发、M/P 规模、U 流水。SRAM 扩容保留候选，当前不实装；生产 RTL 保持。

阶段1沿用 PR241 的条件原生 S32/96 位累加模型，不是生产 M 的算术资格。仅对单行静态权重且完整 A 无法驻留的矩阵，把输出列分组，再按 K 块逐组更新部分和。保持两 P/一 U、各16KiB、N8、双 A/B 缓冲、32信用、17.1GB/s及原权重布局。增加的96位部分和寄存器与切换拍数单列，不免费扩大 SRAM、M 算力或本地 S 端口。

`contexts=1` 调用原版 worker，删除新增 `context_study` 后完整输出必须与 Issue245 结果逐字段相同；`reuse_A=0` 保持新顺序但每 tile 重新读取 A，用于区分重排与复用。切换1拍为研究假设，另测0/3/8拍。每个 A bank 必须等所有消费者完成后才能复用，B 双缓冲单独管理；每个 context 保持 K 顺序，最终一次舍入。

服务器运行（先核验源码和输入清单；固定版本见 `source.json`）：

```bash
sbatch --parsable job.sh
python3 -B project/experiments/area_speed_study/run.py --inputs /absolute/inputs --out /absolute/new-results
```

runner 要求 Slurm 分配核数，最多并发4个单线程 case；严格 C++17/-Wall/-Wextra/-Werror。先执行原 kernel/validation/smoke/oracle 和独立 context 数值/生命周期 oracle，再运行完整 trace，逐项审计流量/容量/算术/ACK及负例。

冻结基础功能文件和输入 SHA 由 `source.json` 指定。完整日志、生成代码、二进制、结果及输出 SHA 留服务器本人目录；仓库收录轻量索引和正式报告。时延来自抽象 DDR/端口模型；实际数值、RTL、物理面积/时序/能耗和真实生成需分别验收。
