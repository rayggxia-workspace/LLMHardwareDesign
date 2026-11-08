"""Directed bridge RTL boundaries; DMA/native observations are explicit peers."""
import pathlib,os,json,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent.parent/'control_rtl_min_v0_1'))
import run as common
def run(verilator,out):
 out.mkdir(parents=True,exist_ok=True);here=pathlib.Path(__file__).resolve().parent;env=dict(os.environ);obj=out/'obj_dir'
 cmd=[verilator,'--binary','--timing','--top-module','tb_dma_bridge','--Mdir',obj,'-j','4','-o','sim',here/'raw16_dma_bridge.sv',here/'tb_dma_bridge.sv']
 build=common.run(cmd,out,env,out/'compile.log');results=[]
 names=['write_full_identity','read_full_identity','wrong_tag','wrong_words','external_status','protocol_error','early_completion','duplicate_native_ACK','tag_exhaustion','admit_gate']
 for mode,name in enumerate(names):
  log=common.run([obj/'sim','+MODE='+str(mode)],out,env,out/(name+'.log'));common.check_cycles.need('PASS bridge' in log,'bridge PASS missing')
  results.append(dict(name=name,mode=mode,log_sha256=common.sha(log.encode())))
 report=dict(cases=results,compile_command=[str(x) for x in cmd],compile_log_sha256=common.sha(build.encode()),provider='explicit bounded peers, not hbm_group_dma in this directed bench')
 (out/'bridge_report.json').write_text(json.dumps(report,indent=2)+'\n');return report
