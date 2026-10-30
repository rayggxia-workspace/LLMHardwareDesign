"""Costed actual ANTENNA_X1 insertion/routing, retaining all failed original gates."""
from pathlib import Path
from collections import defaultdict
import csv,datetime,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from cell_semantics import groups
from check_access import check

DRIVER=Path(__file__).resolve().parent


def run(revision):
    mapping=ROOT/'antenna_netmap/r02';mp=json.loads((mapping/'execution.json').read_text())
    assert mp['native_returncode']==0 and mp['all_sources_unchanged']
    for name in ['marker_net_correlations.json','unique_correlated_native_nets.json','correlation_summary.json']:
        assert sha(mapping/name)==mp['files'][name]['sha256']
    nets=json.loads((mapping/'unique_correlated_native_nets.json').read_text());assert len(nets)==len(set(nets))==636
    markers=json.loads((mapping/'marker_net_correlations.json').read_text());assert len(markers)==1460
    source=ROOT/'eco_views/r02/gemm-C';vp=json.loads((source/'execution.json').read_text());odb=source/'clean.odb'
    eco=ROOT/'leaf_eco/r03/gemm-C';ep=json.loads((eco/'execution.json').read_text())
    assert vp['source_receipt_sha256']==sha(eco/'execution.json') and sha(odb)==vp['source_geometry_sha256']==ep['files']['routed.odb']['sha256']
    assert ep['fresh_DRC_count']==0 and ep['whole_signal_geometry']['pass']
    trial=ROOT/'trials/access-r03/gemm-C';old=json.loads((trial/'execution.json').read_text());sdc=Path(old['source_sdc'])
    reservation=[Path(k) for k in old['input_sha256'] if k.endswith('/access_reservations.tcl')];assert len(reservation)==1
    reservation=reservation[0]
    for p in [sdc,reservation]:assert sha(p)==old['input_sha256'][str(p)]
    out=ROOT/'antenna_diode_eco'/revision/'gemm-C';out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [mapping/'execution.json',mapping/'marker_net_correlations.json',mapping/'unique_correlated_native_nets.json',mapping/'correlation_summary.json',source/'execution.json',odb,eco/'execution.json',trial/'execution.json',sdc,reservation]}
    rec={'scope':'COSTED_REAL_ANTENNA_DIODE_ECO_NOT_PURE_XY_OR_QUALIFIED_BASE',
      'source_SHA':inputs,'full_qualification':False,'original_antenna_findings':1460,'actual_correlated_native_nets':636,
      'native_returncodes':{},'original_antenna_rules_unchanged':True,'no_fake_gate_or_diffusion_area':True,
      'original_SDC_and_allowed_layers_preserved':True,'allowed_layers':'signal M2-M10; clock M4-M10',
      'design_RTL_formal_equivalence':'NOT_EXECUTED','complete_GDS_rules':'NOT_YET_EXECUTED',
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    def save():
        (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    for path in old['libs']:
        if Path(path).is_file():common+=['--bind',path+':'+path+':ro']
    try:
        libs=[]
        for path in old['libs']:
            raw=subprocess.check_output(common+[IMAGE,'cat',path]).decode()
            bodies=[body for name,body in groups(raw,'cell') if name=='ANTENNA_X1']
            if not bodies:continue
            assert len(bodies)==1
            pins=list(groups(bodies[0],'pin'));assert len(pins)==1 and pins[0][0]=='A'
            body=pins[0][1]
            assert re.search(r'\bdirection\s*:\s*input\s*;',body) and not re.search(r'\bfunction\s*:',body)
            assert not list(groups(bodies[0],'ff')) and not list(groups(bodies[0],'latch'))
            cap=float(re.search(r'\bcapacitance\s*:\s*([\d.eE+-]+)',body).group(1));assert cap>0
            unit=re.search(r'capacitive_load_unit\s*\(\s*([^,]+)\s*,\s*([^\)]+)\)',raw);assert unit
            libs.append({'liberty':path,'actual_input_capacitance':cap,'capacitive_load_unit':[unit.group(1).strip(),unit.group(2).strip()],
              'single_input_only_no_output_function_or_state':True})
        assert len(libs)==1;rec['actual_diode_Liberty_contract']=libs[0];save()
        # Recorded marker bbox only chooses among real native receivers. It is
        # not substituted for the previously proven actual polygon net mapping.
        centers=defaultdict(list)
        for marker in markers:
            native=marker['native_net'];assert native in nets
            box=marker['source_polygon_bbox_um'];centers[native].append(((box[0]+box[2])*1000,(box[1]+box[3])*1000))
        assert set(centers)==set(nets)
        requests=out/'requested_nets.tcl'
        requests.write_text('set requested_nets {\n'+''.join('  {'+tcl(n)+' %.6f %.6f}\n'%(sum(x for x,y in centers[n])/len(centers[n]),sum(y for x,y in centers[n])/len(centers[n])) for n in sorted(nets))+'}\n')
        helpers=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        script=out/'run.tcl'
        script.write_text(helpers+'\n'+'\n'.join('read_liberty '+tcl(p) for p in old['libs'])+'\n'+(DRIVER/'antenna_diode_access.tcl').read_text())
        env=','.join(['OMP_NUM_THREADS=4','PINXY_OUTPUT='+str(out),'PINXY_ACCESS_ALL=1','PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),
          'PINXY_DIODE_SOURCE='+str(odb),'PINXY_DIODE_SDC='+str(sdc),'PINXY_DIODE_REQUESTS='+str(requests),
          'PINXY_DIODE_RESERVATIONS='+str(reservation),'PINXY_DIODE_EXPORT_ACCESS='+str(DRIVER/'export_access.tcl')])
        rec['native_returncodes']['implementation']=execute(common,script,out/'native.log',env);save()
        if (out/'routed.odb').exists():
            fresh=out/'fresh.tcl';fresh.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal10 -clock metal4-metal10\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
            rec['native_returncodes']['fresh_DRC']=execute(common,fresh,out/'independent.log',threads=1)
            if rec['native_returncodes']['fresh_DRC']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        if (out/'whole_access.tsv.gz').exists():rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        rec['unchanged_geometry']={k:(out/('after.'+k+'.tsv')).exists() and sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['pins','pdn','die']}
        rec['original_functional_instances_pose_and_terminal_contract_unchanged']=(out/'after.original.tsv').exists() and sha(out/'before.original.tsv')==sha(out/'after.original.tsv')
        if (out/'diode_placed.tsv').exists():
            with (out/'diode_placed.tsv').open() as f:diodes=list(csv.DictReader(f,delimiter='\t'))
            assert len(diodes)==636 and {d['net'] for d in diodes}==set(nets)
            rec['separate_diode_cost']={'inserted_real_ANTENNA_X1':len(diodes),
              'master_bbox_area_um2':sum(int(d['width_dbu'])*int(d['height_dbu'])/4e6 for d in diodes),
              'added_input_capacitance_each':libs[0]['actual_input_capacitance'],'unit':libs[0]['capacitive_load_unit'],
              'not_block_area_saving':True}
    except Exception as error:
        rec['exception']=str(error);(out/'driver_error.txt').write_text(traceback.format_exc())
    rec['all_sources_unchanged']=all(sha(Path(k))==v for k,v in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'}
    save()
    return 0 if 'exception' not in rec and rec['native_returncodes'].get('implementation')==0 else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
