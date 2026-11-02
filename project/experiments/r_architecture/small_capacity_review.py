"""Reproduce the small-R decision from archived actual RTL/SystemC runs.

No new arithmetic simulation, physical qualification, or energy calibration.
"""
from pathlib import Path
import csv, hashlib, json, math

ROOT = Path(__file__).resolve().parents[3]
D = ROOT / 'work/YUZE-LU/157'


def read_csv(name):
    with (D / name).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    inputs = ['SYNTHESIS_RESULTS.csv', 'SYSTEMC_RESULTS.csv',
              'HIGH_FANOUT_TOP20.csv', 'ARCHITECTURES.md',
              'inputs/block_v1_r.sv']
    # The frozen source file inventory is separately recorded in BASELINE.json.
    inputs = [n for n in inputs if (D / n).exists()]
    synth = {r['candidate']: r for r in read_csv('SYNTHESIS_RESULTS.csv')}
    high = read_csv('HIGH_FANOUT_TOP20.csv')
    rows = read_csv('SYSTEMC_RESULTS.csv')
    workloads = ['W0-m0-n2048-t128.bin', 'W1-m0-l24-t128.bin',
                 'W2-m0-n8192-t16.bin', 'Qwen35-GDN-key128-value8-t16.bin',
                 'W0-m1-n2048-t128.bin']
    selected = []
    for cap in [256, 512, 1024, 2048]:
        label = 'B' + str(cap)
        for work in workloads:
            matches = [r for r in rows if r['candidate'] == label and
                       r['workload'] == work and r['policy'] == 'cache' and
                       r['latency'] == '40' and r['bandwidth'] == '16']
            assert len(matches) == 1, (label, work, len(matches))
            r = matches[0]
            assert r['status'] == 'PASS'
            # Confirm CSV metrics directly against the archived execution JSON,
            # not merely against another generated summary.
            n = 27 if work.startswith('Qwen') else 15
            path = D / f'evidence/extended/attempt{n:03d}/results/RESULTS.json'
            raw = json.loads(path.read_bytes())
            exact = [x for x in raw if x['architecture'] == 1 and
                     x['capacity'] == cap and x['workload'] == work and
                     x['policy'] == 'cache' and x['latency'] == 40 and
                     x['bandwidth'] == 16]
            assert len(exact) == 1
            x = exact[0]
            for field in ['cycles', 'S_allocated_peak', 'state_tile_visits',
                          'DRAM_read_bytes', 'DRAM_write_bytes']:
                assert int(r[field]) == x[field], (label, work, field)
            assert x['exit'] == 0 and x['status'] == 'PASS'
            assert sum(x['stages'].values()) == int(r['cycles_including_setup'])
            state = sum(x['traffic'].get(k, 0) for k in
                        ['state_read', 'state_write', 'intermediate_read', 'intermediate_write'])
            selected.append(dict(candidate=label,workload=work,capacity_s32_per_bank=cap,
                two_bank_state_bytes=cap*8,cycles=x['cycles'],
                cycles_including_setup=int(r['cycles_including_setup']),
                S_reserved_bytes=x['S_allocated_peak'],S_free_bytes=16384-x['S_allocated_peak'],
                DDR_total_bytes=x['DRAM_read_bytes']+x['DRAM_write_bytes'],
                DDR_state_and_intermediate_bytes=state,tile_pass_visits=x['state_tile_visits'],
                S_port_cycles=x['stages'].get('S_write_read',0),
                R_load_read_cycles=x['stages'].get('R_load',0)+x['stages'].get('R_read',0),
                DDR_latency_cycles=x['stages'].get('DRAM_latency',0),
                source=str(path.relative_to(ROOT)),input_sha256=x['input_sha256'],
                binary_sha256=x.get('binary_sha256','not recorded in this raw result; see attempt build receipts')))
    p = D / 'SMALL_CAPACITY_RESULTS.csv'
    with p.open('w', encoding='utf-8', newline='') as stream:
        writer=csv.DictWriter(stream,list(selected[0]));writer.writeheader();writer.writerows(selected)
    def table(headers, data):
        return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join(['---']*len(headers))+'|']+
                         ['|'+'|'.join(map(str,row))+'|' for row in data])
    capacity=[]
    for cap in [256,512,1024,2048]:
        s=synth['B'+str(cap)]; hh=[h for h in high if h['candidate']=='B'+str(cap)]
        capacity.append([cap,cap*8,cap//8,round(float(s['area_um2'])),
                         round(float(s['system_component_sum_um2'])/1e6,4),
                         max(int(h['loads']) for h in hh),
                         round(float(s['all_nonclock_signal_pin_C_ff'])/1000,1)])
    metrics=[]
    for row in selected:
        metrics.append([row['candidate'],row['workload'],row['cycles'],row['S_reserved_bytes'],
                        row['DDR_total_bytes'],row['tile_pass_visits'],row['R_load_read_cycles']])
    text='''# 小容量 R：容量、换页与物理代价专项复核

Issue #157 / PR #160。按新指令重点比较256/512/1024，2048仅作容量对照。复用已完成的实际RTL/SystemC、映射与物理证据；本报告不授予新R生产资格，不替换主线R。复现：`python project/experiments/r_architecture/small_capacity_review.py`。

## 容量单位与真实模型对应

一个条目是一个S32状态标量，不是一个head、token或完整向量。每个候选有old/shadow两个物理bank，因此256/512/1024/2048条目对应2/4/8/16KiB状态有效载荷，另有系数、流水、统计与控制。8lane下分别容纳32/64/128/256行。

冻结算子图给出Qwen3.5每层状态32×128×128：单版本2MiB、双版本4MiB；现有研究配置24递推层共双版本96MiB。128key×8value的一个strip为1024条目、双版本8KiB，每层512个strip。Falcon图给出32×128channel×256state：单版本4MiB、双版本8MiB；一个256state×8channel strip为2048条目，每层512个strip。Falcon层数在本专项不另行假定。上述均按S32合同折算，不是模型原始权重大小。

Qwen配置已有真实维度、合成整数单strip的实际运行；Falcon完整层只做尺寸/映射推导，另从已有W0-m1-n2048-t128抽取四容量SSM合成整数证据，对应256state×8channel的条目规模，不能称为真实Falcon参数执行。256/512/1024在Qwen strip内需4/2/1块，在Falcon strip内需8/4/2块，2048对照分别1/1块。GDN全局dot/error必须跨块保持，全部结果写确认后才提交，不能把每块独立提交冒充同一任务。

## 电路收益与瓶颈转移

'''
    text+=table(['每bank条目','双bank字节','8lane行数','R映射面积µm²','共同组件和mm²','最大直接扇出','全非时钟pin-C pF'],capacity)
    text+='''

四种容量最大扇出均落在rd_index[2]外部动态读地址，说明剩余主要瓶颈包含调试/状态读出选择；两拍同步读的后续版本已完成独立功能和匹配周期验证，见[同步读报告](SYNC_READ_REVISION.md)；本表仍是原异步读映射，不把输入pin扇出降低当成总选择网络消失。最大扇出统计整个映射图，而非只看role。小容量同时降低总pin-C和高扇出网络规模，但仍有译码/广播，不能只缩数组就认为问题解决。所有映射面积均非最终布局面积；共同组件已含16KiB标准单元S、M/E与控制/router原型，不重复加状态bank。

## 同一已执行任务的完整代价

默认串行策略、DDR latency40cycle/16B每cycle、S单窄口及共享宽读。周期窗口含载入/运算/搬运/提交，初始化另列CSV；表中S保留含1536B scratch/元数据预算，不代表所有寄存器/真实DMA实现成本已物理闭合。

'''
    text+=table(['候选','任务','周期','S保留B','DDR总B','分块pass访问','R装入/读出周期'],metrics)
    text+='''

关键区别：W0的256/512/1024均可把其余双版本放在S，DDR总量相同。256的S保留15872B，只剩512B；慢并非因为状态全都去DDR，而是重复R/S交换、串行端口和控制。W1每token轮转24层，各容量DDR总量也相同，但1024装下完整strip，省去大量片内交换。W2超过片内缓存时，四个容量DDR状态/中间值量相同，增加容量主要减少命令与burst等待，周期收益已很小。

所有DDR经一个128bit staging packet及S写/读，两bank仍为1RW，未假定四个独立外部窄口；响应背压及至多一个在途写均显式建模。现有BW16→64无收益不能解释成真实DRAM无限快，而是当前128bit片内口/串行调度先限速。直接DDR→R旁路、DMA与计算重叠均未实现，不能把本策略当理论下限。

## 推荐与下一步物理选择

1. **1024作为小容量架构主候选**：恰好容纳Qwen128×8 strip，W1与B2048同周期、共同组件和更小；真实维度16token条带也与2048同周期。这些同周期结果限于原异步读合同；同步读版本的额外周期另见同步读报告。它仍不能驻留完整head/层；不能把条带测试外推完整LLM性能。
2. **256作为面积下界/极小状态专用候选**：仅当工作集合≤256、或系统确实可接受换页成本时使用。对当前1024条带不建议作为默认；历史大floorplan物理虽DRC0但setup/hold失败；本轮紧凑实现及修复终态见续办报告，不能把历史失败或中间通过覆盖最终证据。
3. **512保留折中点**：相对256减少命令/交换等待但仍装不下1024条带，尚无明确普适优势；没有必要立即追加完整P&R。
4. **2048是Falcon strip或2048连续驻留任务的对照**：在W0明显快于所有小容量，在W1/Qwen strip没有额外周期收益。选择依任务生存期，而非单看本体面积。

历史B256大floorplan实测：总线长9026143µm、router DRC0，setup/hold WNS为−0.351331/−0.0563912ns，失败；3000µm大floorplan利用率约3.9%，不能代表紧凑小R。续办已实施B256/1000µm和B1024/1600µm两项代表紧凑物理，保留原300MHz及IO约束。前者M10角落冲突、内部修复目标过强及后续hold违规均保留；原A0/A1超时不算通过，A1独立恢复最终检查后仍未通过。当前候选、同步读及强时钟树迭代的实际终态见[续办报告](CONTINUATION_20261102.md)。实际作业、源commit与归档SHA见[物理运行索引](SMALL_CAPACITY_ACTIVE_RUNS.json)，终态指标见[物理报告](PHYSICAL_RESULTS.md)。运行中不授予资格；不同die尺寸不能宣称同floorplan的纯容量对照。512不追加完整物理，避免扩成无界搜索。

无R窄M/E的精确S32分解需多次发射；新增宽整数C-N必须显式计73074.190µm²及finish/控制成本。不能将其视为现有M/E免费能力，也不将周期域Pareto转换为时序尚失败候选的同频硅片性能。未校准能量继续不报焦耳。

## 可复核证据边界

附CSV的20条记录逐条与attempt015/027原始RESULTS.json核对输入SHA、可用的二进制SHA（旧015结果未逐条记录，需查构建回执）、周期、DDR、S峰值、pass访问以及阶段和；未重新运行算术或宣称新数值验证。脚本记录输入摘要；现有完整证明与2096记录回归继续由check_final.py独立核验。所有状态/流量为有效载荷，未包括完整网络包头、PHY或集成微程序全部成本。
'''
    (D/'SMALL_CAPACITY_REVIEW.md').write_text(text,encoding='utf-8')
    evidence={str((D/n).relative_to(ROOT)):hashlib.sha256((D/n).read_bytes()).hexdigest() for n in inputs}
    for n in [15,27]:
        p=D/f'evidence/extended/attempt{n:03d}/results/RESULTS.json'
        evidence[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    (D/'SMALL_CAPACITY_VALIDATION.json').write_text(json.dumps(dict(passed=True,
        selected_actual_runs_verified=len(selected),inputs_sha256=evidence,
        no_new_physical_qualification=True,no_new_simulation=True),indent=2)+'\n',encoding='utf-8')
    print(f'PASS:{len(selected)} actual archived runs, capacity and traffic accounting; no physical qualification')


if __name__ == '__main__':
    main()
