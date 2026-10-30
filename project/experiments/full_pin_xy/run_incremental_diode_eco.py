"""Add 22 source-proven missing real diodes, retaining the routed 636-diode ECO.

Incremental GRT plus normal DRT is not a claim that only 22 nets change.
Every original endpoint/master/pose, interface and PG contract is checked.
"""
from pathlib import Path
from collections import defaultdict
import csv,datetime,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from verify_mapped_eco import export_graph,load
from cell_semantics import contract,groups
from check_access import check

DRIVER=Path(__file__).resolve().parent


def run(revision):
    mapping=ROOT/'post_diode_netmap/cap-r01';mp=mapping/'execution.json';m=json.loads(mp.read_text())
    assert m['native_returncode']==0 and m['all_sources_unchanged']
    summary=m['correlation_summary'];assert summary['marker_count']==37 and summary['mapped_nets_already_with_real_diode']==[]
    nets=summary['mapped_nets_without_existing_real_diode'];assert len(nets)==len(set(nets))==22
    marker_file=mapping/'marker_net_correlations.json';assert sha(marker_file)==m['files'][marker_file.name]['sha256']
    markers=json.loads(marker_file.read_text());assert all(x['net_mapping']=='UNIQUE_EXACT_POLYGON_CONDUCTOR_CORRELATION' for x in markers)
    source=ROOT/'diode_cap_eco/r01/gemm-C';p=source/'execution.json';prior=json.loads(p.read_text())
    assert sha(p)==m['source_SHA'][str(p)] and prior['all_original_signal_terminal_and_port_graph_equal_with_exact_two_proven_sizes']
    assert prior['fresh_DRC_count']==0 and prior['whole_signal_geometry']['pass'] and prior['retained_real_diode_count']==636
    odb=source/'routed.odb';guide=source/'route.guide';graph=source/'resized.tsv.gz'
    for q in [odb,guide,graph]:assert sha(q)==prior['files'][q.name]['sha256']
    trial=ROOT/'trials/access-r03/gemm-C/execution.json';original=json.loads(trial.read_text());sdc=Path(original['source_sdc'])
    reservations=[Path(k) for k in original['input_sha256'] if k.endswith('/access_reservations.tcl')];assert len(reservations)==1
    for q in [sdc,reservations[0]]:assert sha(q)==original['input_sha256'][str(q)]
    out=ROOT/'antenna_incremental_eco'/revision/'gemm-C';out.mkdir(parents=True,exist_ok=False)
    inputs={str(q):sha(q) for q in [mp,marker_file,p,odb,guide,graph,trial,sdc,reservations[0]]}
    rec={'scope':'22_MATCHED_REAL_ANTENNA_DIODE_LOADS_INCREMENTAL_GRT_NOT_PURE_XY',
      'source_SHA':inputs,'full_qualification':False,'previous_real_diodes':636,'requested_additional_real_diodes':22,
      'no_full_signal_clock_wire_rip_requested':True,'DRT_not_claimed_22_net_only':True,
      'original_allowed_layers':'signal M2-M10; clock M4-M10','original_SDC_unchanged':True,
      'native_returncodes':{},'RTL_formal_equivalence':'NOT_EXECUTED','complete_GDS_rules':'NOT_YET_EXECUTED',
      'scheduler_job':os.environ['SLURM_JOB_ID'],'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
      'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    def save():(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    for q in original['libs']:
        if Path(q).is_file():common+=['--bind',q+':'+q+':ro']
    try:
        raw=subprocess.check_output(common+[IMAGE,'cat','/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'])
        text=raw.decode();model=contract(text,'ANTENNA_X1')
        assert model['state']==[] and model['pins']==[('A',[('direction','input')])]
        cell=dict(groups(text,'cell'))['ANTENNA_X1'];body=dict(groups(cell,'pin'))['A']
        cap=float(re.search(r'\bcapacitance\s*:\s*([\d.eE+-]+)',body).group(1));assert cap>0
        unit=re.search(r'capacitive_load_unit\s*\(\s*([^,]+)\s*,\s*([^\)]+)\)',text);assert unit
        assert float(unit[1])==1 and unit[2].strip()=='ff'
        rec['actual_single_input_no_output_or_state_contract']=model
        rec['actual_input_capacitance_ff']=cap
        rec['actual_typical_Liberty_SHA256']=__import__('hashlib').sha256(raw).hexdigest()
        centers=defaultdict(list)
        for marker in markers:
            box=marker['source_polygon_bbox_um'];centers[marker['native_net']].append(((box[0]+box[2])*1000,(box[1]+box[3])*1000))
        assert set(centers)==set(nets)
        request=out/'requested_nets.tcl'
        request.write_text('set requested_nets {\n'+''.join('  {'+tcl(n)+' %.6f %.6f}\n'%(sum(x for x,y in centers[n])/len(centers[n]),sum(y for x,y in centers[n])/len(centers[n])) for n in sorted(nets))+'}\n')
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        script=out/'run.tcl';script.write_text(helper+'\n'+'\n'.join('read_liberty '+tcl(q) for q in original['libs'])+'\n'+(DRIVER/'antenna_diode_access.tcl').read_text())
        env=','.join(['PINXY_OUTPUT='+str(out),'PINXY_ACCESS_ALL=1','PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),
          'PINXY_DIODE_SOURCE='+str(odb),'PINXY_DIODE_SDC='+str(sdc),'PINXY_DIODE_GUIDES='+str(guide),
          'PINXY_DIODE_PREFIX=PINXY_ANT_R2_','PINXY_DIODE_COUNT=22','PINXY_DIODE_REQUESTS='+str(request),
          'PINXY_DIODE_RESERVATIONS='+str(reservations[0]),'PINXY_DIODE_EXPORT_ACCESS='+str(DRIVER/'export_access.tcl')])
        rec['native_returncodes']['implementation']=execute(common,script,out/'native.log',env);save()
        if (out/'routed.odb').exists():
            fresh=out/'fresh.tcl';fresh.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal10 -clock metal4-metal10\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
            rec['native_returncodes']['fresh_DRC']=execute(common,fresh,out/'independent.log',threads=1)
            if rec['native_returncodes']['fresh_DRC']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
            rec['native_returncodes']['relative_graph_export']=export_graph(common,out/'routed.odb',out,'extra_diodes')
            assert rec['native_returncodes']['relative_graph_export']==0
            a,at,ap=load(graph);b,bt,bp=load(out/'extra_diodes.tsv.gz');added=set(b)-set(a)
            assert len(added)==22 and set(a)<=set(b) and all(a[n]==b[n] for n in a) and ap==bp
            assert at=={k:v for k,v in bt.items() if k[0] in a}
            target=[]
            for name in added:
                assert b[name]==('ANTENNA_X1','CORE_ANTENNACELL') and name.startswith('PINXY_ANT_R2_')
                terms={pin:v for (inst,pin),v in bt.items() if inst==name}
                assert set(terms)=={'A'} and terms['A'][0]=='INPUT';target.append(terms['A'][1])
            assert len(set(target))==22 and set(target)==set(nets)
            assert sum(x[0]=='ANTENNA_X1' for x in b.values())==658
            rec['all_original_instances_and_signal_graph_preserved_with_only_22_real_diode_loads']=True
            rec['actual_total_real_diodes']=658
        if (out/'whole_access.tsv.gz').exists():rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        rec['pin_PG_die_unchanged']={k:(out/('after.'+k+'.tsv')).exists() and sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['pins','pdn','die']}
        rec['all_prior_functional_and_636_diode_poses_and_terminals_unchanged']=(out/'after.original.tsv').exists() and sha(out/'before.original.tsv')==sha(out/'after.original.tsv')
        if (out/'diode_placed.tsv').exists():
            with (out/'diode_placed.tsv').open() as f:placed=list(csv.DictReader(f,delimiter='\t'))
            assert len(placed)==22 and {q['net'] for q in placed}==set(nets)
            rec['separate_additional_diode_cost']={'added_real_ANTENNA_X1':22,'master_bbox_area_um2':sum(int(q['width_dbu'])*int(q['height_dbu'])/4e6 for q in placed),'added_input_capacitance_each_ff':cap,'not_block_area_saving':True}
        for kind in ['setup','hold']:
            q=out/(kind+'.txt')
            if q.exists():rec[kind+'_ns']=float(re.search(r'worst slack (?:min|max)\s+([-\d.]+)',q.read_text())[1])
        if (out/'checks.txt').exists():rec['literal_VIOLATED_markers_not_complete_failure_count']=(out/'checks.txt').read_text().count('(VIOLATED)')
    except Exception:rec['actual_failure']=traceback.format_exc()
    if (out/'stages.tsv').exists():
        with (out/'stages.tsv').open() as f:rec['native_stage_status']={q['stage']:q['status'] for q in csv.DictReader(f,delimiter='\t')}
    rec['all_sources_unchanged']=all(sha(Path(k))==v for k,v in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={q.name:{'bytes':q.stat().st_size,'sha256':sha(q)} for q in out.iterdir() if q.is_file() and q.name!='execution.json'};save()
    passed=('actual_failure' not in rec and rec.get('native_returncodes',{}).get('implementation')==0 and rec.get('fresh_DRC_count')==0
      and rec.get('all_original_instances_and_signal_graph_preserved_with_only_22_real_diode_loads')
      and rec.get('all_prior_functional_and_636_diode_poses_and_terminals_unchanged')
      and all(rec.get('pin_PG_die_unchanged',{}).get(k) for k in ['pins','pdn','die'])
      and rec.get('whole_signal_geometry',{}).get('pass') and rec.get('setup_ns',-1)>=0 and rec.get('hold_ns',-1)>=0
      and rec.get('literal_VIOLATED_markers_not_complete_failure_count')==0 and rec['all_sources_unchanged']
      and all(rec.get('native_stage_status',{}).get(k)=='EXECUTED' for k in ['begin_incremental_GRT','actual_diode_insert','diode_legalization','global_route','detailed_route','preserve_original_views','VDD','VSS','whole_signal_geometry','rcx','sta']))
    return 0 if passed else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
