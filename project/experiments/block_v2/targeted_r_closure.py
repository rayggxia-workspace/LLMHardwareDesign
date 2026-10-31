"""Generate and audit a bounded R physical ECO from an immutable RC trace.

This is not final acceptance. Native route/finish, complete LEC and every
independent final physical/functional gate remain mandatory.
"""
import hashlib
import json
import re


def config_bytes(evidence_bytes):
    data=json.loads(evidence_bytes)
    assert data['diagnostic_completed'] and data['source_bytes_unchanged']
    assert data['native_leaf_accepted'] is False
    assert data['actual_design']=='outputs/100/pnr/r'
    assert data['actual_spef']=='outputs/104/diagnostic.spef'
    rows=data['hold_targets']
    assert 1<=len(rows)<=512 and len({x['endpoint'] for x in rows})==len(rows)
    for row in rows:
        assert re.fullmatch(r'\$auto\$ff\.cc:337:slice\$[0-9]+',row['endpoint'])
        assert (row['startpoint'] in ('reset','rsp_ready') or re.fullmatch(r'\$auto\$ff\.cc:337:slice\$[0-9]+',row['startpoint']))
        assert -.030<row['hold_slack_ns']<=.050
        assert row['setup_slack_ns']>=.100
    actual=data['hold_paths'];assert actual
    selected={row['endpoint']:row for row in rows}
    for path in actual:
        assert path['endpoint'] in selected
        chosen=selected[path['endpoint']]
        assert chosen['startpoint']==path['startpoint'] and chosen['hold_slack_ns']<=path['slack_ns']
    resize=data['resize_targets']
    assert len(resize)==10
    for i,row in enumerate(resize):
        assert row['instance']=='wire'+str(592286-i)
        assert row['master']==('BUF_X2' if i==1 else 'BUF_X1')
        assert row['min_slack_ns']>=.300 and row['protected']==0
        assert row['signal_only'] and row['single_fanout']
    lines=['# Generated exclusively from the hash-bound actual-RC evidence.',
           'set evidence_sha '+hashlib.sha256(evidence_bytes).hexdigest(),
           'set targets {']
    lines+=[' {'+row['endpoint']+'}' for row in rows]
    lines+=['}','set resize_targets {']
    lines+=[' {'+row['instance']+' '+row['master']+'}' for row in resize]
    lines+=['}','']
    return '\n'.join(lines).encode()


def prepare(raw,flow,source,sha,full_optimization=False):
    """Retain prior physical repair audits, while applying one additional ECO."""
    import shutil
    from pathlib import Path
    root=Path(__file__).resolve().parents[3]
    evidence=root/'work/YUZE-LU/143/r-input-hold/trace-106/index.json'
    payload=evidence.read_bytes();config=config_bytes(payload)
    data=json.loads(payload)
    for name,digest in data['files'].items():
        assert '/' not in name and '\\' not in name and name not in ('.','..')
        assert sha(evidence.parent/name)==digest
    shutil.copyfile(evidence,raw/'r-targeted-evidence.json')
    (raw/'r-targeted-config.tcl').write_bytes(config)
    script=root/'project/experiments/block_v2/r_targeted_closure.tcl'
    shutil.copyfile(script,raw/'r-targeted-closure.tcl')
    electrical={}
    for label in ('failed-116','trace-119'):
        folder=root/'work/YUZE-LU/143/r-input-hold'/label
        index=json.loads((folder/'index.json').read_text())
        assert index['qualified'] is False
        for name,digest in index['files'].items():assert sha(folder/name)==digest
        electrical[label]=dict(index_sha256=sha(folder/'index.json'),index=index)
    assert electrical['failed-116']['index']['actual_target_buffers']==332
    assert electrical['trace-119']['index']['newly_violating_driver']['master']=='MUX2_X1'
    (raw/'r-targeted-electrical-evidence.json').write_bytes((json.dumps(electrical,indent=2)+'\n').encode())
    prior=json.loads((source/'receipt.json').read_text())
    rel=Path('flow/results/nangate45/bv1_block_v1_r/base')
    files=['r-measured-hold.tcl','r-hold-targets.json','r-electrical-stage.py','r-input-hold-guard.tcl']
    names=['issue143-measured-hold.tsv','issue143-measured-hold-checks.tsv','issue143-measured-before-checks.tsv',
           'issue143-measured-before-electrical.rpt','issue143-measured-after-electrical.rpt',
           'issue143-measured-electrical-stage.json','issue143-input-hold-guard.tsv']
    for relative in [Path(f) for f in files]+[rel/f for f in names]:
        assert sha(source/relative)==prior['outputs'][str(relative)]
        shutil.copyfile(source/relative,raw/relative)
    flow['targeted_r_closure']=dict(script_sha256=sha(script),evidence_sha256=sha(evidence),
        generator_auditor_sha256=sha(Path(__file__)),
        electrical_evidence_sha256=sha(raw/'r-targeted-electrical-evidence.json'),
        electrical_resize=dict(instance='$abc$4429625$auto$blifparse.cc:397:parse_blif$4540226',old_master='MUX2_X1',new_master='MUX2_X2',minimum_hold_headroom_ns=.100),
        config_sha256=sha(raw/'r-targeted-config.tcl'),hold_targets=[r['endpoint'] for r in data['hold_targets']],
        buffers_per_endpoint=4,resize_targets=data['resize_targets'],
        pre_eco_recovery_checkpoints=['issue143-targeted-pre.odb','issue143-targeted-pre.sdc','issue143-targeted-pre.guide'],
        inherited_repair_evidence=dict(source=str(source),receipt_sha256=sha(source/'receipt.json'),
            files={str(f):sha(source/f) for f in [Path(x) for x in files]+[rel/x for x in names]}),
        full_native_optimization=full_optimization,
        native_optional_optimization='SKIP_INCREMENTAL_REPAIR=0,OPT_POST_GRT_WNS=0: repeat native design/timing repair before measured ECO;107 proved rerouting changes estimated timing' if full_optimization else 'SKIP_INCREMENTAL_REPAIR=1,OPT_POST_GRT_WNS=1: retain completed100 optimization; no final checks skipped',
        scope='Ten measured long-wire repeaters to BUF_X4; four local BUF_X1 per measured hold endpoint; exact116 newly-violating MUX2_X1 to equivalent MUX2_X2 with current hold guard. No RTL/FF/clock/SDC change. Strict intermediate electrical/timing and complete final proof/all gates required.')
    return raw/'r-targeted-closure.tcl'


def audit(raw,flow,receipt,sha):
    """Recompute generated configuration and audit every actual ECO row."""
    from pathlib import Path
    root=Path(__file__).resolve().parents[3]
    metadata=flow['targeted_r_closure']
    assert sha(Path(__file__))==metadata['generator_auditor_sha256']
    flag='0' if metadata.get('full_native_optimization') else '1'
    assert flow['actual_variables']['SKIP_INCREMENTAL_REPAIR']==flag and flow['actual_variables']['OPT_POST_GRT_WNS']==flag
    payload=(raw/'r-targeted-evidence.json').read_bytes()
    assert (raw/'r-targeted-config.tcl').read_bytes()==config_bytes(payload)
    names=['r-targeted-evidence.json','r-targeted-config.tcl','r-targeted-closure.tcl']
    for name,key in zip(names,('evidence_sha256','config_sha256','script_sha256')):
        assert sha(raw/name)==metadata[key]==receipt['outputs'][name]
    assert sha(root/'project/experiments/block_v2/r_targeted_closure.tcl')==metadata['script_sha256']
    assert sha(root/'work/YUZE-LU/143/r-input-hold/trace-106/index.json')==metadata['evidence_sha256']
    names.append('r-targeted-electrical-evidence.json')
    assert sha(raw/names[-1])==metadata['electrical_evidence_sha256']==receipt['outputs'][names[-1]]
    electrical=json.loads((raw/names[-1]).read_text())
    for label,entry in electrical.items():
        folder=root/'work/YUZE-LU/143/r-input-hold'/label
        assert sha(folder/'index.json')==entry['index_sha256']
        assert json.loads((folder/'index.json').read_text())==entry['index']
        for name,digest in entry['index']['files'].items():assert sha(folder/name)==digest
    inherited=metadata['inherited_repair_evidence'];prior=Path(inherited['source'])
    assert sha(prior/'receipt.json')==inherited['receipt_sha256']
    old=json.loads((prior/'receipt.json').read_text())
    for name,digest in inherited['files'].items():
        assert sha(prior/name)==sha(raw/name)==digest==old['outputs'][name]==receipt['outputs'][name]
    prefix='flow/results/nangate45/bv1_block_v1_r/base/'
    for name in metadata['pre_eco_recovery_checkpoints']:
        assert sha(raw/prefix/name)==receipt['outputs'][prefix+name]
    files=['issue143-targeted-hold.tsv','issue143-targeted-hold-checks.tsv',
           'issue143-targeted-before-checks.tsv','issue143-targeted-before-electrical.rpt',
           'issue143-targeted-after-electrical.rpt','issue143-targeted-electrical-stage.json',
           'issue143-targeted-hold-timing.rpt']
    for f in files:assert sha(raw/prefix/f)==receipt['outputs'][prefix+f]
    rows=[line.split('\t') for line in (raw/prefix/files[0]).read_text().splitlines()]
    targets=metadata['hold_targets'];count=len(targets)
    assert metadata['buffers_per_endpoint']==4
    assert rows[0]==['scope','targets',str(count),'buffers_per_endpoint','4','evidence_sha256',metadata['evidence_sha256']]
    electrical_rows=[r for r in rows if r[0]=='electrical_resize'];assert len(electrical_rows)==1
    want=metadata['electrical_resize'];row=electrical_rows[0]
    assert row[:4]==['electrical_resize',want['instance'],want['old_master'],want['new_master']]
    assert float(row[4])>=want['minimum_hold_headroom_ns'] and row[5]=='connections_location_protection_preserved'
    resize=[r for r in rows if r[0]=='resize']
    expected=metadata['resize_targets'];assert len(resize)==len(expected)==10
    for row,want in zip(resize,expected):
        assert row[:4]==['resize',want['instance'],want['master'],'BUF_X4']
        assert float(row[4])>=.300 and row[5]=='connections_location_protection_preserved'
    endpoints=[r for r in rows if r[0]=='endpoint'];buffers=[r for r in rows if r[0]=='buffer'];verified=[r for r in rows if r[0]=='verified']
    assert len(rows)==2+10+6*count and len(endpoints)==len(verified)==count and len(buffers)==4*count
    assert [r[2] for r in endpoints]==targets and [r[1] for r in endpoints]==[str(i) for i in range(count)]
    assert all(r[3] in ('DFF_X1','DFF_X2') and float(r[5])>=.100 for r in endpoints)
    assert [(r[1],r[2],r[3],r[4]) for r in buffers]==[(str(i),str(j),'issue143_r_closure_%d_%d'%(i,j),'BUF_X1') for i in range(count) for j in range(4)]
    assert verified==[['verified',str(i),'CK_Q_PG_preserved','other_fanout_preserved','protection_restored'] for i in range(count)]
    from measured_electrical_stage import check_files
    fresh=check_files(raw/prefix/files[3],raw/prefix/files[4],raw/prefix/files[2],raw/prefix/files[1])
    assert fresh==json.loads((raw/prefix/files[5]).read_text()) and fresh['native_leaf_accepted'] is False
    for i in range(count):files.append('issue143-targeted-setup-%d.rpt'%i)
    for row in expected:files.append('issue143-targeted-repeater-'+row['instance']+'.rpt')
    files.append('issue143-targeted-electrical-mux-min.rpt')
    for name in files:assert sha(raw/prefix/name)==receipt['outputs'][prefix+name]
    return names,files
