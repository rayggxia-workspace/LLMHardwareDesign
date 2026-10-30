"""Remap one measured failing VECTOR cone, preserving every state boundary.

This is an additional gate implementation experiment, not a pin-XY saving.
Every fanout leaving the cone is exposed and independently checked by ABC CEC.
No source ODB, original state cell, clock tree, port, constraint or layer changes.
A new physical implementation is mandatory before any timing benefit claim.
"""
from pathlib import Path
from collections import defaultdict,Counter
import datetime,gzip,hashlib,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,sha
from verify_mapped_eco import load
from cell_semantics import groups,contract
from verify_ram_sync_wrapper import YOSYS
DRIVER=Path(__file__).resolve().parent
LIB='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'


def run(revision,selection='full_cone'):
    assert selection in ['full_cone','measured_path_slice']
    source=ROOT/'vector_resume/r01';rp=source/'execution.json';s=json.loads(rp.read_text())
    prior=ROOT/'vector_clone_probe/r03';gp=prior/'execution.json';g=json.loads(gp.read_text())
    odb=source/'routed.odb';graph=prior/'source.tsv.gz'
    assert s.get('completed_utc') and s['fresh_DRC_count']==0 and s['whole_signal_geometry']['pass']
    assert s['all_sources_unchanged'] and g.get('completed_utc') and g['all_closed_sources_unchanged']
    assert sha(odb)==s['files'][odb.name]['sha256']==g['source_SHA'][str(odb)]
    assert sha(graph)==g['files'][graph.name]['sha256']
    trial=ROOT/'trials/access-r03/vector-C/execution.json';t=json.loads(trial.read_text());sdc=Path(t['source_sdc'])
    assert sha(sdc)==t['input_sha256'][str(sdc)]
    inputs={str(p):sha(p) for p in [rp,odb,gp,graph,trial,sdc]}
    out=ROOT/'vector_critical_cone_remap'/revision;out.mkdir(parents=True,exist_ok=False)
    q={'scope':'ONE_ACTUAL_FAILING_CONE_GATE_REMAP_AND_RELATIVE_COMBINATIONAL_CEC_NOT_PHYSICAL_OR_RTL_QUALIFICATION',
       'source_SHA':inputs,'source_setup_ns':s['setup_ns'],'source_min_ns':s['hold_ns'],
       'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
       'original_functional_architecture_pipeline_state_ports_clocks_loads_and_layer_sets':'UNCHANGED_SOURCE; replacement pending independent physical verification',
       'cost_scope':'ADDITIONAL_GATE_MAPPING_NOT_PURE_XY; source and all previous failures retained',
       'native_returncodes':{},'selection_profile':selection,'full_qualification':False,'actual_source_ODB_edited':False,
       'physical_route_RC_STA_GDS_full_rules':'NOT_EXECUTED','relative_combinational_equivalence':'NOT_EXECUTED'}
    save=lambda:(out/'execution.json').write_text(json.dumps(q,indent=2)+'\n');save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out),IMAGE]
    def command(label,args,timeout=1800):
        with (out/(label+'.log')).open('x') as f:
            try:q['native_returncodes'][label]=subprocess.call(common+args,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
            except subprocess.TimeoutExpired:
                q['native_returncodes'][label]='TIMEOUT_'+str(timeout)+'s';save();raise
        save();assert q['native_returncodes'][label]==0,label+' native command failed'
    try:
        raw=subprocess.check_output(common+['cat',LIB]);lib=raw.decode();q['actual_Liberty_SHA256']=hashlib.sha256(raw).hexdigest()
        assert q['actual_Liberty_SHA256']=='8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1'
        q['actual_Yosys_version']=subprocess.check_output(common+[YOSYS,'-V']).decode().strip()
        abc=YOSYS.rsplit('/',1)[0]+'/yosys-abc'
        q['actual_tool_SHA256']=subprocess.check_output(common+['sha256sum',YOSYS,abc]).decode().splitlines()
        cells,terms,ports=load(graph);models=dict(groups(lib,'cell'));contracts={};physical_only=set()
        signal_terminal_masters={cells[n][0] for n,pin in terms}
        for master in {c[0] for c in cells.values()}:
            assert master in models,('Missing real cell Liberty',master)
            if not list(groups(models[master],'pin')):
                # Observed r01 input: 5326 actual TAPCELL_X1, no native signal
                # terminals and no Liberty signal pins. Never remove or move
                # these substrate ties; they are outside Boolean cone mapping.
                assert master not in signal_terminal_masters,('Signal terminals missing from Liberty',master)
                physical_only.add(master);contracts[master]={'pins':[],'state':[]}
            else:
                try:contracts[master]=contract('cell ("'+master+'") {'+models[master]+'}',master)
                except AssertionError:raise AssertionError(('Unsupported actual Liberty signal contract',master))
        q['physical_only_no_signal_masters_preserved_outside_cone']={m:sum(v[0]==m for v in cells.values()) for m in physical_only}
        bycell=defaultdict(dict);drivers={};users=defaultdict(set)
        for (inst,pin),(direction,net) in terms.items():
            bycell[inst][pin]=(direction,net)
            if net=='NULL':continue
            if direction=='OUTPUT':
                assert net not in drivers,('Multiple original native drivers',net)
                drivers[net]=inst
            elif direction=='INPUT':users[net].add(inst)
            else:raise AssertionError(('Unsupported inout cone model',inst,pin,direction))
        protected={n for n,(m,kind) in cells.items() if contracts[m]['state']}
        assert len(protected)==4117,('Source state inventory changed',len(protected))
        state=set(protected);protected.update(n for n,(m,kind) in cells.items() if m in physical_only);clock_roots=set()
        for inst in state:
            m=cells[inst][0]
            for kind,args,fields in contracts[m]['state']:
                for key,value in fields:
                    if key in ['clocked_on','clocked_on_also','enable']:
                        for pin in re.findall(r'[A-Za-z_][A-Za-z_0-9]*',value):
                            if pin in bycell[inst]:clock_roots.add(bycell[inst][pin][1])
        pending=list(clock_roots);seen=set()
        while pending:
            net=pending.pop()
            if net in seen or net=='NULL':continue
            seen.add(net);inst=drivers.get(net)
            if inst is None or inst in state:continue
            protected.add(inst)
            pending.extend(n for d,n in bycell[inst].values() if d=='INPUT')
        display={re.sub(r'\\([\[\]])',r'\1',n):n for n in cells};assert len(display)==len(cells)
        endpoint=display['wr_data_r[18]$_DFFE_PN0P_'];assert endpoint in state
        target=bycell[endpoint]['D'][1];selected=set();pending=[target]
        while pending:
            net=pending.pop();inst=drivers.get(net)
            if inst is None or inst in protected or inst in selected:continue
            selected.add(inst);pending.extend(n for d,n in bycell[inst].values() if d=='INPUT' and n!='NULL')
        assert selected and not selected&protected
        if selection=='measured_path_slice':
            audit=ROOT/'actual_path_audit/r01/vector';ap=audit/'execution.json';a=json.loads(ap.read_text());jp=audit/'setup_paths.json'
            assert a['native_returncode']==0 and a['all_sources_unchanged'] and all(a['source_worst_slacks_exactly_replayed'].values())
            assert a['source_SHA'][str(odb)]==sha(odb) and sha(jp)==a['files'][jp.name]['sha256']
            assert sha(jp)=='d4a2682f34e4dc4088090baf9adf2b7d69657512b83e62c739d1370d3dc7a923'
            inputs.update({str(p):sha(p) for p in [ap,jp]})
            path=min(json.loads(jp.read_text())['checks'],key=lambda x:x['slack']);nodes=path['source_path']
            arcs=[display[re.sub(r'\\([\[\]])',r'\1',b['instance'])] for a,b in zip(nodes,nodes[1:]) if a.get('instance') and a['instance']==b.get('instance')]
            assert len(arcs)==141 and set(arcs)<=selected
            full_count=len(selected);selected=set(arcs)-protected
            # One actual fan-in step gives local Boolean restructuring room;
            # all resulting crossing fanouts still become CEC observations.
            for inst in list(selected):
                for d,n in bycell[inst].values():
                    driver=drivers.get(n)
                    if d=='INPUT' and driver is not None and driver not in protected:selected.add(driver)
            q['prior_full_cone_cells']=full_count;q['measured_path_cell_arcs']=141
            q['prior_attempt']='r02 full cone timed out after1800s before mapped netlist/CEC; preserved, no repeated whole-cone run'
            q['scope']='MEASURED_141_ARC_PATH_AND_ONE_HOP_GATE_REMAP_NOT_ALL_VECTOR_TIMING_OR_PHYSICAL_REPAIR'
        topoutputs={n for d,n in ports.values() if d=='OUTPUT'}
        inputnets=set();outputnets=set();wires=set();pin_net={}
        for inst in sorted(selected):
            for pin,(d,net) in bycell[inst].items():
                nn=net if net!='NULL' else 'FLOAT:'+inst+'/'+pin
                assert net!='NULL' or nn not in drivers
                pin_net[inst,pin]=nn;wires.add(nn)
                if d=='INPUT' and drivers.get(net) not in selected:inputnets.add(nn)
                if d=='OUTPUT' and net!='NULL' and (users[net]-selected or net in topoutputs):outputnets.add(nn)
        assert target in outputnets and not inputnets&outputnets
        names={n:'n'+str(i) for i,n in enumerate(sorted(wires))};ci=sorted(inputnets);co=sorted(outputnets)
        assert ci and co
        v=['module hpy_vector_cut(input ['+str(len(ci)-1)+':0] CI, output ['+str(len(co)-1)+':0] CO);']
        v+=['wire '+w+';' for w in names.values()]
        v+=['assign '+names[n]+' = CI['+str(i)+'];' for i,n in enumerate(ci)]
        v+=['assign CO['+str(i)+'] = '+names[n]+';' for i,n in enumerate(co)]
        for index,inst in enumerate(sorted(selected)):
            m=cells[inst][0];assert not contracts[m]['state']
            expected={p for p,fields in contracts[m]['pins']}
            assert set(bycell[inst])==expected,(inst,'Liberty/native terminal mismatch')
            v.append(m+' g'+str(index)+'('+','.join('.'+p+'('+names[pin_net[inst,p]]+')' for p in sorted(bycell[inst]))+');')
        v.append('endmodule');(out/'cut.v').write_text('\n'.join(v)+'\n')
        binding={'source_ODB_SHA256':sha(odb),'measured_endpoint':endpoint+'/D','target_native_net':target,
                 'all_selected_original_instances':sorted(selected),'input_bits_to_original_net':ci,'output_bits_to_original_net':co,
                 'all_output_fanouts_outside_selected_cone_exposed':True,'arbitrary_original_floating_inputs_modeled_as_independent_inputs':sorted(n for n in ci if n.startswith('FLOAT:')),
                 'all_original_state_instances_and_clock_cone_instances_protected':sorted(protected),'source_instance_to_cut_cell':{'g'+str(i):n for i,n in enumerate(sorted(selected))}}
        with gzip.open(str(out/'boundary_binding.json.gz'),'wt') as f:json.dump(binding,f,sort_keys=True)
        q.update(original_selected_cells=len(selected),all_state_cells_protected=len(state),protected_state_and_clock_cone_cells=len(protected),
                 cut_inputs=len(ci),all_cut_outputs=len(co),selected_master_counts=dict(Counter(cells[n][0] for n in selected)),
                 endpoint=endpoint+'/D',target_native_net=target,ABC_target_ps=3000,
                 ABC_delay_target_is_not_extracted_STA_or_original_clock_change=True);save()
        script=['read_liberty -ignore_miss_func '+LIB,'read_verilog cut.v','hierarchy -check -top hpy_vector_cut','flatten','proc','opt','techmap','opt','clean',
                'write_blif reference.blif','abc -liberty '+LIB+' -D 3000','clean','tee -o mapped_stat.json stat -json -liberty '+LIB,
                'write_verilog -noattr remapped.v','write_json remapped.json']
        budget=300 if selection=='measured_path_slice' else 1800
        (out/'map.ys').write_text('\n'.join(script)+'\n');command('mapping',[YOSYS,'-s','map.ys'],budget)
        mapped=json.loads((out/'remapped.json').read_text())['modules']['hpy_vector_cut']
        q['new_cut_cell_types']=dict(Counter(c['type'] for c in mapped['cells'].values()))
        assert all(c['type'] in models and not contracts.get(c['type'],{}).get('state') and not list(groups(models[c['type']],'ff')) and not list(groups(models[c['type']],'latch')) for c in mapped['cells'].values())
        # A fresh process loads functional models for every newly mapped cell;
        # no dependence on modules pruned by the first hierarchy pass.
        (out/'candidate_to_blif.ys').write_text('\n'.join(['read_liberty -ignore_miss_func '+LIB,'read_verilog remapped.v','hierarchy -check -top hpy_vector_cut','flatten','proc','opt','techmap','opt','clean','write_blif implementation.blif'])+'\n')
        command('fresh_candidate_boolean_model',[YOSYS,'-s','candidate_to_blif.ys'],budget)
        command('independent_combinational_CEC',[abc,'-c','cec reference.blif implementation.blif'],budget)
        log=(out/'independent_combinational_CEC.log').read_text()
        assert re.search(r'Networks are equivalent',log) and not re.search(r'NOT EQUIVALENT|not equivalent|Error:',log,re.I)
        q['relative_combinational_equivalence']='PASS_ALL_EXPOSED_CONE_OUTPUTS_FOR_ARBITRARY_STATE_INPUTS; not original RTL proof or installed physical ECO'
        q['mapped_statistics']=json.loads((out/'mapped_stat.json').read_text());save()
    except Exception:q['actual_failure']=traceback.format_exc();traceback.print_exc()
    q['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items());q['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    q['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return int(bool(q.get('actual_failure')) or not q['all_closed_sources_unchanged'] or not q['relative_combinational_equivalence'].startswith('PASS'))
if __name__=='__main__':sys.exit(run(*sys.argv[1:3]))
