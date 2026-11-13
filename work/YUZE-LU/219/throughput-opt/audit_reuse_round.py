"""Read saved artifacts, replay without planner, and bind the round evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
from native_pointwise import execute
from native_reuse import verify
from resident_probe import analyse
from resident_replay import replay
from resident_timing import audit
from verify_resident_bindings import verify as verify_recipes
from verify_cover_frontier import verify as verify_schedule


def main():
    p=argparse.ArgumentParser();p.add_argument('runtime',type=Path);a=p.parse_args();root=a.runtime
    def read(f):return json.loads(f.read_text())
    programs=read(root/'actual-boundaries-v2/programs.json')
    fixture_path=Path('work/YUZE-LU/219/throughput-opt/results/resident-boundary-program-terminal-r16/generated/actual-boundary-fixtures.json')
    regions=read(Path('work/YUZE-LU/219/throughput-opt/results/source-closed-pointwise-r14/generated/native-regions.json'))
    graphs=[g for r in regions for g in r['graphs']];cases=0
    for f in read(fixture_path):
        gi=f['region_index'];old=graphs[gi];saved=programs[str(gi)];verify(saved['graph'],old)
        values={(n,i):v for n,i,v in f['inputs']};gold=execute(old,values)
        for b in saved['plans'].values():
            result=replay(saved['graph'] if b.get('value_reuse') else old,b,values);audit(b,b['service_timing'])
            if b.get('value_reuse'):
                if result['logical_native_outputs']!={n['id']:gold[n['output']] for n in old['operations']}:raise ValueError('saved reuse differs')
            elif result['observed_native_outputs']!={n['output']:gold[n['output']] for n in old['operations']}:raise ValueError('saved baseline differs')
            cases+=1
    probe=root/'reuse-rtl-v2';acceptance=read(probe/'acceptance.json');manifest=read(probe/'manifest.json')
    for i,expected in enumerate(acceptance['reports']):
        if analyse(probe,probe/f'simulate-{i}.log',write_summary=False)!=expected:raise ValueError('saved RTL report differs')
    original_probe=Path('D:/Data/电路实验/issue219-runtime-round15/continuation-rtl-r16-v3')
    origin=read(original_probe/'manifest.json')
    for f,v in manifest['sha256'].items():
        if f.startswith('rtl/') and origin['sha256'].get(f)!=v:raise ValueError('DUT RTL changed')
    for c in manifest['cases']:
        values={(n,i):v for n,i,v in c['values']};old=c['original_graph'];g=c['graph'];b=c['plan'];gold=execute(old,values)
        if b.get('value_reuse'):verify(g,old)
        result=replay(g,b,values);audit(b,b['service_timing'])
        if b.get('value_reuse') and result['logical_native_outputs']!={n['id']:gold[n['output']] for n in old['operations']}:
            raise ValueError('saved RTL program source proof differs')
    for f,reason in (('stale.log',b'reused SRAM/backed value changed'),('commit.log',b'original output commit missing')):
        if reason not in (probe/f).read_bytes():raise ValueError('wrong RTL negative')
    cover={}
    for name in ('original_resident','conditional_reuse'):
        base=root/'cover-compare-v1'/name;ir=read(base/'ir.json');summary=read(base/'summary.json')
        if verify_recipes(ir)!=summary['resident_native_audit']:raise ValueError('saved recipe audit differs')
        for strategy,expected in summary['plan_audits'].items():
            if verify_schedule(ir['tasks'],ir['hardware'],ir['resident_actions'],read(base/(strategy+'.json')),18)!=expected:
                raise ValueError('saved graph schedule differs')
        cover[name]=summary['plans'][summary['strongest_greedy']]
    fullbase=Path('work/YUZE-LU/219/throughput-opt/results/resident-full-selected-terminal-r18')
    full=read(fullbase/'generated/report.json');raw=[json.loads(line) for line in (fullbase/'replay.log').read_text().splitlines() if line.startswith('{')]
    if not full['passed'] or raw!=full['samples'] or len(raw)!=3:raise ValueError('full graph output/report differs')
    expected=('bde45c6cdb455fd3db408592766bf4894f327586714010fe74b126b07937af4d',
              '5ee07808b663b54c2739745b93d9403917e6c787363c454f1ba177887ab319d9',
              'e8302da1c912cb1e0230570b7df2c946af9b238fcc00956da3c20181544b1453')
    for sample,digest in zip(raw,expected):
        if (not sample['bit_exact_to_original'] or not sample['top1_equal'] or sample['logits_raw_sha256']!=digest or
            len(sample['resident']['loops'])!=73 or not sample['resident']['passed']):raise ValueError('full selected-loop evidence differs')
    receipt=read(fullbase/'receipt.json')
    for f,entry in receipt['recovered'].items():
        if hashlib.sha256((fullbase/f).read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('terminal SHA differs')
    result={'passed':True,'actual_fixture_replays':cases,'rtl_cases_per_initialization':acceptance['cases_per_initialization'],
        'rtl_saved_program_replays':len(manifest['cases']),'cover':cover,'old_full_integer_samples':3,
        'old_full_selected_loops_per_sample':73,'old_full_report_sha256':hashlib.sha256((fullbase/'generated/report.json').read_bytes()).hexdigest(),
        'scope':'independent saved-source, finite-S numeric, event accounting, frozen RTL and schedule evidence; no planner rerun, no SystemC/system/energy/token/s qualification'}
    match=read(root/'final-source-match.json');tail=read(root/'tail-fix-evidence.json')
    if not match['passed'] or match['checked_saved_programs']!=551 or not tail['passed'] or tail['old_exception']!='lost canonical live output':
        raise ValueError('final-source/tail regression evidence differs')
    result.update(final_source_match=match,tail_fix={'old_exception':tail['old_exception'],'fixed_total_ticks':tail['fixed_total_ticks'],
                  'frozen_source_sha256':tail['frozen_source_sha256']})
    (root/'independent-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
