"""Write the first-round handoff only from completed calibration and audit files."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
result = json.loads((HERE / 'candidate-rollup.json').read_bytes())
check = json.loads((HERE / 'rollup-check.json').read_bytes())
jobs = json.loads((HERE / 'fast-jobs.json').read_bytes())
final_jobs = json.loads((HERE / 'job-final-status.json').read_bytes())
assert final_jobs['selected_completed'] and not final_jobs['active_in_this_round']

def span(values, digits=3):
    return '–'.join(f'{v:.{digits}f}' for v in sorted(values))

rows = []
widthrows = []
for model in result['models']:
    for phase, label in [('prefill', '短 P2（冷状态外推）'), ('decode', '第二步 Decode')]:
        window = model['windows'][phase]
        candidate = window['candidate']
        rows.append('| ' + ' | '.join([
            model['name'], label, span(window['baseline']['on_chip']['mean_w']),
            span(candidate['on_chip']['mean_w']), span(candidate['on_chip_plus_ddr']['mean_w']),
            span(candidate['on_chip']['mj_per_token'], 1),
            span(candidate['on_chip_plus_ddr']['mj_per_token'], 1)]) + ' |')
for item in check['checks']:
    if item['phase']=='decode':
        widthrows.append(f"- {item['model']} 第二步 Decode：区间宽度由 {item['old_width_w']:.6f} W 变为 {item['candidate_width_w']:.6f} W，缩小 {item['width_reduction']:.2%}。原状态代理占原宽度的 {item['old_state_proxy_width_fraction']:.2%}。")

joblines = []
for name, job in jobs.items():
    cal = json.loads((HERE / (name + '-calibration.json')).read_bytes())
    assert cal['gate_replay_pass'] and len(cal['windows']) == 12
    collection = json.loads((HERE / 'results' / name / 'collection.json').read_bytes())
    assert collection['jobs']['power_job'] == job['power_job']
    path = job['directory'] + '/' + job.get('power_subdir', 'power')
    joblines.append(f"- {name}：综合 {job['job']}，完整门级回放 {job['gate_job']}，最终功耗 {job['power_job']}；映射 {cal['source']['cell_count']:,} 单元。结果 `{path}/calibration.json`，日志 `{path}/slurm-{job['power_job']}.log`。若回放与功耗号相同，两阶段由同一作业完成；历史尝试的阶段通过与作业终态分别记录。")

body = '''# GDN / Mamba 状态更新第一轮交付

负责人 Melodydt，2026-11-18，Asia/Shanghai。项目 llm-hardware-design，关联 [Issue #280](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/280)，上游 [PR #281](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/281)。

本轮完成两个候选电路的真实捕获回放、连续状态压力检查、200 MHz 综合网表活动功耗及双口径模型积分。仅把 v3 中 GDN / Mamba 状态代理替换为具体候选情景；正式七模型默认数值保持不变。不存在完整 512-token Prefill 重测。本轮选用作业均已 COMPLETED 0:0，没有本轮遗留运行或等待作业；其他会话的作业不在该结论范围内。

## 200 MHz 条件估算结果

| 模型 | 窗口 | 原 v3 片上 W | 候选片上 W | 候选片上＋DDR W | 候选片上 mJ/token | 候选片上＋DDR mJ/token |
|---|---|---:|---:|---:|---:|---:|
''' + '\n'.join(rows) + '\n\n' + '\n'.join(widthrows) + '''

采样端点是两个早期通道块的活动差异，不是统计置信区间，也不是全模型保证误差界。Prefill 样本均为全零初态，只支持冷状态外推；Decode 具有真实历史状态。独立层及更长真实输入覆盖待补。

## 本轮完善的部分

- Qwen3.5 的 GDN 已绑定固定 R RTL、真实输入、完整装载/执行/读回命令及门级内部活动。
- Falcon 宽系数 S32/Q24 候选解决原 S16/Q14 的样本系数越界，采用 65-bit 乘积寄存器和 72-bit 点积；它是实际测量的候选版本。
- 所有输出与每个状态元素均对各自定点参考逐字一致。相对冻结浮点 Q16，Qwen 正常输出/状态最大差为 1/2 LSB、32 步压力为 1/18；Falcon 宽系数正常为 53/12、压力为 125/13。压力输入交替复用捕获样本，不是真实长序列。
- 用活跃减等长静默的增量，按两批八路归并一个 16 通道服务；整窗另加一个共享 R 的静默驻留，避免漏计内部状态存储与控制。
- Falcon 外部 delta×value 注入继续保留 E32 标量代理。格式转换、真实集成接口和跨块传输仍未标定。
- 固定 v3 比较基线，不混入上游控制 v4/v5；代码、结果、网表、波形、工具、原始输入均有 SHA 追溯。

## 方法与边界

固定 200 MHz / 5 ns，Nangate45 typical，零延迟综合网表 VCD。未加载布线寄生、SDF 或完成物理时序签核。R 内部两组状态 bank 映射为触发器，系统数据 SRAM 基线仍为 512-bit；两者不是同一存储物。

模型情景采用一个共享八路 R。检查累计服务时间不超过冻结 TLM 窗口只是必要条件，尚不能证明真实调度/部署已实现。原速度不变。其他 v3 分项和 DDR 保持固定；读 DMA 实测、控制外壳/全局时钟/实际门控、集成互连、DDR PHY/板级 I/O 等 v3 缺项继续存在。

该候选 R 尚未成为七模型共用的冻结芯片配置。若后续统一使用同一芯片，其他模型的 R 漏电与门控驻留也须按一致的部署合同补计，不能只替换两个模型就声称完成统一硬件比较。

精度尚无独立模型级验收。Falcon 单次 Python 诊断中，精确注入可把状态最大差从 12 降至 4 LSB，合并一次舍入再降至 1 LSB（输出仍 30 LSB）；该诊断尚无对应 RTL，不能拿其精度替换本次实际候选。

## 作业与版本

服务器 `yuzelu@10.129.166.172`。以下为本轮选用作业，最终状态及退出码见 `job-final-status.txt`；12 核、UNLIMITED，目录均在本人的 `Melodydt/runs/issue-280/recurrent-round1-20261118` 下。

''' + '\n'.join(joblines) + '''

综合命令：`sbatch --parsable --time=0 run_fast_calibration.sbatch`。完整活动命令：`sbatch --parsable --time=0 run_full_gate_power.sbatch`，目录为 `power-full/`。`generate_gate.py` 显式开启 `--trace-underscore`，分拆生成使用 `--output-groups 0`，再以隔离 Clang 14 / C++20 / -O0 构建；不改变 RTL、网表或命令向量。工具包来源与散列见 `compiler-install.json`，实际编译器、生成文件清单和二进制散列见 `generation-receipt.json` / `low-build-input.json` / `prebuilt-receipt.json`。

OpenSTA 读取原网表时不接受 `wire signed` 语法；`sta-view/` 仅移除 160 处结构声明的 signed 关键字，宽度、单元、连接和 assign 保持逐字一致，核对单元数不变。两个视图检查作业 120376/120377 为 COMPLETED 0:0。选用目录中的功耗脚本核验门级回放 SHA 检查点、真实 VCD 层级及内部网络，再读取兼容视图；四路独立窗口各用三线程，合计不超过 12 核。`run_final_power.sbatch` / `calibrate_final.py` 是为原始 `power-full` 路线预置的后处理，若作业被替代并取消，则不作为最终结果。历史失败日志和最终有效结果分别保留，不能把流程曾经失败写成全部作业成功。

额外的 120422 逐位图审计为 COMPLETED 0:0：以同一 Yosys 分别读取原始和兼容视图，逐一比较所有单元类型/参数/引脚位、顶层端口方向与位、全部命名网络的位和范围；仅忽略 signed 元数据和源位置属性。两模型 912,206 / 944,203 个单元全部通过，未残留行为单元。该审计把兼容语法处理与原始门级功能连接起来，原/新网表及图 SHA 见 `signed-graph-audit.json`。

当前 OpenSTA 对内部网线名的预检标注数为 0，明确单元引脚名的共享 ID 预检为 2。完整追踪已经原生包含单元引脚层级，因此先从精确 STA 网表重新读取 `sta_graph.json`，逐一核验连接引脚、端口位及全部初始波形值，覆盖完整时直接使用原始 VCD。仅当输入缺少原生引脚层级时才启用位连接别名转换；实际采用方式见 `pins.json`。每个窗口必须精确标注所有已连接引脚/端口位，Qwen 4,004,878、Falcon 4,125,979。`verify_pin_mapper.py` 对原生覆盖、缺初值拒绝、标量、向量、常量、共享 ID、时间戳及输入变化拒绝的检查通过。初次图预检 120381/120382 漏设时钟而失败，修正的 120383/120384 已通过；初次仅接口波形的 120380 只验证工具格式，排除于能耗结果。完整原生引脚的短前缀预检 120390 也只检验读取/覆盖，不参与模型积分。

跟踪与复查：`sacct -X -j <作业号> --format=JobID,State,Elapsed,ExitCode`；在对应功耗目录运行 `tail -n 30 slurm-<作业号>.log`、`cat calibration.json`、`sha256sum -c inputs.sha256`。逐窗 OpenROAD 日志及 SHA 已下载；大网表、VCD、门级二进制留在服务器。工具实测版本及镜像 SHA 见 `toolchain.json` 和各 `calibration.json`。

固定基础 R 来源 commit `f034be2b7c87137b92f7bfce274a5485647e512d`。两个实际 RTL 副本在 `rtl/`，源修改和 Linux 换行 SHA 在回执中区分。200 MHz v3 快照 `baseline-200mhz-v3.json` 的 SHA-256 为 `25ecc38c734d806c2592fcbba5503ea7c0cff6884e3c43fd97bb2c31c56bac00`。

失败/替代记录：120315/120316 在容器启动前因脚本换行错误失败；原综合 120317/120318 因存储共享后清理耗时较长，被同 RTL 的 120331/120334 全映射结果替代，原依赖 120320/120321 同时取消。GCC 构建 120335/120336/120358/120363/120369 已取消并保留日志。Clang 初次回放 120371/120372 默认隐藏下划线命名的内部网络，其波形不满足本轮活动验收，不用于功耗结果。完整后继记录见 `fast-jobs.json`；被取消或未通过覆盖的尝试不记为功耗成功。

## 复现与交付

在仓库根目录或完整结果包解压根目录运行：

```text
python -B work/Melodydt/280/recurrent-step1/rollup_candidate.py
python -B work/Melodydt/280/recurrent-step1/verify_candidate.py
```

RTL 数值复现命令见 README；需要 NumPy 和 ModelSim，门级复跑需要上述服务器工具。PDF 生成入口为 `build_delivery_pdf.py`，打包入口为 `package_delivery.py`。管理结构检查为 `python scripts/check_project.py`，不能替代业务/物理检查。实际验证清单和 PDF/ZIP SHA 见最终交付回执。

交付目录为 `output/pdf/seven-model-sync/2026-11-18-r4/`：`200mhz-power.pdf` 是 9 页主报告（5 页新候选标定加 4 页冻结七模型 v3 附录）；`recurrent-state-first-round-bundle.zip` 包含原始捕获、命令、RTL、校准回执和可独立复算脚本。`combined-receipt.json` / `bundle-receipt.json` 固定 PDF/ZIP SHA；本实验目录的 `pdf-visual-review.json` / `validation.json` 记录全页检查和实际验证。原五页 `recurrent-state-first-round.pdf` 仅为合订版生成源。

本地隔离目录为 `work/Melodydt/280/recurrent-step1/`，根目录副本没有 `.git`。独立分支为 `task/280-recurrent-first-round`，目标基分支为 `task/280-seven-model-energy`；实际提交/PR 回执见 `publication.json` 与在线分支。完整捕获 ZIP 仅保存本地/获授权服务器，不将原始张量包发布到公开仓库。主会话 `closure-v5` 和其共享本地进度文件未修改；公共进度与复现入口通过本轮独立分支提交审查。

独立分支创建时的 head 为 `de9fd4befa54a1334efd831f7992cac0d25460da`。上传前读取上游 head，以其文件树保留主线进展；本轮提交及基准 SHA 见 `publication.json`，修改另以文件清单 SHA 固定。基础 R 的 `f034be2b7c87137b92f7bfce274a5485647e512d` 只表示原始 RTL 来源，不代表本轮候选和报告已在该 commit 中。

首次公开上传曾被自动审批拒绝，原因是内部服务器地址、远程路径和实验元数据的公开授权不明确。用户审阅本地报告及待发布清单后，明确回复“正常上传”，现已授权该范围。此后按清单通过 Melodydt 连接发布；实际提交、PR、读回验证和登记状态见 `publication.json`。历史拒绝与本次明确授权分别保留，不将授权本身写成已经上传或合并。

## 后续与验收状态

第一轮技术交付完成后，剩余事项为：
1. 扩展独立层、非零 Prefill 状态和真实更长序列，核验误差累积及模型输出精度。
2. 确认共享 R 的实例数、装载路径、真实调度、驻留和门控，校准集成接口及格式转换。
3. 实现并标定 Falcon 注入与单次舍入候选，再与现版同口径对比。
4. 精度和部署合同验收后再更新正式七模型默认值；如要求物理结果，另补时序及寄生。
5. 独立审查人待指定，完成审查/合并；#280 的其他能耗覆盖由其主线继续维护。

规则 rayggxia-project-collab 1.0.0。当前第一轮可审查，整体 Issue 保持 in_progress；不标 done。项目登记沿用 management-hub PR #5 的 pending 记录，最终读回状态见 publication.json。看板缺 config/board.json 和 Projects 能力，条目 unverified、同步 pending，由有权限维护者接续。没有配置聊天结束后的自动监测。
'''
optimized=[key for key,value in jobs.items() if value.get('selected_stage')=='trace_optimized']
if optimized:
    body=body.replace('## 复现与交付', '''## 同源波形输出优化的采用

选用模型：'''+', '.join(optimized)+'''。完整引脚追踪使 -O0 回放耗时较长，因此在独立目录重新编译相同生成代码的 Trace 更新函数为 -O1。如 `fast-jobs.json` 的 `opt_stage` 为 `logic`，该模型又将 FAST 门级计算函数编译为 -O1，并保留前一轮 Trace 目标文件；慢速初始化对象继续采用固定的 -O0 版本。生成的 C++、RTL、网表、输入向量均未修改；原 archive 校验后只替换指定目标文件，再重新链接。编译命令、生成文件 SHA 与最终二进制 SHA 保存在 `low-build-input.json` / `prebuilt-receipt.json`，logic 路线同时保存前一轮构建回执。

启动入口为 `sbatch --parsable --time=0 run_trace_optimized.sbatch`，logic 路线为 `run_logic_optimized.sbatch`；均为 12 核、UNLIMITED。目录、选用作业及原活动来源见 `fast-jobs.json` 和 `trace-opt-jobs.json`。最终选用必须通过完整门级逐字回放、全引脚覆盖及全部配对功耗。优化前后完整波形声明及前 100 ns 事件另作逐字节一致核验。Falcon 的两版完整波形 SHA 也完全相同，输入和功耗脚本相同，因此在保留 120413 完整评估的同时提前停止重复流水线；证据见 `falcon-full-wave-equivalence.json`。Qwen 在最终功耗通过后停止冗余作业。120393 动态库路径错误的试点被取消，后继修正了路径及失败即停止行为；失败试点不作结果依据。选用作业的最终数字与 SHA 来自其独立输出目录。

## 复现与交付''')
(HERE / 'DELIVERY.md').write_text(body, encoding='utf-8')
handoff = ROOT / 'docs/handoffs/2026-11-18-issue-280-recurrent-first-round.md'
handoff.write_text(body.replace('见 README', '见 `work/Melodydt/280/recurrent-step1/README.md`') +
    '\n\n本文件引用的相对实验文件均位于 `work/Melodydt/280/recurrent-step1/`。恢复第一步：读 `publication.json` 与选用作业终态，核对 source/input SHA，再运行两条积分复算命令。\n', encoding='utf-8')
print('DELIVERY_DOCS_WRITTEN', handoff)
