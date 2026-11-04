"""Regenerate the Chinese report and CSV solely from audited frozen evidence."""
import csv
import hashlib
import io
import json
from pathlib import Path

from check_evidence import DEFAULT, ROOT, audit


def main():
    verified = audit(DEFAULT)
    path = DEFAULT / 'result/results.json'
    results = json.loads(path.read_text())
    rows = {r['name']: r for r in results['runs']}

    def table(names):
        text = '| 配置 | S / 组 / 通道 | 信用 / 队列 | LOAD GB/s | STORE GB/s | LOAD P99 ns |\n'
        text += '|---|---|---|---:|---:|---:|\n'
        for name in names:
            r = rows[name]
            text += (f'| `{name}` | {r["active_s"]} / {r["groups"]} / {r["channels"]} '
                     f'| {r["credits"]} / {r["queue"]} | {r["load"]["gbps"]:.3f} '
                     f'| {r["store"]["gbps"]:.3f} | {r["load"]["p99_latency_ticks"]/3:.1f} |\n')
        return text

    scale = table(n for n in rows if n.startswith('scale-'))
    credit = table(n for n in rows if n.startswith('credit-'))
    clocks = table(n for n in rows if n.startswith('clock-'))
    width = table(n for n in rows if n.startswith('width-') or n.startswith('fair-'))
    blocked = rows['held-s0']['load']['other_completions_during_s0_hold']
    report = f'''# 多私有 S／HBM 供数：服务器架构与 RTL 验证结果

2026-11-04，Asia/Shanghai。任务 [Issue #181](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/181)，成果 [PR #182](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/182) 待独立审查、未合并；执行账号 huangpingyang04-lgtm。用户确定的范围是架构与仿真验证。

## 结果与结论

服务器 Slurm **{verified['job_id']}，c64/node1，4 CPU，COMPLETED 0:0、TimeLimit=UNLIMITED**。35 组正向配置、5 类预期拒绝负控制通过；实际运行 230 个 8×32 乘 32×8 矩阵，核对 **14,720 个 S64 输出**，累计 **3,362,870 次运行断言**（其中包括等待上限和逐拍检查，不是同等数量的独立案例）。原版 S/feeder/M 源保持 main 的逐字节身份。

这轮支持的结论：有限多目的地供数、跨时钟 FIFO、S 真实写确认、原生 feeder→M、M 实际结果写回 S→外存模型能够组成可验证的闭环；分通道与足够在途资源有助于本模型的吞吐。**尚不能据此宣称真实 HBM 速度、JEDEC 合规、完整 AXI 接入、减扇出收益或物理时序通过。**

## 实际执行路径与归属

```text
有界多通道/4-bank时序模型（默认500MHz用户侧）
    → 每S请求异步FIFO → transport → 原S真实写ACK
    → 原S存储/feeder（300MHz）→ 共享原版M数值验证器
    → 夹具读取实际M响应 → 同一transport写回S
    → S真实读响应 → 响应异步FIFO → 外存模型STORE及写完成
```

验证顶层实际包含 **16 份独立16KiB标准单元 S、16份原feeder、一份共享M**，每例激活2/4/8/16份S。M按S顺序复用；不是16个同时计算的大Block。其共享选择网络是数值夹具，不作为最终片上互联或扇出优化的物理实现。

新增可综合RTL是异步FIFO与S事务endpoint：每S两份16×155bit FIFO及等待真实S响应的状态。155bit包为write1/tag16/word_address10/payload128。所有权、信用账本、组间/组内轮询、外存时序及M回写编排位于 **C++架构夹具**；未把这些软件逻辑冒称已实现的C/D、仲裁或完整AXI RTL。

每S先LOAD 48个矩阵容器和bulk压力字；核对写ACK后，原feeder读取S并送M。实际M输出的32个128bit字由夹具写入S地址80..111，STORE读回输入/压力数据及这32字输出，在独立结果数组逐项验证。没有直接预装S内部RAM，没有用oracle结果替代M输出。全部例LOAD有效字节合计1,069,568，STORE合计1,187,328；结果写S阶段另行计时。

## 固定假设与计量方式

时基1/3ns，核心周期10tick=300MHz；默认用户侧6tick=500MHz。HBM引脚时钟/PHY没有建模。模型默认每通道256bit用户总线、4bank、64项有限队列、20用户周期返回基延迟、行变化额外6周期、bank命令间隔2周期、读写方向变化停4周期；每512周期前16周期禁止数据传输。刷新时仍可有限接收/安排后继请求，是简化控制器假设，不代表真实命令合法性。

默认每S16信用、每次LOAD grant最多4字。信用从发请求保持到S写ACK返回或STORE外存写完成，包含模型队列、在途、CDC及S等待。两级轮询选择组和组内S；无信用/无剩余任务者跳过。每组单独token桶每300MHz周期补一个128bit字，容量2字，限制组链路带宽。

默认每组两个S，`group_id % channels`分配通道。下表通道数是本架构模型资源数，不等同于指定HBM代际的物理通道定义；256bit是模型的用户接口宽度。未校准厂商VIP、Ramulator或实际器件参数。

GB/s = 成功退休有效字节 × 3 / 本阶段tick数，**包括初始等待与尾部排空**。LOAD从空队列到所有S写确认退休；STORE从S读请求到最后外存写完成。矩阵验证和结果写S分别执行，不包含在这两个阶段吞吐内，所以这些数字不是完整工作负载吞吐，也不是持续读写混合吞吐。P99按排序位置取样；端到端延迟从任务发出算至实际退休。

## 规模和通道对照

{scale}
8S由共享1通道改为4通道，LOAD从{rows['scale-s8-ch1']['load']['gbps']:.3f}提高至{rows['scale-s8-ch4']['load']['gbps']:.3f}GB/s；16S/8组/4通道达到{rows['scale-s16-ch4']['load']['gbps']:.3f}GB/s，低于组链路理论合计38.4GB/s。16S共享1通道反而低于8S共享1通道：增加S同时增加队列和调度竞争，不能假定实例数越多吞吐一定越大。

## 信用与队列容量

{credit}
相同8S/4组/4通道下，信用1→2→8→32、队列64时，LOAD约2.016→3.975→14.886→18.065GB/s。队列只有4项时，即使信用提高到32，LOAD仍约6.134GB/s。结论是**信用与接收队列要匹配**；扩大一个参数不能补齐另一个短板。大信用还会提高请求排队延迟，见P99。

## 用户时钟与相位

{clocks}
period5/6/10/15分别是600/500/300/200MHz用户时钟；核心始终300MHz。同频非零相位也执行异步FIFO路径。所有数据与矩阵检查通过，证明本RTL数字仿真的跨域行为；不证明任意亚稳态、单端复位、CDC布局约束或真实500MHz时序。

## 宽度与突发长度

{width}
宽度128→256提升当前共享通道LOAD，而512没有进一步提升，说明命令、bank、目的地、有限队列和组链路也会成为瓶颈。STORE请求入口每通道每用户周期只发一个128bit S读任务，是本原型显式入口瓶颈；因此加宽外存数据口不会单独提高其吞吐。这是模型入口限制，不能解释为HBM硬件写能力上限。

## 背压、公平性、复位及负控制

- S0在LOAD阶段暂停2000个核心周期（约6.667µs），其余7S仍完成全部 **{blocked}笔** LOAD；没有被S0拖停。全部S最终完成且信用/队列排空。
- 连续有剩余任务和信用时，所记录的最长其他获选轮数不超过同例S数减1；这是轮询机会检查，不是无条件的端到端延迟上界。无信用与物理背压等待另计。
- 对每个被背压的响应逐字检查valid、tag、地址和数据保持；对读/写确认检查目的地/事务标识，不重复退休。
- 在有在途请求时执行平台协调reset：同时清控制器队列、两侧RTL FIFO及信用，再重新发请求；S内容不依靠reset清零。未实现单独复位DMA后接收旧响应的恢复协议。
- 三种Verilator初态×两随机种子均通过。其他例另覆盖长延迟、刷新对照与burst1/16。
- 5类负控制分别是损坏payload、损坏tag、非法S数量、地址extent越界和零信用；均非零退出并匹配预期原因。后3类是配置入口拒绝，前2类是夹具运行期检出，不代表硬件协议错误恢复。
- 独立Python检查器重算字节数、信用/队列上限、吞吐和链路上界，核对全35例/5负例、原始日志SHA及固定源。额外篡改吞吐、信用和数值覆盖的3个内存负例均被拒绝。

## 复现与来源

- 最终运行输入commit：`{verified['source_commit']}`；原宏base：`4b1df2c7cbdaa0fa6f9f468f2b5b854cec875609`。
- 工具：Verilator5.042（报告revision为UNKNOWN.REV，实际二进制SHA另存）；g++11.4；现有只读ORFS容器。最终C++开启`-Wall -Wextra -Werror`，无构建警告。
- [完整模型说明与启动流程](../../project/experiments/hbm_feed/README.md)、[启动器](../../project/experiments/hbm_feed/launch.py)、[逐例配置与原始结果](../../work/huangpingyang04-lgtm/181/evidence/release/result/results.json)。
- [Slurm终态](../../work/huangpingyang04-lgtm/181/evidence/release/scheduler.txt)、[逐文件SHA索引](../../work/huangpingyang04-lgtm/181/evidence/release/reception-index.json)、[本地实收回执](../../work/huangpingyang04-lgtm/181/evidence/release/LOCAL_RECEPTION.json)、[独立审计](../../work/huangpingyang04-lgtm/181/INDEPENDENT_CHECK.json)。
- 最终服务器目录：`/public/home/yuzelu/PingyangHuang/issue181-hbm-r03-20261104`，源码归档及实际执行二进制留原目录，大小和SHA在实收索引。47项轻量原件、210,428字节逐字节实收。
- 初轮97159：35例/230矩阵通过，但当时尚无M结果写回；中轮97160补齐闭环、35例/5负例通过，保留4条C++排版警告。最终97162修正排版并启用Werror，数值和性能指标与97160一致。全部原件分别保存在preliminary/final/release，不覆盖历史、不将初轮当作完整闭环。

```powershell
python -X utf8 -B project/experiments/hbm_feed/check_evidence.py
python -X utf8 -B project/experiments/hbm_feed/summarize.py
python -X utf8 -B scripts/check_project.py
```

## 可行性与下一步接口

架构/仿真层面已得到可执行正证据。推荐保持300MHz本地计算，采用分组寻址与多外存通道，按真实搬运量配置并发和有限缓冲；不要把所有S重新汇入一个128bit公共瓶颈。下一阶段应把当前C++分组仲裁/元数据账本落实为RTL，与现有control_d多S扩展或明确替代实现衔接，再完成完整AXI、位宽适配和所选HBM控制器接口合同。

本原型没有实现真正HBM控制器/PHY/训练/ECC、HBM2/3完整bank时序、完整AXI五通道转换、16路并行计算、完整模型推理、同一S计算与补料并发、P&R/扇出/面积/功耗或封装。当前结果不能转授既有宏或系统物理资格；真实HBM吞吐仍需器件参数校准、完整协议仿真或平台实测。

协作：rayggxia-project-collab1.0.0；登记management-hubPR5已读回仍open/unmerged，pending；缺config/board.json且无Projects条目/字段工具，看板unverified、同步pending。独立审查人及看板管理员待指定，Issue保持in_review，PR不自行合并。
'''
    out = ROOT / 'docs/experiments/issue-181-hbm-results.md'
    out.write_bytes(report.encode('utf-8'))
    csv_path = ROOT / 'work/huangpingyang04-lgtm/181/metrics.csv'
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(['case', 'S', 'groups', 'channels', 'credits', 'queue', 'load_GBps', 'store_GBps', 'load_p99_ns'])
    for r in results['runs']:
        writer.writerow([r['name'], r['active_s'], r['groups'], r['channels'], r['credits'], r['queue'],
                         r['load']['gbps'], r['store']['gbps'], r['load']['p99_latency_ticks']/3])
    csv_path.write_bytes(stream.getvalue().encode('utf-8'))
    manifest = dict(input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    report_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
                    csv_sha256=hashlib.sha256(csv_path.read_bytes()).hexdigest(),
                    source_commit=verified['source_commit'])
    (csv_path.parent / 'REPORT_MANIFEST.json').write_bytes((json.dumps(manifest, indent=2)+'\n').encode('utf-8'))
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
