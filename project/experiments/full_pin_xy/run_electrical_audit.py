"""Read completed immutable RC/STA path reports, never reroute or modify them."""
from pathlib import Path
import datetime,json,sys
from run_exports import ROOT,sha
from summarize_path_electrical import summarize

out=ROOT/'electrical_observations'/sys.argv[1];out.mkdir(parents=True,exist_ok=False)
cases={'act':('r02','fullC-r02'),'gemm':('r01','r01'),'mxu':('r03','grid-r05'),
 'vector':('r04','grid-r05'),'opentpu_aux':('r03','grid-r05'),'llaccel_aux':('r03','grid-r05')}
inputs=[(c,r,p) for c,revs in cases.items() for r,p in zip(revs,['A','C'])]
inputs += [('act','fullC-r01','A_replay'),('act','fullBcohort-r01','B')]
summary=[]
for case,rev,plan in inputs:
    source=ROOT/'trials'/rev/(case+'-'+plan);receipt=json.loads((source/'execution.json').read_text());assert receipt.get('finished_utc')
    p=source/'timing.paths.json';expected=receipt['outputs'][p.name]['sha256'];assert sha(p)==expected
    selected=receipt.get('selected_pin_count')
    if selected is None:
        command=receipt['command'];environment=dict(x.split('=',1) for x in command[command.index('--env')+1].split(','))
        selected=sum(line.startswith('lappend relocations ') for line in Path(environment['PINXY_RELOCATIONS']).read_text().splitlines())
    r=summarize(p);r.update({'case':case,'revision':rev,'plan':plan,'selected_pin_count':selected,
       'source':str(p),'source_sha256':expected,'RC_STA_receipt':str(source/'execution.json')})
    # Independently compare the streaming parser to the standard whole-document
    # parser on the complete real ACT C report before processing giant reports.
    if case=='act' and plan=='C':
        reference=json.loads(p.read_text())['checks'];assert len(reference)==r['reported_checks']
        values=[float(q['capacitance']) for check in reference for q in check.get('source_path',[]) if 'capacitance' in q]
        assert max(values)==r['path_observations']['data']['maximum_observed_capacitance_F']
        r['streaming_crosscheck']='PASS standard JSON count and actual data-path maximum capacitance';del reference,values
    dest=out/(case+'-'+plan+'.json');dest.write_text(json.dumps(r,indent=2)+'\n');summary.append(r)
    print('ACTUAL_PATH_OBSERVATIONS',case,plan,r['reported_checks'],flush=True)
(out/'summary.json').write_text(json.dumps({'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'records':summary,
  'scope':'Native RCX/OpenSTA path observations at inherited independent-block boundaries, not all-net coverage or full system electrical qualification.'},indent=2)+'\n')
