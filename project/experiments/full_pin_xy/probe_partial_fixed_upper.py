"""Native controlled test for partial fixed prewire routing, not a system.

Same measured0.8um x32um M10 conductor, same technology and M11/M12 range.
Compare FIXED vs ROUTED metadata in a private router fixture. Lower geometry
must remain exact; the fixed bridge must actually be necessary after routing.
This is a tool capability test, never a frozen six-block implementation.
"""
from pathlib import Path
import csv,datetime,json,os,re,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from check_access import check,check_rows
DRIVER=Path(__file__).resolve().parent
def run(revision):
    tech=ROOT/'upper_layer_probe/r01/model/research12.tech.lef';m=json.loads((tech.parent/'model.json').read_text());assert m['original_M1_M10_and_via1_via9_layer_blocks_identical'] and sha(tech)==m['files'][tech.name]['sha256']
    out=ROOT/'partial_fixed_upper_probe'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'TINY_PARTIAL_FIXED_NATIVE_ROUTER_CAPABILITY_NOT_SYSTEM_OR_MANUFACTURING_QUALIFICATION','source_SHA':{str(tech):sha(tech)},'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],'full_qualification':False,'cases':{},'actual_M10_conductor':'Original construction policy0.8um width/32um length; fixture positions are not actual six-block positions','original_leaf_M5_M6_pins':'NOT_CHANGED_OR_MODELED_BY_THIS_PROBE'}
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
    (out/'fixture.v').write_text('module hpy_partial_fixed(input src, output pad_a,pad_b,dst); assign pad_a=src; assign pad_b=src; assign dst=src; endmodule\n')
    try:
        for status in ['FIXED','ROUTED']:
            folder=out/status;folder.mkdir();lines=[helper,'read_lef '+tcl(tech),'read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef','read_verilog '+tcl(out/'fixture.v'),'link_design hpy_partial_fixed','initialize_floorplan -die_area {0 0 64 64} -core_area {1 1 63 63} -site FreePDK45_38x28_10R_NP_162NW_34O','make_tracks','set b [ord::get_db_block];set tech [ord::get_db_tech]']
            for pin,x,y in [('src',9.695,16.070),('pad_a',25.695,16.070),('pad_b',25.695,48.070),('dst',41.695,48.070)]:lines.append('place_pin -pin_name '+pin+' -layer metal10 -location {'+str(x)+' '+str(y)+'} -pin_size {.8 .8}')
            lines+=['set n [[$b findBTerm src] getNet];if {[llength [$n getBTerms]]!=4 || [llength [$b getNets]]!=1} {error "Native four-terminal net aliasing failed"}',
              'set m10 [$tech findLayer metal10];if {[$m10 getWidth]!=1600} {error "Actual M10 width is not0.8um"};set w [odb::dbWire_create $n];set e [odb::dbWireEncoder];$e begin $w;$e newPath $m10 '+status+';$e addPoint 51390 32140;$e addPoint 51390 96140;$e end',
              'set ::env(PINXY_ACCESS_OUT) '+tcl(folder/'before.tsv'),'source '+tcl(DRIVER/'export_access.tcl'),
              'write_db '+tcl(folder/'before_NOT_SYSTEM.odb'),'write_def '+tcl(folder/'before.def'),
              'set_routing_layers -signal metal11-metal12 -clock metal11-metal12',
              'if {![stage native_global {global_route -guide_file '+tcl(folder/'route.guide')+' -congestion_report_file '+tcl(folder/'congestion.rpt')+'}]} {close $stages;exit 1}',
              'if {![stage native_upper_route {detailed_route -output_drc '+tcl(folder/'route.drc')+' -verbose 1}]} {close $stages;exit 1}',
              'write_db '+tcl(folder/'routed_NOT_SYSTEM.odb'),'write_def '+tcl(folder/'routed.def'),
              'set ::env(PINXY_ACCESS_OUT) '+tcl(folder/'after.tsv'),'source '+tcl(DRIVER/'export_access.tcl'),
              'stage independent_native_DRC {drt::check_drc -output_file '+tcl(folder/'independent.drc')+'}','close $stages']
            script=folder/'run.tcl';script.write_text('\n'.join(lines)+'\n');rc=execute(common,script,folder/'native.log','PINXY_OUTPUT='+str(folder)+',PINXY_ACCESS_ALL=1',threads=4)
            result={'native_returncode':rc,'source_status':status,'complete_function_RC_STA':'NOT_EXECUTED_CAPABILITY_ONLY'}
            if (folder/'before.tsv').exists():result['before']=check(folder/'before.tsv',True)
            if (folder/'after.tsv').exists():
                rows=list(csv.DictReader((folder/'after.tsv').open(),delimiter='\t'));before=list(csv.DictReader((folder/'before.tsv').open(),delimiter='\t'));result['after']=check_rows([dict(r) for r in rows],True)
                pool=[r for r in before if r['kind']=='WIRE' and r['layer']=='metal10'];assert len(pool)==1
                key=lambda r:tuple(int(r[k]) for k in ['x0','y0','x1','y1']);p=key(pool[0]);original=[key(r) for r in before if r['layer']=='metal10']
                result['all_after_M10_material_contained_in_original_pool_or_original_pads']=all(any(a<=x0 and b<=y0 and x1<=c and y1<=d for a,b,c,d in original) for r in rows if r['layer']=='metal10' for x0,y0,x1,y1 in [key(r)])
                result['original_M10_pool_rectangle_retained']=any(r['kind']=='WIRE' and r['layer']=='metal10' and key(r)==p for r in rows)
                removed=[dict(r) for r in rows if not(r['kind']=='WIRE' and r['layer']=='metal10' and key(r)==p)]
                result['all4_terminals_without_M10_pool_connected']=check_rows(removed,True)['pass'];result['pool_bridge_actually_necessary']=result['after']['pass'] and not result['all4_terminals_without_M10_pool_connected']
                if (folder/'independent.drc').exists():result['native_DRC_count']=len(re.findall(r'^violation type:',(folder/'independent.drc').read_text(),re.M))
            rec['cases'][status]=result
        rec['ROUTED_metadata_candidate_physically_usable_in_this_fixture_only']=all(rec['cases']['ROUTED'].get(k) for k in ['all_after_M10_material_contained_in_original_pool_or_original_pads','original_M10_pool_rectangle_retained','pool_bridge_actually_necessary']) and rec['cases']['ROUTED'].get('native_DRC_count')==0
        rec['native_FIXED_status_restore_in_real_base']='NOT_IMPLEMENTED_BY_THIS_FIXTURE; necessary before any final system claim'
    except Exception:rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    rec['all_sources_unchanged']=all(sha(Path(p))==v for p,v in rec['source_SHA'].items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={str(p.relative_to(out)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.rglob('*') if p.is_file()};(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');return int(bool(rec.get('actual_failure')) or not rec.get('ROUTED_metadata_candidate_physically_usable_in_this_fixture_only'))
if __name__=='__main__':sys.exit(run(sys.argv[1]))
