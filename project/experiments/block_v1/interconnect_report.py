"""Build a closed finite-experiment report only from verified collected evidence."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def verified(folder,expected):
    index=json.loads((folder/'index.json').read_text())
    for name,row in index['files'].items():
        p=folder/name
        assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],name
    queue=json.loads((folder/'node-queue.json').read_text())
    state=json.loads((folder/'node-queue-state.json').read_text())
    assert state['manifest_sha256']==hashlib.sha256((folder/'node-queue.json').read_bytes()).hexdigest()
    assert set(state['tasks'])=={r['id']for r in queue['tasks']}
    assert all(r['status']=='PASSED'for r in state['tasks'].values())
    assert (folder/'tasks/native-node-queue/exit-code.txt').read_text().strip()=='0'
    rows=[];commits=set()
    for name in sorted(index['files']):
        if not (name.endswith('/interconnect-result.json') or name.endswith('/interconnect-result-summary.json')):continue
        r=json.loads((folder/name).read_text());task=(folder/name).parent
        receipt=json.loads((task/'receipt.json').read_text());assert receipt['passed']
        source=index['files'][name].get('derived_from')
        if source:
            assert source['original_receipt_bound'] and source['sha256']==receipt['outputs']['interconnect-result.json']
        else:assert index['files'][name]['sha256']==receipt['outputs']['interconnect-result.json']
        assert r['passed'] and r['experiment_completed'] and r['native_preservation']['passed']
        assert not r['production_macros_modified'] and not r['geometry_qualified'] and not r['calibrated_12layer_rc_qualified']
        assert len(r['link_paths'])==130 and all(set(p)=={'min','max'}for p in r['link_paths'].values())
        assert r['declared_model_passed']==(not any(r['counts'].values()) and r['min_link_setup_ns']>=0 and r['min_link_hold_ns']>=0)
        timing={line.split()[2]:float(line.split()[3])for line in (task/'timing.rpt').read_text().splitlines()
                if line.startswith('worst slack ')}
        assert set(timing)=={'min','max'}
        assert (timing['max']<0)==(r['counts']['setup_count']>0)
        assert (timing['min']<0)==(r['counts']['hold_count']>0)
        r['global_setup_ns']=timing['max'];r['global_hold_ns']=timing['min']
        commits.add(receipt['source_commit']);rows.append(dict(task=task.name,**r))
    assert len(rows)==expected,(folder,len(rows),expected)
    assert len(commits)==1
    intervals=[]
    for r in state['tasks'].values():
        intervals.extend([(r['started'],1),(r['finished'],-1)])
    active=peak=0
    for _,delta in sorted(intervals):active+=delta;peak=max(peak,active)
    resources=dict(max_parallel_tasks=peak,default_cpus=16,
                   largest_sampled_tree_rss_gib=max(r.get('sampled_peak_tree_rss_bytes',0)for r in state['tasks'].values())/2**30)
    assert peak<=6
    return rows,dict(run_id=index['run_id'],source_commit=commits.pop(),resources=resources)


def table(rows,profile=False):
    result=['|接口|方案|长度µm|RC条件|C/slew违规|setup/hold违规|链路setup ns|链路hold ns|声明条件通过|',
            '|---|---|---:|---|---:|---:|---:|---:|---|']
    for r in rows:
        c=r['counts'];length=r['length_um']
        if profile:length=f"{min(length.values()):.0f}–{max(length.values()):.0f}"
        else:length=f'{length:.0f}'
        result.append(f"|{r['pair'].upper()}|{r['topology']}|{length}|{r['variant']}|{c['capacitance']}/{c['slew']}|{c['setup_count']}/{c['hold_count']}|{r['min_link_setup_ns']:.6f}|{r['min_link_hold_ns']:.6f}|{'是'if r['declared_model_passed']else'否'}|")
    return '\n'.join(result)


def report(root,primary,profile,output):
    a,ma=verified(primary,36);b,mb=verified(profile,12)
    assert (ma['run_id'],mb['run_id'])==('block-v1-20261029-907','block-v1-20261029-908'),'This evidence-specific report does not describe another run'
    section=json.loads((root/'work/YUZE-LU/121/interconnect-study-20261029/cross-section-sanity.json').read_text())
    assert section['passed']
    script=root/'project/experiments/block_v1/interconnect_cross_section.py'
    assert hashlib.sha256(script.read_bytes()).hexdigest()==section['source_sha256']
    assert abs(section['cases']['both-planes-neighbors']['grids'][-1]['capacitance_ff_per_um']-.336771929059818)<1e-14
    passes=Counter(r['pair']for r in a+b if r['declared_model_passed'])
    records={r['pair']:r['native_preservation']['records']['counts']for r in a+b}
    cells=json.loads((primary/'tasks/interconnect-probe/interconnect-probe.json').read_text())['cells']
    lines=['# M/S/T真实生产者—消费者互联有限实验',
           '',f"已完成48项真实宏测量：MT通过{passes['mt']}/24项，TS通过{passes['ts']}/24项。这里的通过仅限声明的电气与时序条件，新增缓冲/中继尚无放置布线资格。生产M/S/T未改动，主线Issue121仍需按其自身验收推进。",
           '', '关键结果：', '',
           '- M→T在568µm/base直连时，电容、slew、hold均无违规，但`right_write_index[6]→T.write_ready→M.rsp_ready→left_cmd_ready`的setup为−0.159452ns。负载合格不能替代跨宏组合时序验收。',
           '- 按实际接点距离，M→T在high直连有98项电容/17项slew违规；8→2端口缓冲清零这些违规，setup仍为−0.243808ns。section下加入8→8→2中继后电气违规清零，setup仍为−0.313493ns。M→T在本轮声明I/O预算下没有整体通过方案。',
           '- T→S最长连接1688µm，high直连有78项电容/64项slew违规，8→2缓冲后全部通过，链路setup+0.377193ns。section下8→2仍有65项电容违规，8→8→2则全部通过，链路setup+0.308616ns。存在可行的电气候选，但有源器件必须预制，尚需实际放置与布线。',
           '', '## 实验回答什么', '',
           '固定M1–M10的积木能否仅通过M11/M12连接，取决于原生输出驱动、双方内部寄生、线的RC及跨宏组合时序。对两个真实接口各130根数据/valid/反向ready线，同时载入两份完整原生门级宏及寄生，比较直连、端口缓冲和端口缓冲加一级中继。',
           '', 'MT：M.rsp_data/valid→T.write_data/valid，T.write_ready→M.rsp_ready；TS：T.read_data/valid→S.din/req，S.ready→T.read_take。T的lease/index及S的写模式/地址由外部控制输入承担。本实验不声称完整协议控制器、系统吞吐或MoE调度已实现。',
           '', 'Nangate45 typical Liberty，300MHz，0.1ns不确定度；未连接外部口保持0.8/0.2ns、BUF_X2和50fF条件。相连接口使用实际生产者和接收者，不再使用虚拟BUF_X2，也不额外叠加2fF接收假负载。共同理想clock根保留双方原CTS图，不授予组合CTS资格。',
           '', '## 原生图与工具控制', '',
           'M/T/S交付功能Verilog省略ODB中原有输入保护器件。实验按已验收physical回执与原清单恢复M142/T190/S143个ANTENNA_X1到实验副本，验证精确字节逆变换和原文件SHA不变；不是删器件或屏蔽警告。真实总线使用向量端口。原生连接、全部ground/coupling C和R的计数及SHA256记录指纹在拼接后反查。',
           '',f'保留的原生记录：MT `{records["mt"]}`；TS `{records["ts"]}`。新增线用π模型；未做新层串扰资格。原生警告、连接着的未标注驱动、错误单位、无约束路径、缺失真实源/接收pin均为硬失败。',
           '', 'run901–905的路径/工具接口/单位前置失败保留。run906小电路工具控制与完整RC准备通过，但真实宏拼接存在省略保护器件与端口命名问题，结果全部拒收；只在核验精确作业身份后取消本侧线93214，主线和他人任务未动。后续只复用已通过RC准备，逐文件SHA及图准备函数AST一致性检查，不复用失败STA。',
           '', 'run907实际四DFF、两个保护器件、向量端口、分离SPEF控制通过；大R/大C实际工具负例产生违规。run908再验证混合BUF_X8/BUF_X2及非等长线控制。弱DFF直连自身的电容/slew违规如实保留，“图消费正例”不等于电路通过。',
           '', '## 固定长度扫描（36项）', '',
           'direct保留原生驱动；endpoints在原驱动之后增加BUF_X4发送、在原接收之前增加BUF_X4接收；relay再加一个BUF_X4中继。局部两段线各8µm，主线中继等分。每段含0.24Ω声明via预算。新增门均是电气候选，没有临时改动生产宏底层。',
           '', 'base：C′0.155390996fF/µm、R′0.015Ω/µm；high：R/C同时1.5×。high是敏感性条件，不是制造工艺角。',
           '',f"下表违规数量覆盖两宏全局，余量栏为130根连接上的最差路径；已逐项与原始全局worst slack交叉检查。48项全局最小hold为{min(r['global_hold_ns']for r in a+b):.9f}ns，不能把链路的较大hold余量当作整宏余量。",'',table(a),
           '', '## 实际接点距离及较强缓冲（12项）', '',
           '用已接收M10内部接点的逐bit坐标，在R0相邻、80µm间隔的四方位中选最小最大Manhattan距离：MT向东916/1348/1548µm，TS向北880/1468/1688µm（最小/中位/最大）。线可以从内部M10接点沿Z上到新增层后跨块走线，没有强制先退到宏边缘。这是距离下界，不证明130根线同时可布通。',
           '', 'endpoints为新增BUF_X8发送、BUF_X2接收；relay再加一个BUF_X8中继。high使用C′0.233086494、R′0.0225；section使用独立理想截面C′0.336771929、相同R′。两者都不是标定工艺或实际三维布线提取。', '',table(b,True),
           '', '## 电容模型的独立核对', '',
           '二维有限体积、2µm宽/厚、0.8µm下间隔、εr3.9，单下连续接地平面/再加两根接地邻线/再加上连续接地平面的C′分别为0.219417/0.249961/0.336772fF/µm。0.2/0.1/0.05µm三档网格，最后两档相差<0.37%；加远外边界相差<0.71%；能量、电荷、残差、平行板解析控制和错误面距负例通过。',
           '', '真实M10/M12是图案而非连续平面，三维交叉线、介质标定、开关相关耦合未建模。因此不能用这些数值宣称真实工艺电容或上界；它们说明原high不能被当作普遍保守上界。',
           '', '## 给主线的边界建议', '',
           '1. 保留混合内部接点。按输出驱动—原生寄生—允许线负载—接收电容定义接口契约，分别规定最大线长/RC、扇出、输入到达预算、输出延迟预算和setup/hold，而不是仅写“有M10 pin”。',
           '2. 长线的负载可以用预制较强发送缓冲、必要的接收隔离和中继分段处理；这些有源器件必须在固定M1–M10底座内预先放置供电、布线验收，或成为固定中继小宏。M11/M12本身不能提供驱动，不能待定制时临时增加FEOL器件。实际位置、接点接入和本地8µm假设仍需验证。',
           '3. M→T的ready跨宏组合路径需要单独处理。在已测0.8ns输入/0.8ns输出预算下，短线也可能不满足300MHz，单纯加缓冲不能保证解决。先用真实外部控制器的寄存器与连线时序分配预算；若不够，再采用能正确处理在途数据的弹性缓冲/信用或局部寄存控制，并验证协议与延迟。不得直接插一只ready寄存器、添加false path或随意放宽约束来宣称通过。',
           '4. 不把全部接口统一堆满缓冲。原生短线已经满足时，加门会增加延迟/功耗；从具体接口结果选择资源。当前仅覆盖单下游、声明环境和代表性链路，不外推广播、多跳、所有宏或完整模型。',
           '', 'BUF_X8/BUF_X2的Liberty单元面积分别为'+str(cells['BUF_X8']['area_um2'])+'/'+str(cells['BUF_X2']['area_um2'])+'µm²。130根线的8→2端口候选共260门、587.86µm²；8→8→2含中继共390门、1037.40µm²。这只计标准单元面积，不是放置留白、供电、pin接入或routing面积。',
           '', '## 来源、资源与复现', '',
           f"run907源commit `{ma['source_commit']}`；run908源commit `{mb['source_commit']}`。完整源/工具/输入/输出SHA在每任务receipt及本地捕获index。",
           '', '93222与93236均自然COMPLETED/0:0，分别34:05和14:07。实验后重新核验M/T/S原始Verilog/SPEF/SDC九文件及三个原physical回执SHA不变，见`work/YUZE-LU/121/interconnect-study-20261029/production-source-readback.json`。',
           '',f"run907资源：`{ma['resources']}`；run908：`{mb['resources']}`。实际峰值并发不超过6个独立16CPU任务，任务即完补位。Issue121共享最多8allocation、pending/unknown计入；run908初次准入无空位时没有提交或挤占其他作业。",
           '', '服务器原始目录：`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261029-{901..908}`。大Verilog/SPEF/ODB及完整全零扇出字典留在授权服务器。派生结果摘要只把该字典替换成计数/字典SHA，原始报告SHA绑定原receipt，其余字段不改。',
           '', '```powershell',
           'python -m unittest discover -s project/experiments/block_v1 -p test_interconnect_spef.py -v',
           'python scripts/check_project.py',
           'python project/experiments/block_v1/interconnect_pin_profiles.py . NEW_PIN_PROFILE.json',
           'python project/experiments/block_v1/interconnect_cross_section.py NEW_SECTION.json',
           'python project/experiments/block_v1/interconnect_collect.py block-v1-20261029-907 NEW_RUN907_CAPTURE',
           'python project/experiments/block_v1/interconnect_collect.py block-v1-20261029-908 NEW_RUN908_CAPTURE',
           'python project/experiments/block_v1/interconnect_report.py . NEW_RUN907_CAPTURE NEW_RUN908_CAPTURE NEW_REPORT.md',
           '```',
           '', '重新测量必须生成新run ID、重新bundle精确Git对象，经原共享dispatch提交。不能修改旧源或重复提交已有关联job的任务。此报告不更新主线Issue完成状态、不授予制造/完整P&R/共同CTS资格。','']
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(passed=True,measurements=48,declared_model_passes=dict(passes),runs=[ma,mb])))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    for name in ('root','primary','profile','output'):p.add_argument(name,type=Path)
    a=p.parse_args();report(a.root,a.primary,a.profile,a.output)
