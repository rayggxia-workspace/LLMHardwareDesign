"""Verify received artifacts and produce a compact, reproducible comparison."""
import hashlib
import argparse
import json
import math
from pathlib import Path
import sys
import tarfile

parser=argparse.ArgumentParser()
parser.add_argument('run',nargs='?',choices=('run35','run36','run37'),default='run35')
parser.add_argument('--runs-root',type=Path,default=Path(__file__).resolve().parent)
parser.add_argument('--repo',type=Path)
ARGS=parser.parse_args()
ROOT=ARGS.runs_root.resolve()
REPO=ARGS.repo.resolve() if ARGS.repo else ROOT.parent/'242/r-load-bounds/repo'
RUN=ROOT/'run35'
RECEIPTS=RUN/'receipts'
OUT=REPO/'work/Melodydt/247/optimization-sweep'
SOURCE='e2f91b346f57e872610b0e416290901f5d5e666e'
NAMES=('base','vector8','vector16','nexp8','m16','feed2','ddr25p6','ddr34p2',
       'pool48','pool96','write16','m16_feed2','vector16_nexp8','compute_bundle')
WORK=(('decode512','queued_pipe_w8'),('decode512','queued_pipe_w16'),
      ('decode2048','queued_pipe_w8'),('prefill2','queued_pipe_w8'))
LABELS=dict(base='当前条件基线',vector8='U向量8路',vector16='U向量16路',nexp8='NExp 8路',m16='M的K并行8→16',
            feed2='A64B＋B128B适配',ddr25p6='DDR 25.6GB/s',ddr34p2='DDR 34.2GB/s',pool48='共享48KiB',
            pool96='共享96KiB',write16='M写回16B修正对照',m16_feed2='M16＋A/B扩宽',
            vector16_nexp8='向量16＋NExp8',compute_bundle='M16＋供数＋向量16＋NExp8')
if ARGS.run=='run36':
    RUN=ROOT/'run36';RECEIPTS=RUN/'receipts';OUT=OUT/'run36'
    SOURCE='d9afc95a9b649b096c8a7930d99d56d065d78047'
    NAMES=('base','s16_n4','s16_n8','vector16_s16_n4','read128','m16_feed2_read128','balanced')
    LABELS.update(s16_n4='S16桥接＋NExp4路',s16_n8='S16桥接＋NExp8路',vector16_s16_n4='向量16＋S16桥接N4',
                  read128='M本地取数128B',m16_feed2_read128='M16＋供数＋本地取数128B',balanced='上述M组合＋向量16＋S16桥接N4')
elif ARGS.run=='run37':
    RUN=ROOT/'run37';RECEIPTS=RUN/'receipts';OUT=OUT/'run37'
    SOURCE='f1700f031d629e5af33ad8b36ff9523a6393d90b'
    NAMES=('base','vector8_s16_n4','vector8_s16_n4_bridge8')
    LABELS.update(vector8_s16_n4='向量8＋S16桥接N4',vector8_s16_n4_bridge8='向量8＋S16桥接N4，桥接8拍')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if not RECEIPTS.exists():
        RECEIPTS.mkdir()
        with tarfile.open(RUN/'receipts.tar') as archive:
            for member in archive.getmembers():
                target=(RECEIPTS/member.name).resolve()
                if not member.isfile() or not target.is_relative_to(RECEIPTS.resolve()):
                    raise ValueError('unsafe receipt member '+member.name)
                target.parent.mkdir(parents=True,exist_ok=True)
                with archive.extractfile(member) as source:
                    target.write_bytes(source.read())
    collection=json.loads((RECEIPTS/'collection.json').read_bytes())
    assert collection['collection_succeeded'] and collection['source_commit']==SOURCE
    for name,item in collection['files'].items():
        assert sha(RECEIPTS/name)==item['sha256'],name
    manifest=json.loads((RUN/'inputs.json').read_bytes())
    assert (RUN/'inputs.json').read_bytes()==(RECEIPTS/'inputs.json').read_bytes()
    assert sha(RUN/'payload.tar')==manifest['payload_sha256']
    with tarfile.open(RUN/'payload.tar') as archive:
        for field,prefix in (('code_sha256','source/'),('input_sha256','')):
            for name,digest in manifest[field].items():
                assert hashlib.sha256(archive.extractfile(prefix+name).read()).hexdigest()==digest,name
    result=json.loads((RECEIPTS/'results/result.json').read_bytes())
    assert result['passed'] and result['baseline_phase_passed'] and len(result['cases'])==len(NAMES)*8
    assert result['source_commit']==SOURCE and result['native_full_model_tokens_per_second'] is None
    prior=json.loads((ROOT/'run25/receipts/results/result.json').read_bytes())
    rows={};full_controls=0;negative_count=0
    for item in result['cases']:
        name=item['optimization']; row=item['result']; m=row['optimization_sweep']
        key=(name,item['workload'],item['profile'],item['dual_ports'])
        assert key not in rows and name in NAMES
        rows[key]=item
        historical=[x for x in prior['cases'] if all(x[k]==item[k] for k in
                    ('workload','profile','variant','dual_ports','shared_pool_KiB'))]
        assert len(historical)==1
        reference=historical[0]['result']
        for field in ('read_bus_bytes','write_bus_bytes','logical_read_bytes','logical_write_bytes','dma_descriptors',
                      'M_commands','M_tiles','KV_state_write_bytes','cache_hits','cache_misses','dirty_evictions','dead_lines_discarded'):
            assert row[field]==reference[field],(key,field)
        assert reference['M_work_ticks']-row['M_work_ticks']==m['compute_old']-m['compute_new']
        assert reference['adapter_work_ticks']-row['adapter_work_ticks']==m['adapt_old']-m['adapt_new']
        assert reference['vector_work_ticks']-row['vector_work_ticks']==m['vector_old']-m['vector_new']+m['nexp_old']-m['nexp_new']
        if 'nexp_S16_bridge' in m:
            assert m['M_read_new']<=m['M_read_old']
            if m['nexp_S16_bridge']:
                assert m['bridge_values']==reference['iteration_study']['fallback_values']
                assert m['bridge_cycles']==m['bridge_values']//8*m.get('bridge_cost_per8',1)
            else:
                assert m['bridge_values']==m['bridge_cycles']==0
        assert math.isclose(row['tokens_per_second']*row['seconds'],row['tokens'],rel_tol=1e-10)
        assert abs(row['seconds']*300e6-row['ticks'])<1.1
        pool=row['shared_pool_study']
        assert pool['live_epoch']==pool['live_workers']==0
        assert pool['peak_bytes']<=item['shared_pool_KiB']*1024 and pool['fill_peak_descriptors']<=2
        for p in pool['P']:
            assert p['fifo_peak']<=4 and not p['active'] and p['read_bytes']==p['consumed_bytes']
        clean=dict(row);clean.pop('optimization_sweep')
        if name in ('base','pool48','pool96'):
            assert clean==reference,(key,'exact reference mismatch');full_controls+=1
        logfile=next(p for p in (RECEIPTS/'results').glob('*.log') if sha(p)==item['log_sha256'])
        actual=[json.loads(x[7:]) for x in logfile.read_text().splitlines() if x.startswith('RESULT ')]
        assert actual==[row],key
        assert set(item['negative_checks'])=={'read_bus_bytes','M_commands','M_work_ticks','vector_work_ticks','tokens_per_second'}
        negative_count+=len(item['negative_checks'])
    assert set(rows)=={(n,w,p,d) for n in NAMES for w,p in WORK for d in (False,True)}
    comparisons=[]
    for name in NAMES:
        for w,p in WORK:
            for dual in (False,True):
                item=rows[name,w,p,dual]; r=item['result']; b=rows['base',w,p,dual]['result']
                comparisons.append(dict(optimization=name,label=LABELS[name],workload=w,profile=p,dual_ports=dual,
                     tokens_per_second=r['tokens_per_second'],baseline=b['tokens_per_second'],
                     speed_gain_percent=(r['tokens_per_second']/b['tokens_per_second']-1)*100,
                     seconds=r['seconds'],spans_ticks=r['spans_ticks'],
                     M_work_ticks=r['M_work_ticks'],vector_work_ticks=r['vector_work_ticks'],
                     adapter_work_ticks=r['adapter_work_ticks'],intervention_ledger=r['optimization_sweep']))
    best=max(comparisons,key=lambda x:x['tokens_per_second'])
    summary=dict(passed=True,source_commit=SOURCE,run=RUN.name,job={'run35':102040,'run36':102041,'run37':102043}[RUN.name],scenario_count=len(result['cases']),
                 complete_historical_controls=full_controls,negative_result_checks=negative_count,
                 numeric=result['numeric'],highest=best,comparisons=comparisons,
                 native_full_model_tokens_per_second=None,physical_clock_qualified=False,
                 result_sha256=sha(RECEIPTS/'results/result.json'),receipts_sha256=sha(RUN/'receipts.tar'),
                 verified_received_files=len(collection['files']),source_files=len(manifest['code_sha256']),
                 input_files=len(manifest['input_sha256']),versions=result['versions'])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
    # Full raw events/binaries remain on the authorized server; compact JSON
    # here describes exact retained locations and SHA, never an encoded upload.
    for name in ('inputs.json','sacct.txt','tools.sha256','output-files.sha256','source-files.sha256','input-files.sha256'):
        (OUT/name).write_bytes((RECEIPTS/name).read_bytes())
    (OUT/'result-summary.json').write_text(json.dumps({k:v for k,v in result.items() if k not in ('cases','output_sha256','generation','numeric')},indent=2)+'\n',encoding='utf8')
    (OUT/'README.md').write_text('# 优化方向条件评估证据\n\nIssue247 / PR243，Melodydt。\n'
        f'analysis.json包含全部{len(result["cases"])}项派生比较；原始结果、逐例日志、数值事件及二进制保存在授权服务器{RUN.name}，索引见output-files.sha256。\n'
        '本地已回收文件逐SHA核验，原始事件也保留本地receipts；仓库轻量索引不等于原始全包上传。\n'
        '这些是旧S32/K256/S96模型条件值，不是原生RTL整图token/s；未新增RTL或物理验收。\n',encoding='utf8')
    table=[]
    for dual in (False,True):
        table+=['## '+('idealdual条件' if dual else 'shared条件'),'','| 方案 | W8 decode512 | W16 decode512 | W8 decode2048 | W8 prefill2 |','|---|---:|---:|---:|---:|']
        for name in NAMES:
            vals=[rows[name,w,p,dual]['result']['tokens_per_second'] for w,p in WORK]
            table.append('| '+LABELS[name]+' | '+' | '.join(f'{v:.6f}' for v in vals)+' |')
        table.append('')
    (OUT/'tables.md').write_text('\n'.join(table),encoding='utf8')
    print(json.dumps(dict(passed=True,highest=best,controls=full_controls,files=len(collection['files']),summary=str(OUT/'analysis.json'))))


if __name__=='__main__':
    main()
