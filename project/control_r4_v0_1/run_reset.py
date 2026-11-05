"""Actual reset cohort plus independently checked reloading/readmission."""
import argparse,json,os,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;OLD=HERE.parent/'control_rtl_min_v0_1';sys.path.insert(0,str(OLD))
import run as common,reset_check,stored_ack_check
def main():
 p=argparse.ArgumentParser();p.add_argument('--verilator',required=True);p.add_argument('--out',type=pathlib.Path,required=True)
 p.add_argument('--stored-ack', action='store_true', help='exercise stale stored ACK after cohort reload')
 a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True);env=dict(os.environ)
 bundles=json.loads((HERE.parent/'control_image_v0_1/bundles.json').read_text(encoding='utf-8'))['bundles'];images={k:bytes.fromhex(v) for k,v in next(b for b in bundles if b['manifest']['bundle']=='receiver_first_16B')['images_hex'].items()}
 paths={}
 for key,data in images.items():
  f=out/(key+'.mem');f.write_text('\n'.join('{:032x}'.format(int.from_bytes(data[i:i+16],'little')) for i in range(0,len(data),16))+'\n');paths[key]=f
 def compile(top,files,directory):
  directory.mkdir(parents=True,exist_ok=True);cmd=[a.verilator,'--binary','--timing','--top-module',top,'-I'+str(HERE),'-I'+str(OLD),'--Mdir',directory/'obj_dir','-j','4','-o','sim']+files
  log=common.run(cmd,directory,env,directory/'compile.log');return dict(command=[str(x) for x in cmd],log_sha256=common.sha(log.encode()))
 source=[OLD/x for x in ['mc_min_controller.sv','lc_min_controller.sv','tb_network_pm.sv']]+[HERE/x for x in ['lc_raw16_s_adapter.sv','raw16_dma_bridge.sv','cohort_reset_controller.sv','finite_external_memory.sv','tb_reset_local.sv','tb_control_reset.sv']]+[HERE.parent/x for x in ['rtl/block_local_s/block_local_s_arbiter.sv','rtl/block_local_s/block_local_s_macro.sv','rtl/block_feed_v1/block_feed_s16k.sv','rtl/block_feed_v1/block_feed_loader.sv','rtl/hbm_feed/hbm_group_dma.sv','rtl/hbm_feed/hbm_async_fifo.sv']]
 if a.stored_ack: source=['-DTB_STORED_ACK_GUARD',HERE/'p_stored_ack_guard.sv']+source
 build=compile('tb_control_reset',source,out);results=[]
 names=['clean_reset_reload','held_external_STORE_flush','old_response_FIFO_flush','partial_reload_gate','DMA_poison_recovery','lost_TX_ACK_recovery']
 for scenario,name in enumerate(names):
  args=[out/'obj_dir/sim','+SCENARIO='+str(scenario),'+STALL=2','+IMAGE='+str(paths['mother']),'+WORDS='+str(len(images['mother'])//16)]
  for b in (0,1):args+=['+LOCAL'+str(b)+'='+str(paths['local'+str(b)]),'+WORDS'+str(b)+'='+str(len(images['local'+str(b)])//16)]
  log=common.run(args,out,env,out/(name+'.log'));common.check_cycles.need('PASS reset' in log,'reset integration PASS missing')
  checked=reset_check.check(log,scenario,images)
  if a.stored_ack:
   ack=stored_ack_check.check(log)
   assert ack['pending'] is None and ack['rejected']==int(scenario==5)
   if scenario==5:
    [old]=ack['abandoned']
    assert old['commit'] is not None and old['accepted'] is None
    assert [r['identity']>>208 for r in ack['receipts']]==[(8<<32)|2,(9<<32)|2]
   checked['stored_ack_guard']=ack
  if scenario==0:mutants=reset_check.mutations(log,scenario,images)
  results.append(dict(name=name,scenario=scenario,checker=checked,command=[str(x) for x in args],log_sha256=common.sha(log.encode())))
  print(name,'PASS',checked['cycles'],'cycles',flush=True)
 unit=out/'coordinator';unitbuild=compile('tb_cohort_reset',[HERE/'cohort_reset_controller.sv',HERE/'tb_cohort_reset.sv'],unit);units=[]
 for mode,name in enumerate(['complete_ACK_new_epoch','missing_ACK','stale_ACK_sequence','stale_ACK_epoch','duplicate_ACK','not_quiet','partial_reload','old_reload_generation','missing_reload','old_reset_epoch','runtime_fault']):
  log=common.run([unit/'obj_dir/sim','+MODE='+str(mode)],unit,env,unit/(name+'.log'));common.check_cycles.need('PASS cohort' in log,'coordinator PASS missing');units.append(dict(name=name,mode=mode,log_sha256=common.sha(log.encode())))
 report=dict(schema='actual-control-cohort-reset/0.1',results=results,coordinator_unit_cases=units,mutations=mutants,compile=build,unit_compile=unitbuild,
  tools=dict(verilator=common.run([a.verilator,'--version'],out,env).strip(),python=sys.version),
  input_images_sha256={k:common.sha(v) for k,v in images.items()},actual_MC=True,actual_LCs=2,actual_S=2,actual_DMA=True,CDC_FIFOs=2,
  ACK_provider='trusted test wrapper certifies synchronous reset edges and empty public provider outputs; no production management transport or physical reset/CDC qualification')
 (out/'reset_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('PASS 6 actual reset/reload integrations +11 coordinator RTL boundaries; 4 mutants rejected',flush=True)
if __name__=='__main__':main()
