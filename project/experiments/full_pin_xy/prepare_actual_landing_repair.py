"""One diagnosed GEMM/MXU M10 landing repair, screened against actual geometry."""
from pathlib import Path
import csv,gzip,hashlib,json,re,sys
from run_exports import ROOT,sha
from run_escape_landing import run


def prepare(revision,case='gemm'):
    assert case in ['gemm','mxu']
    source=ROOT/'escape_fixtures'/('gemm-r02/gemm-C' if case=='gemm' else 'mxu-r01/mxu-C')
    old=json.loads((source/'execution.json').read_text());expected=1 if case=='gemm' else 2
    assert old.get('completed_utc') and old['native_route_returncode']==0 and old['independent_DRC_count']==expected
    drc=(source/'independent.drc').read_text()
    pair='net:gemm_a_rdata[128] net:gemm_a_rdata[129]' if case=='gemm' else 'net:act_data[197] net:act_data[213]'
    assert pair in drc and 'on Layer metal10' in drc
    if case=='mxu':assert 'net:act_data[12]' in drc and 'on Layer metal6' in drc
    net='gemm_a_rdata[128]' if case=='gemm' else 'act_data[197]';obstacles=[];terminals=[]
    with gzip.open(source/'whole_access.tsv.gz','rt') as f:
        for q in csv.DictReader(f,delimiter='\t'):
            if q['net']==net and q['kind'] in ['ITERM','BTERM']:terminals.append(q)
            if q['net']!=net and q['layer']=='metal10':obstacles.append([int(q[k])/2000 for k in ['x0','y0','x1','y1']])
    original=next(q for q in terminals if q['kind']=='BTERM');term=next(q for q in terminals if q['kind']=='ITERM')
    assert original['layer']=='metal10' and term['layer'] in ['metal5','metal6']
    names=['whole_access.tsv.gz','parent_M10_PG.tsv','u_macro-pg-access-obstructions.tsv']
    for name in names[1:]:
        with (source/name).open() as f:
            for q in csv.DictReader(f,delimiter='\t'):
                if name=='parent_M10_PG.tsv':keys=['x0','y0','x1','y1']
                else:
                    if q['layer']!='metal10':continue
                    keys=['xmin_dbu','ymin_dbu','xmax_dbu','ymax_dbu']
                obstacles.append([int(q[k])/2000 for k in keys])
    bounds=re.search(r'-die_area \{0 0 ([\d.]+) ([\d.]+)\}',(source/'setup.tcl').read_text());assert bounds
    die_w,die_h=map(float,bounds.groups())
    endpoint=[(int(term[k+'0'])+int(term[k+'1']))/4000 for k in ['x','y']];candidates=[]
    for i in range(-20,21):
        for j in range(-20,21):
            x=.095+(round((endpoint[0]-.095)/3.2)+i)*3.2;y=.07+(round((endpoint[1]-.07)/3.2)+j)*3.2
            b=[x-.4,y-.4,x+.4,y+.4]
            if min(b)<10 or b[2]>die_w-10 or b[3]>die_h-10:continue
            if not any(b[0]-1.5<q[2] and b[2]+1.5>q[0] and b[1]-1.5<q[3] and b[3]+1.5>q[1] for q in obstacles):
                candidates.append((abs(x-endpoint[0])+abs(y-endpoint[1]),x,y))
    assert candidates,'No actual-metal screened proposed landing'
    _,x,y=min(candidates);input_set=case+'-actual-landing-'+revision;out=ROOT/'inputs'/input_set;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'PROPOSED_NEW_PARENT_M10_XY_NOT_LEAF_PIN_CHANGE','case':case,'source_fixture':str(source),
      'expected_source_native_DRC_count':expected,'other_source_errors_preserved_not_waived':case=='mxu',
      'net':net,'original_leaf_layer':term['layer'],'leaf_parent_xy_um':endpoint,
      'old_parent_xy_um':[(int(original[k+'0'])+int(original[k+'1']))/4000 for k in ['x','y']],
      'new_parent_xy_um':[round(x,6),round(y,6)],'parent_layer':'metal10','parent_size_um':[.8,.8],
      'M10_only_static_guard_um':1.5,'source_die_um':[0,0,die_w,die_h],
      'source_setup_SHA':sha(source/'setup.tcl'),'guard_source':'Actual M10 maximum PRL spacing; not imposed on original M5/M6 pins',
      'screened':'Actual other-net M10 wires/vias/terminals, fixed parent PG and macro OBS; reroute/DRC still required',
      'source_files_uncompressed_SHA':{},'source_files_SHA':{n:sha(source/n) for n in names},'full_qualification':False}
    for n in names:
        raw=gzip.decompress((source/n).read_bytes()) if n.endswith('.gz') else (source/n).read_bytes()
        rec['source_files_uncompressed_SHA'][n if n.endswith('.gz') else n+'.gz']=hashlib.sha256(raw).hexdigest()
    (out/'landing_delta.json').write_text(json.dumps(rec,indent=2)+'\n')
    return run(input_set,revision)


if __name__=='__main__':sys.exit(prepare(*sys.argv[1:3]))
