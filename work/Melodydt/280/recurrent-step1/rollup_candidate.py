"""Candidate-specific replacement of the state-operation proxy, conditional on its format."""
from pathlib import Path
from hashlib import sha256
import json,math
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
selected=sys.argv[1:]
assert len(selected)<=1 and all(x in ('qwen35','falcon-wide') for x in selected)
sys.path.insert(0,str(HERE.parent))
from seven_model_arithmetic_estimate import calibrations
_,_,multiply_cost,calibration_sources=calibrations()
basepath=HERE/'baseline-200mhz-v3.json'
base=json.loads(basepath.read_bytes())
rows=[]
sources={basepath.relative_to(ROOT).as_posix():sha256(basepath.read_bytes()).hexdigest()}
graph_audit_path=HERE/'signed-graph-audit.json'
graph_audit=json.loads(graph_audit_path.read_bytes())
assert len(graph_audit)==2 and all(row['passed'] for row in graph_audit)
sources[graph_audit_path.relative_to(ROOT).as_posix()]=sha256(graph_audit_path.read_bytes()).hexdigest()
for helper in (Path(__file__),HERE.parent/'seven_model_arithmetic_estimate.py',HERE.parent/'six_model_tlm_power.py'):
    sources[helper.relative_to(ROOT).as_posix()]=sha256(helper.read_bytes()).hexdigest()
for filename,h in calibration_sources.items():
    sources[(HERE.parent/'arithmetic-calibration-results'/filename).relative_to(ROOT).as_posix()]=h
tbcheck_path=HERE/'calibration-tb-check.json'
tbcheck=json.loads(tbcheck_path.read_bytes())
sources[tbcheck_path.relative_to(ROOT).as_posix()]=sha256(tbcheck_path.read_bytes()).hexdigest()
bindings_path=HERE/'input-bindings.json'
bindings=json.loads(bindings_path.read_bytes())
sources[bindings_path.relative_to(ROOT).as_posix()]=sha256(bindings_path.read_bytes()).hexdigest()
for name,key,term in [('Qwen3.5-4B','qwen35','proxy_gdn_state'),('Falcon-H1-3B','falcon-wide','proxy_mamba_state')]:
    if selected and key not in selected:continue
    path=HERE/(key+'-calibration.json')
    sources[path.relative_to(ROOT).as_posix()]=sha256(path.read_bytes()).hexdigest()
    measured=json.loads(path.read_bytes())
    checkpoint_path=HERE/'results'/key/'power/gate-replay-receipt.json'
    checkpoint=json.loads(checkpoint_path.read_bytes())
    signature={Path(k).name:v for k,v in checkpoint['inputs'].items()}
    for filename in ('commands.txt','segments.json'):
        assert signature[filename]==bindings[key][filename]['server_lf_sha256']
    nested_segments=(json.dumps([sample['segment'] for sample in measured['windows']],indent=2)+'\n').encode()
    assert sha256(nested_segments).hexdigest()==signature['segments.json'],'power phase labels changed from the original command segmentation'
    sources[checkpoint_path.relative_to(ROOT).as_posix()]=sha256(checkpoint_path.read_bytes()).hexdigest()
    graph_row=next(row for row in graph_audit if row['model']==key+'-fast')
    assert graph_row['source_verilog_sha256']==measured['source']['netlist_sha256']
    assert graph_row['sta_graph_sha256']==measured['pin_graph']['graph_sha256']
    assert measured['gate_replay_pass'] and measured['clock_mhz']==200
    assert len(measured['windows'])==len(tbcheck[key]['windows_ps'])==12
    for sample,(ident,a,b,c) in zip(measured['windows'],tbcheck[key]['windows_ps']):
        assert sample['window_ps']==b-a==c-b
    rtl=(HERE/'rtl/block_v1_r_qwen35.sv'
         if key=='qwen35' else HERE/'rtl/block_v1_r_falcon_s32q24.sv')
    rtl_bytes=rtl.read_bytes()
    local_replay_path=HERE/(key+'-cal-receipt.json')
    local_replay=json.loads(local_replay_path.read_bytes())
    sources[local_replay_path.relative_to(ROOT).as_posix()]=sha256(local_replay_path.read_bytes()).hexdigest()
    assert local_replay['candidate_rtl_sha256']==sha256(rtl_bytes).hexdigest()
    assert measured['source']['rtl_sha256']==sha256(rtl_bytes.replace(b'\r\n',b'\n')).hexdigest()
    assert measured['inputs_sha256']['commands.txt']==bindings[key]['commands.txt']['server_lf_sha256']
    assert local_replay['commands_sha256']==bindings[key]['commands.txt']['local_sha256']
    sources[rtl.relative_to(ROOT).as_posix()]=sha256(rtl_bytes).hexdigest()
    model=next(m for m in base['models'] if m['name']==name)
    capture_key='qwen35' if key=='qwen35' else 'falcon'
    original_path=HERE.parent/(capture_key+'_tlm_power_v3_arithmetic.json')
    original=json.loads(original_path.read_bytes())
    assert original['calibration_sha256']==calibration_sources,'v3 arithmetic calibration inputs changed'
    sources[original_path.relative_to(ROOT).as_posix()]=sha256(original_path.read_bytes()).hexdigest()
    report=dict(name=name,rtl_binding=dict(local_sha256=sha256(rtl_bytes).hexdigest(),
                server_lf_sha256=measured['source']['rtl_sha256']),windows={})
    for phase in ('prefill','decode'):
        ref=model['windows'][phase]
        samples=[s for s in measured['windows'] if s['segment']['window']==phase]
        assert len(samples)==4
        calls=sum(x['calls'] for x in original['windows'][phase]['operation_audit'] if term[6:] in x['signature'])
        energy=[]
        duration=[]
        for group in (0,1):
            pair=[x for x in samples if x['segment']['group']==group]
            assert sorted(x['segment']['lane0'] for x in pair)==[0,8]
            energy.append(sum(x['increment_nj'] for x in pair)*1e-9)
            duration.append(sum(x['window_ps'] for x in pair)*1e-12)
        active_s=max(duration)*calls
        assert active_s<=ref['seconds'], 'one shared R exceeds the frozen window time budget'
        idle=[x['power_w']['idle']['total'] for x in samples]
        injection=[0.,0.]
        if key=='falcon-wide':
            # delta*value is supplied by the test driver; retain its scalar energy proxy.
            injection=[calls*16*multiply_cost[0]*.5e-9,calls*16*multiply_cost[1]*2e-9]
        replacement=[calls*min(energy)+ref['seconds']*min(idle)+injection[0],
                     calls*max(energy)+ref['seconds']*max(idle)+injection[1]]
        estimate={}
        for scope in ('on_chip','on_chip_plus_ddr'):
            e=[ref[scope]['window_j'][i]-ref['arithmetic_components_j'][term][i]+replacement[i] for i in (0,1)]
            assert min(e)>0 and e[0]<=e[1]
            estimate[scope]=dict(window_j=e,mean_w=[v/ref['seconds'] for v in e],mj_per_token=[v*1000/ref['tokens'] for v in e])
        report['windows'][phase]=dict(calls=calls,increment_nj_per_16channel_block=[v*1e9 for v in energy],
            shared_r_idle_w=[min(idle),max(idle)],one_r_active_time_s=active_s,
            window_s=ref['seconds'],original_proxy_j=ref['arithmetic_components_j'][term],
            candidate_replacement_j=replacement,baseline={s:ref[s] for s in estimate},candidate=estimate)
        report['windows'][phase]['retained_injection_proxy_j']=injection
    rows.append(report)
result=dict(scope='Candidate hardware scenario; 1 time-multiplexed 8-lane R, complete load/execute/readback activity, observed two-group energy endpoints.',
            baseline_origin='Byte-exact snapshot of output/pdf/seven-model-sync/2026-11-18-r3/200mhz-power-v3.json',
            sample_limits='Both captured prefill groups start from all-zero state; prefill is a cold-state extrapolation, not a whole-prefill uncertainty bound. Decode samples carry actual history; independent-layer and longer real-sequence coverage are absent.',
            precision='Original float TLM and candidate fixed-point differ; end-to-end model accuracy remains unvalidated.',
            exclusion='External injection retains scalar energy proxy; standalone format conversion logic and integration fabric remain uncalibrated.',
            injection_calibration_sha256=calibration_sources,
            input_sha256=sources,models=rows)
output='candidate-rollup'+('-'+selected[0] if selected else '')+'.json'
(HERE/output).write_text(json.dumps(result,indent=2)+'\n')
for r in rows:
    print(r['name'],r['windows']['decode']['candidate'])
