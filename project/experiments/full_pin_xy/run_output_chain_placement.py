"""Evidence-directed existing output-buffer placement ECO, same functional netlist."""
from pathlib import Path
import csv,datetime,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from buffer_graph_contract import identity_buffer
from cell_semantics import groups
from check_access import check

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'checkpoint_route/r01';p=source/'execution.json';proof=json.loads(p.read_text())
    assert proof.get('completed_utc') and proof['native_returncode']==0 and proof['fresh_DRC_count']==0
    assert proof['whole_signal_geometry']['pass'] and proof['source_unchanged']
    odb=source/'routed.odb';assert sha(odb)==proof['files']['routed.odb']['sha256']
    old=json.loads((ROOT/'trials/access-r03/opentpu_aux-C/execution.json').read_text());sdc=Path(old['source_sdc'])
    reservation=[Path(k) for k in old['input_sha256'] if k.endswith('/access_reservations.tcl')];assert len(reservation)==1
    reservation=reservation[0]
    for q in [sdc,reservation]:assert sha(q)==old['input_sha256'][str(q)]
    path_audit=ROOT/'actual_path_audit/r01/opentpu_aux/execution.json';audit=json.loads(path_audit.read_text())
    assert audit['native_returncode']==0 and all(audit['source_worst_slacks_exactly_replayed'].values())
    assert audit['source_SHA'][str(odb)]==sha(odb)
    out=ROOT/'output_chain_placement'/revision/'opentpu_aux-C';out.mkdir(parents=True,exist_ok=False)
    inputs={str(q):sha(q) for q in [p,odb,sdc,reservation,path_audit]}
    record={'scope':'SAME_NETLIST_EXISTING_IDENTITY_BUFFER_PLACEMENT_ECO_NOT_PURE_PIN_XY',
      'new_functional_cells':0,'master_sizing_changes':0,'functional_net_splits':0,
      'source_SHA':inputs,'original_signal_pin_PG_die_and_SDC_to_be_verified':True,
      'original_allowed_layers':'signal M2-M8; clock M4-M8','full_qualification':False,
      'placement_heuristic':'Real private identity-buffer chains; actual port rectangle center and retained upstream driver instance bbox center. Bbox center is a placement proxy, not a fabricated signal-pin coordinate. Preserve original fixed instances.',
      'original_source_setup_hold_failures_retained':True,'RTL_formal_equivalence':'NOT_EXECUTED',
      'complete_GDS_rules':'NOT_EXECUTED','scheduler_job':os.environ['SLURM_JOB_ID'],
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
      'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'native_returncodes':{}}
    def save():
        (out/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
    save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    for path in old['libs']:
        if Path(path).is_file():common+=['--bind',path+':'+path+':ro']
    try:
        lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
        text=subprocess.check_output(common+[IMAGE,'cat',lib]).decode()
        allowed={}
        for name,body in groups(text,'cell'):
            if not re.fullmatch(r'(?:CLKBUF|BUF)_X\d+',name):continue
            ip,op,contract=identity_buffer(text,name);allowed[name]=(ip,op)
        assert allowed
        models=out/'actual_buffer_models.tcl'
        models.write_text('set buffer_models [dict create]\n'+''.join('dict set buffer_models '+tcl(n)+' {'+ip+' '+op+'}\n' for n,(ip,op) in sorted(allowed.items())))
        record['actual_Liberty_identity_buffer_masters']=allowed
        helpers=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        script=out/'run.tcl';script.write_text(helpers+'\n'+'\n'.join('read_liberty '+tcl(path) for path in old['libs'])+'\n'+(DRIVER/'output_chain_placement.tcl').read_text())
        env=','.join(['OMP_NUM_THREADS=4','PINXY_OUTPUT='+str(out),'PINXY_ACCESS_ALL=1','PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),
          'PINXY_CHAIN_SOURCE='+str(odb),'PINXY_CHAIN_SDC='+str(sdc),'PINXY_CHAIN_MODELS='+str(models),
          'PINXY_CHAIN_RESERVATIONS='+str(reservation),'PINXY_CHAIN_EXPORT_ACCESS='+str(DRIVER/'export_access.tcl')])
        record['native_returncodes']['implementation']=execute(common,script,out/'native.log',env);save()
        if (out/'routed.odb').exists():
            fresh=out/'fresh.tcl';fresh.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal8 -clock metal4-metal8\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
            record['native_returncodes']['fresh_DRC']=execute(common,fresh,out/'independent.log',threads=1)
            if record['native_returncodes']['fresh_DRC']==0:record['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        if (out/'whole_access.tsv.gz').exists():record['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        record['original_functional_cell_master_and_connection_contract_unchanged']=(out/'after.connections.tsv').exists() and sha(out/'before.connections.tsv')==sha(out/'after.connections.tsv')
        record['nonselected_original_pose_unchanged']=(out/'after.nonselected.tsv').exists() and sha(out/'before.nonselected.tsv')==sha(out/'after.nonselected.tsv')
        record['pin_PG_die_unchanged']={k:(out/('after.'+k+'.tsv')).exists() and sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['pins','pdn','die']}
        if (out/'output_selection.tsv').exists():
            with (out/'output_selection.tsv').open() as f:choices=list(csv.DictReader(f,delimiter='\t'))
            record['output_port_selection_summary']={'all_output_ports_considered':len(choices),'private_output_chains_selected':sum(r['status']=='PROPOSED_EXISTING_PRIVATE_CHAIN_RELOCATION' for r in choices)}
        if (out/'proposed_existing_buffer_moves.tsv').exists():
            with (out/'proposed_existing_buffer_moves.tsv').open() as f:moves=list(csv.DictReader(f,delimiter='\t'))
            assert len({r['instance'] for r in moves})==len(moves)
            record['selected_existing_buffers']=len(moves)
        for kind in ['setup','hold']:
            q=out/(kind+'.txt')
            if q.exists():
                match=re.search(r'worst slack (?:max|min)\s+([-\d.]+)',q.read_text());assert match
                record[kind+'_ns']=float(match[1])
        if (out/'checks.txt').exists():record['literal_VIOLATED_markers_not_complete_failure_count']=(out/'checks.txt').read_text().count('(VIOLATED)')
        if (out/'stages.tsv').exists():
            with (out/'stages.tsv').open() as f:record['native_stage_status']={r['stage']:r['status'] for r in csv.DictReader(f,delimiter='\t')}
    except Exception as error:
        record['exception']=str(error);(out/'driver_error.txt').write_text(traceback.format_exc())
    record['all_sources_unchanged']=all(sha(Path(k))==v for k,v in inputs.items())
    record['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    record['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'}
    save()
    # A zero command return never conceals failing timing/electrical gates.
    passed=('exception' not in record and record['native_returncodes'].get('implementation')==0
      and record.get('fresh_DRC_count')==0 and record.get('setup_ns',-1)>=0 and record.get('hold_ns',-1)>=0
      and record.get('literal_VIOLATED_markers_not_complete_failure_count')==0 and record['all_sources_unchanged']
      and record.get('whole_signal_geometry',{}).get('pass') and all(record.get('pin_PG_die_unchanged',{}).get(k) for k in ['pins','pdn','die'])
      and record.get('original_functional_cell_master_and_connection_contract_unchanged') and record.get('nonselected_original_pose_unchanged')
      and all(record.get('native_stage_status',{}).get(k)=='EXECUTED' for k in ['legalization','global_route','detailed_route','preserve_contracts','VDD','VSS','whole_signal_geometry','rcx','sta']))
    return 0 if passed else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
