"""Generate the current RTL report from independently audited server evidence."""
import hashlib
import json
from pathlib import Path
from check_rtl_evidence import ROOT, DEFAULT, audit


def main():
    verified = audit()
    data_path = DEFAULT / 'result/results.json'
    result = json.loads(data_path.read_text())
    rows = {r['name']: r for r in result['runs']}
    def table(names):
        text = '| 配置 | S / 组 / 通道 | 信用 / 模型队列 | LOAD GB/s | 第二搬运阶段 GB/s | 最长轮询绕过 |\n'
        text += '|---|---|---|---:|---:|---:|\n'
        for name in names:
            r = rows[name]
            text += (f'| `{name}` | {r["active_s"]} / {r["groups"]} / {r["channels"]} | '
                     f'{r["credits"]} / {r["queue"]} | {r["load"]["gbps"]:.3f} | '
                     f'{r["store"]["gbps"]:.3f} | {r["load"]["max_bypass"]} |\n')
        return text
    scale = table(n for n in rows if n.startswith('g'))
    capacity = table(n for n in rows if n.startswith('credit'))
    clocks = table(n for n in rows if n.startswith('clock'))
    cases = table(['held-s0', 'held-completion', 'paused-core', 'long-latency', 'mixed-directions',
                   'coordinated-reset', 'read-error-drain', 'write-error-drain', 'bad-id-recovery',
                   'duplicate-recovery', 'upper-boundaries', 'full-16k-descriptor'])
    report = f'''# 分组仲裁与多S搬运RTL：服务器验证结果

2026-11-04，Asia/Shanghai。更新同一[PR182](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/182)、[Issue181](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/181)。执行账号huangpingyang04-lgtm。原[第一阶段架构实验](issue-181-hbm-results.md)作为历史基线保留，当前结果以本报告为准。

## 已完成

最终服务器 **Slurm97178，c64/node1，4CPU，TimeLimit=UNLIMITED，COMPLETED0:0**。新分组仲裁和多S搬运由实际RTL执行，C++不再代替轮询、事务分配、S选择或槽退休。

- **38组正向场景、228个RTL非法描述符/配置拒绝、1个坏payload预期失败负控制通过。**正向场景包括外存错误完成、坏ID/重复响应检出并协调复位恢复，不把“检出故障”描述为故障流量计算成功。
- **238个实际原版S/feeder/M矩阵、15,232个S64结果、6,912,294次运行检查通过。**检查次数包括等待/逐拍断言，不等于相同数量独立案例。
- **4S及16S完整DMA核心均完成Yosys通用门级综合、check-assert及无锁存器核对。**通用单元数分别60,581/366,562，未映射Nangate45 Liberty，不能作为面积或时序数据。
- Verilator lint、C++`-Wall -Wextra -Werror`构建、独立证据审计及3个篡改负控制通过。Yosys保留17种memory-to-register提示，未关闭或删除提示，原日志中check报告0问题。

## 改成RTL的部分

模块[ hbm_group_dma.sv ](../../project/rtl/hbm_feed/hbm_group_dma.sv)实现：每S独立描述符/游标、一项活动任务及保持完成、每S最多8个有限槽、代次tag、真实LOAD/STORE生命周期、S端口请求保持、组间/组内轮询、响应归属/状态检查、错误停止新字分配并排空、协议错误sticky状态。

描述符包含方向、40bit外存字节地址、10bit S字地址、11bit字数及16bit任务tag。LOAD直到真实S写ACK才释放槽；STORE先读真实S，再等外存写响应释放槽。每次轮询授权一个128bit字；请求在异步FIFO背压时保持完整内容。每通道185bit请求/146bit响应经过真实双时钟RTL FIFO。

验证组合实际实例化16份原版16KiB S/feeder及一份共享原版M；按场景激活2/4/8/16份S。M仍作为顺序数值验证器，不是16个并行计算Block。本续作新增的是事务级D原型，并未把既有control_d/系统控制RTL替换或宣称其资格继承。

**本轮C++只负责配置描述符、外存有限时序/数据模型和独立oracle。**它接受RTL自行发出的请求，允许不同ID乱序返回；不直接写S内部存储，不维护硬件信用或选择下一搬运字。LOAD→真实S→feeder→M核对数值；STORE读取真实S全部字节并与独立外存图像核对。M结果写回适配器未纳入此轮新增RTL；第一阶段的夹具回写证据仍单独保留。

## 规模和通道

{scale}
当前原型每通道只有一个128bit/core-cycle请求入口，300MHz理论上限4.8GB/s；4通道合计19.2GB/s。默认信用4时，16S/4通道LOAD约{rows['g4-s4-ch4']['load']['gbps']:.3f}GB/s，STORE约{rows['g4-s4-ch4']['store']['gbps']:.3f}GB/s；8S从1通道到4通道约{rows['g4-s2-ch1']['load']['gbps']:.3f}→{rows['g4-s2-ch4']['load']['gbps']:.3f}GB/s。数据来自真实RTL握手及模型等待，不沿用第一阶段C++调度器的吞吐数值。

## 在途信用和模型队列

{capacity}
8S/4通道下，信用1、2、4、8与32项模型队列的LOAD分别约1.438、2.875、5.623、10.778GB/s。信用8但队列4时约4.637GB/s，说明FIFO往返、响应等待和模型接收容量仍需匹配。最大信用由RTL槽数限定，未把第一阶段32信用当作当前硬件能力。

## 时钟与相位

{clocks}
period5/6/10/15分别对应600/500/300/200MHz用户侧，核心始终按300MHz运行；phase是1/3ns tick偏移。同频异相也走异步FIFO。暂停核心时钟的定向场景额外检验响应FIFO满背压。上述是数字仿真，不包含亚稳态MTBF、CDC物理约束或时序签核。

## 定向场景

{cases}
- S0阻塞2000核心周期时，其余7S完成全部 **{rows['held-s0']['load']['other_s_acks_during_hold']}** 次S访问（7×256），随后S0也完成且全部槽排空。
- 完成被主机背压时，tag/status/成功字数稳定。每次S请求被背压和内存请求被背压均逐位核对保持。
- 每通道先选组再选组内S；实际grant对应预边沿具备资格的源。最长连续被其他源绕过轮数不超过同例活动S数减1，16S共享通道实测15。这个界不包含无信用/无数据/无限外存等待。
- read-error/write-error场景均观察到 **1项真实status3完成**，不回滚已写内容；已分配槽继续排空，其他S正常完成。读错误场景重新LOAD后才计算矩阵。错误场景表格吞吐不用于容量比较。
- 坏ID及重复响应触发RTL protocol_error；协调清空DMA/两域FIFO/外存队列后，重新LOAD/计算/STORE通过。没有宣称单端复位可接收旧响应。
- 6类非法输入为零长度、本地范围溢出、外存未对齐、40bit地址溢出、零信用、非法通道数；每例在RTL端拒绝并保持错误完成，不发内存流量。上边界定向场景实际LOAD/STORE最后一个本地字及40bit最高合法外存字。
- `full-16k-descriptor`实际搬运每S1024字。三种初态×两个随机种子均通过。
- 外存模型故意损坏payload，夹具对真实S写请求与独立数据源的核对拒绝，不将该失败计作正向通过。独立审计再篡改信用、吞吐和矩阵覆盖，三个内存负例均被拒绝。

GB/s按成功描述符有效字节×3/ticks计算，包括阶段启动等待、CDC、S确认、完成背压与排空。第二阶段通常是STORE；mixed-directions一半LOAD/一半STORE，不能将该行理解为纯STORE。M计算不计入搬运带宽；read-error行展示重新LOAD的成功阶段；write-error行不把失败描述符的部分写入计为有效字节。没有报告整模型tokens/s或读写混合峰值。

## 综合与证据

完整DMA核心按2组×2S及4组×4S、8槽、4通道分别综合。Yosys0.63、`synth -noabc`、通用门级输出，不是Liberty工艺映射；不是网表LEC或最终门级功能仿真。所有最终RTL运行源为`{verified['source_commit']}`；原S/feeder/M源与main `4b1df2c7`逐字节相同。

首次97176在Werror下拒绝夹具4处歧义排版，原始失败保留；修正后的97177完成36场景及两配置综合；97178增加边界/非法配置检查后完成38场景及全部检查。所有历史任务自然结束，没有取消其他作业或覆盖原文件。最终目录`/public/home/yuzelu/PingyangHuang/issue181-hbm-rtl03-20261104`。

最终实收 **50份原文件、18,322,759字节**。完整Yosys日志以原字节保存在reception.tar.gz及服务器，Git中保留压缩原件、索引和轻量日志，避免展开大日志；独立检查器直接核验压缩包内的每个原文件。较大的通用网表和可执行文件留服务器，SHA和大小在索引。未把压缩日志当作可复现物理数据库。

- [RTL合同](../HBM_GROUP_DMA.md)、[运行器](../../project/experiments/hbm_feed/run_rtl.py)、[逐例原始结果](../../work/huangpingyang04-lgtm/181/evidence/rtl-release/result/results.json)。
- [独立审计](../../work/huangpingyang04-lgtm/181/RTL_INDEPENDENT_CHECK.json)、[源/输出索引](../../work/huangpingyang04-lgtm/181/evidence/rtl-release/reception-index.json)、[Slurm终态](../../work/huangpingyang04-lgtm/181/evidence/rtl-release/scheduler.txt)。

```powershell
python -X utf8 -B project/experiments/hbm_feed/check_rtl_evidence.py
python -X utf8 -B project/experiments/hbm_feed/summarize_rtl.py
python -X utf8 -B scripts/check_project.py
# 全新服务器实验（先提交输入）：
python -X utf8 -B project/experiments/hbm_feed/launch.py --rtl --attempt <新名称> --package-dir <新本地目录>
```

## 仍待验证

HBM式时序模型仍是明确假设，未按真实HBM器件/VIP/Ramulator校准。内存接口是本报告定义的带ID原生事务口；完整AXI五通道/位宽适配、商用HBM控制器/PHY、封装、完整模型、并行M阵列、同S计算/搬运并发及P&R/时序/扇出/面积/功耗均未授予通过资格。通用综合规模已经不小，是否满足实际面积和300MHz必须另行工艺映射/物理验证。

规则rayggxia-project-collab1.0.0；负责人huangpingyang04-lgtm；成果更新PR182供独立审查、不自行合并。登记沿用management-hubPR5 pending；无config/board.json及Projects字段工具，看板unverified/同步pending，管理员与审查人待指定。
'''
    out = ROOT / 'docs/experiments/issue-181-hbm-rtl-results.md'
    out.write_bytes(report.encode('utf-8'))
    manifest = dict(input_sha256=hashlib.sha256(data_path.read_bytes()).hexdigest(),
                    generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    report_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
                    source_commit=verified['source_commit'])
    (ROOT / 'work/huangpingyang04-lgtm/181/RTL_REPORT_MANIFEST.json').write_bytes((json.dumps(manifest, indent=2)+'\n').encode())
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
