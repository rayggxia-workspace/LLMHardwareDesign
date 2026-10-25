# Issue99 R 状态单元

本目录实现/验收单 head D128×N256 的 S32 连续递推、全 head range guard、RNE 重标、有限外部 trial/proposal/shadow 和原子发布。它不等于完整 R Block、32head 全链或物理签核。主代码在 `project/rtl/r_state/r99.sv`；先读 `PROTOCOL.md` 和机器合同 `contracts.py`。

所有实际张量、bigint、RTL、Yosys/map/gate 在已授权本人服务器 Slurm 执行；PC 仅语法、管理结构和字节校验。复用72整数coeff/单位，不运行模型/下载权重。输入固定 source SHA；共享 B/C 为 [72,256]，不是逐head张量。

服务器源码阶段含根 `binding.json`；以任意新输出目录运行（不得覆盖）：

```bash
python -B project/experiments/r_state/inputs.py --old /public/home/yuzelu/RuizhiLiang/issue72-numeric-closure-20261024 --out NEW_INPUT
python -B project/experiments/r_state/run.py build --out NEW_BUILD
python -B project/experiments/r_state/run.py sim --input NEW_INPUT --build NEW_BUILD --mode real --stall 0 --out NEW_RUN
python -B project/experiments/r_state/verify.py --input NEW_INPUT --run NEW_RUN --out NEW_RECEIPT.json
```

`mode real/protocol/boundary` 分别做72步、恢复协议、19项合成边界；每种 `stall 0/1`。`run.py map --library EXACT_LIBERTY --out NEW_MAP` 映射真实库存，单16KiB SRAM黑盒与外部fabric面积除外。`analyze.py`严格接收六路以及原Liberty独立area sum；`negative.py`实际改输出/单位/提交记录并重SHA，再调用完整receiver。

门级：`gate.py prepare`只从已接收real72的首步与真实重标前一状态抽取检查点，导出actual mapped JSON和Liberty行为模型；同 `checkpoint_sim.cpp` 分别建RTL/gate。先 `sim` + `pilot` 验收首步，实测决定剩余三条件。`receive`要求4gate+4RTL全部逐码一致，`gate_schema.py`再核完整行schema、公共metadata、同条件cycle/IO相等。无门级Qpoke，72连续仅RTL。

完整实际命令/作业、最终源码与成果SHA见 `work/Liangruizhi/99/` 和 `results/issue-99/index.json`；正式数据大包留服务器。PC运行：

```text
python -B scripts/check_project.py
python -B project/experiments/r_state/verify_archive.py --archive project/experiments/r_state/results/issue-99/selected.zip --index project/experiments/r_state/results/issue-99/index.json --kind selected --out D:/Projects/Codex/NEW_OWN_TASK/byte-receipt.json
```

`verify_archive.py`仅读取字节，不做张量运算。科学包保留失败输入提取/语法日志与先前输出；源码原Git SHA校验和字节接收不能替代独立bigint/RTL/gate验收。离线研究面积不是目标工艺PPA、SRAM面积或STA通过。
