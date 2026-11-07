"""Read-only native qualification on immutable MC final ODB/SPEF/GDS."""
import argparse,hashlib,json,os,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;COMMON=HERE.parent/'block_v1';COMPACT=HERE.parent/'compact_local_s'
sys.path.insert(0,str(COMMON));sys.path.insert(0,str(COMPACT))
from native_annotation import inspect as annotation_check
from native_passive_endpoint import audit as endpoint_check
from clock_checks import audit as clock_check

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--full-drc',action='store_true');a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);work=a.candidate.resolve();results=work/'flow/results/nangate45/mother_control_64/base';files={k:results/('6_final.'+k) for k in ('odb','v','def','sdc','spef','gds')};digests={k:sha(v) for k,v in files.items()}
 platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45');std=platform/'lib/NangateOpenCellLibrary_typical.lib';bank=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib');assert sha(bank)=='47f8de1c22d27beb51982c73ab745e1f3f2b5a7819e53bcb6da73980ce077189'
 env=dict(os.environ);env.update(OMP_NUM_THREADS=os.environ.get('SLURM_CPUS_PER_TASK','4'),BV1_ODB=str(files['odb']),BV1_SDC=str(files['sdc']),BV1_SPEF=str(files['spef']))
 def run(argv,log):
  with (out/log).open('w') as f:r=subprocess.run(list(map(str,argv)),cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT)
  if r.returncode:raise RuntimeError(f'{log}: exit {r.returncode}')
 def tcl(n,text):
  path=out/(n+'.tcl');path.write_text(text);run(['openroad','-no_init','-exit',path],n+'.log')
 sta=(COMMON/'native_sta.tcl').read_text().replace('set clock_ports [get_ports clk]','set clock_ports [get_ports clk_i]').replace('source [file join [file dirname [info script]] native_annotation.tcl]',f'source {{{COMMON}/native_annotation.tcl}}')
 tcl('sta',f'read_liberty {{{bank}}}\n'+sta+(COMPACT/'clock_checks.tcl').read_text())
 tcl('physical',f'read_liberty {{{bank}}}\n'+(COMMON/'native_physical.tcl').read_text()+'\ncheck_placement -verbose\n')
 tcl('route-drc',f'read_db {{{files["odb"]}}}\ndrt::check_drc_cmd native-drc.rpt 0 0 0 0 mother_native_drc\n')
 physical={r[0]:r[1:] for r in (x.split('\t') for x in (out/'physical-summary.tsv').read_text().splitlines())}
 passive={pin:dict(master=master,type=kind,direction=direction,net=net,pin=pin.rsplit('/',1)[1]) for pin,master,kind,direction,net in (x.split('\t') for x in (out/'passive-inventory.tsv').read_text().splitlines())}
 endpoints=endpoint_check(out,out/'timed-endpoints',std.read_text(),passive);annotation=annotation_check(out);clocks=clock_check(out)
 resolved=(out/'constraints-readback.sdc').read_text();period=float(re.search(r'create_clock .*?-period ([0-9.eE+-]+)',resolved)[1]);assert abs(period-3.333333333)<1e-6;assert not re.search(r'^set_(?:false_path|multicycle_path|case_analysis)',resolved,re.M)
 # A bit-specific Tcl port token is required; avoid substring matches [1]/[10].
 wrapper=(HERE.parents[1]/'rtl/mother_control_v1/mother_control_64.sv').read_text().split(');',1)[0];bits={'input':[],'output':[]}
 for direction,width,name in re.findall(r'(input|output) wire (\[[^\]]+\])?\s*(\w+)',wrapper):
  if name=='clk_i':continue
  count=int(width.strip('[]').split(':')[0])+1 if width else 1
  bits[direction].extend([name] if count==1 else [f'{name}[{i}]' for i in range(count)])
 for direction,names in bits.items():
  command='set_'+direction+'_delay';lines=[x for x in resolved.splitlines() if x.startswith(command)]
  for name in names:
   tokens=[name,name.replace('[','\\[').replace(']','\\]')];found=[x for x in lines if any(re.search(r'(?<![A-Za-z0-9_])'+re.escape(token)+r'(?![A-Za-z0-9_\[])',x) for token in tokens)]
   for flag,expected in [('-max',.5),('-min',.05)]:
    selected=[x for x in found if flag in x];assert selected,(name,flag);assert all(abs(float(re.search(command+r'\s+([0-9.eE+-]+)',x)[1])-expected)<1e-6 for x in selected)
   if direction=='output':
    loads=[x for x in resolved.splitlines() if x.startswith('set_load ') and any(re.search(r'(?<![A-Za-z0-9_])'+re.escape(token)+r'(?![A-Za-z0-9_\[])',x) for token in tokens)];assert loads and all(abs(float(re.search(r'-pin_load\s+([0-9.eE+-]+)',x)[1])-5)<1e-6 for x in loads),name
 checks={'timed_endpoints':endpoints['passed'],'all_connected_rc_annotated':annotation['passed'],'sram_clock_checks':clocks['passed'],'pg_signal_placement':all(physical[k]==[v] for k,v in {'unplaced':'0','incorrect_pg_iterms':'0','open_signal_inputs':'0','pg_VDD':'1','pg_VSS':'1'}.items()),'native_route_drc':not (out/'native-drc.rpt').read_text().strip(),'sdc_all_bits':True}
 report=dict(schema='mother-native-audit/1',candidate=str(work),final_sha256=digests,checks=checks,endpoint_proof=endpoints,annotation=annotation,sram_clocks=clocks,full_gds_drc_performed=False,passed=False)
 (out/'audit.json').write_text(json.dumps(report,indent=2)+'\n');assert all(checks.values()),checks
 if a.full_drc:
  deck=platform/'drc/FreePDK45.lydrc';assert sha(deck)=='4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147';run(['klayout','-b','-r',deck,'-rd','in_gds='+str(files['gds']),'-rd','report_file='+str(out/'full-drc.lyrdb')],'full-drc.log');from xml.etree import ElementTree as ET;count=len(ET.parse(out/'full-drc.lyrdb').findall('.//items/item'));checks['full_original_gds_drc']=count==0;report.update(full_gds_drc_performed=True,full_gds_drc_items=count,full_deck_sha256=sha(deck))
  tcl('views',f'read_liberty {{{std}}}\nread_liberty {{{bank}}}\nread_db {{{files["odb"]}}}\nread_sdc {{{files["sdc"]}}}\nread_spef {{{files["spef"]}}}\nset_propagated_clock [all_clocks]\nwrite_timing_model -library_name mother_control_64_tt -cell_name mother_control_64 mother_control_64.lib\nwrite_abstract_lef -bloat_factor 0 mother_control_64.lef\n')
  report['views_sha256']={str(p.name):sha(p) for p in out.glob('mother_control_64.*')}
 report['passed']=a.full_drc and all(checks.values());assert digests=={k:sha(v) for k,v in files.items()};(out/'audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':report['passed'],'checks':checks}),flush=True)
 if a.full_drc:assert report['passed']
if __name__=='__main__':main()
