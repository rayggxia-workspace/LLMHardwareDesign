from pathlib import Path
import importlib.util,types,tempfile,os,json,subprocess
sp=importlib.util.spec_from_file_location('overlay','project/experiments/s_sram/initial_dc_overlay.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
with tempfile.TemporaryDirectory(dir='.local',prefix='dc-overlay-control-') as tmp:
 root=Path(tmp).resolve();src=root/'source';ref=src/'compiler/characterizer/stimuli.py';ref.parent.mkdir(parents=True);ref.write_bytes(Path('.local/stimuli-reference155.py').read_bytes());original=ref.read_bytes()
 subprocess.run(['python','project/experiments/s_sram/initial_dc_overlay.py','--source',str(src),'--destination',str(root/'overlay'),'--receipt',str(root/'proof.json')],check=True)
 assert ref.read_bytes()==original
 namespace={'OPTS':types.SimpleNamespace(openram_temp=str(root))};exec(m.AUDIT,namespace)
 nested=root/'nested.sp';nested.write_text('* model fixture\n.model nm NMOS\n');model=root/'model.sp';model.write_text('.include nested.sp\n');stim=root/'stim.sp';stim.write_text('.include "'+str(model)+'"\n.TRAN 10p 1n\n.end\n',encoding='utf-8');(root/'.spiceinit').write_text('option klu\n')
 os.environ['S_SRAM_CHARACTERIZATION_AUDIT']=str(root/'audit')
 state=namespace['_s_sram_audit_begin'](stim);assert len(state[2]['inputs'])==4
 (root/'timing.lis').write_text('Measurement fixture only\n');namespace['_s_sram_audit_end'](state,0)
 record=json.loads((state[1]/'receipt.json').read_text());assert record['outputs'] and not record['qualified']
 state=namespace['_s_sram_audit_begin'](stim);nested.write_text('* changed device model\n');rejected=False
 try:namespace['_s_sram_audit_end'](state,0)
 except AssertionError:rejected=True
 assert rejected
 del os.environ['S_SRAM_CHARACTERIZATION_AUDIT']
print('PASS: native source patch, original unchanged, recursive includes/JSON/object capture, changed model rejected')

