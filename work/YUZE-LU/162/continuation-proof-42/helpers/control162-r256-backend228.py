"""Generate fixed named physical configurations from PR168 exact cores."""
from pathlib import Path
import subprocess,re,json,hashlib
repo=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');rev='55f2553bdacbca971b1505a11675a0b1eb12fcad'
for name in ['project/rtl/r_local_state/.gitattributes','work/YUZE-LU/162/r256-integration-20261103/.gitattributes']:
 p=repo/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(subprocess.check_output(['git','show',rev+':'+name],cwd=repo))
rows=[]
for role,old,param,value,macro in [('c_r8','control_c','ENDPOINTS',8,None),('route_r8','control_route','ENDPOINTS',8,'TEST_ENDPOINTS'),('s_arbiter_r7','control_s_arbiter','CLIENTS',7,'TEST_CLIENTS'),('status_r8','control_status','QUEUES',8,'TEST_QUEUES'),('reset_r28','control_reset_distribution','BRANCHES',28,'TEST_RESET_BRANCHES')]:
 new='control_'+role if role!='reset_r28'else'control_reset_distribution_r28'
 parent=repo/'project/rtl/control_v1'/(old+'.sv');text=parent.read_text(encoding='utf-8')
 match=re.search(r'\bmodule\s+'+old+r'\s*#\((.*?)\)\s*\((.*?)\n\);',text,re.S);assert match,old
 header=match[2].replace('output reg','output wire');ports=re.findall(r'\b([A-Za-z_]\w*)\s*(?=,|\n|$)',header);assert len(ports)==len(set(ports))and ports
 target=parent.with_name(new+'.sv');assert not target.exists()
 target.write_text('// Fixed named physical configuration of the exact PR168 core.\nmodule '+new+' #(parameter integer '+param+'='+str(value)+')(\n'+header.strip()+'\n);\n '+old+' #(.'+param+'('+param+')) implementation('+','.join('.'+p+'('+p+')'for p in ports)+');\nendmodule\n',encoding='utf-8')
 stem={'c_r8':'c','route_r8':'route','s_arbiter_r7':'s_arbiter','status_r8':'status','reset_r28':'reset'}[role]
 bench=repo/'project/experiments/control_v1'/('test_'+stem+'.cpp');b=bench.read_text(encoding='utf-8').replace('V'+old,'V'+new)
 if macro:b='#define '+macro+' '+str(value)+'\n'+b
 if role=='c_r8':
  assert b.count('v.task_endpoint==1')==1 and b.count('0x2000,7<<8')==1
  b=b.replace('unsigned word=0;','unsigned word=0;unsigned expected_ep=1;').replace('v.task_endpoint==1','v.task_endpoint==expected_ep').replace('0x2000,7<<8','0x2000,8<<8').replace('current seven-endpoint reference','current eight-endpoint reference')
  marker=' std::cout<<';at=b.index(marker,b.index('int main('))
  b=b[:at]+''' {
 Sim s;s.expected_ep=7;s.cfg(true,0x2000,0x700);s.load({ins(13,1,0,0,1,2),ins(14,2,1),ins(18)});s.random_ready=true;s.cfg(true,4,1);
 for(unsigned n=0;n<300&&s.tasks.empty();++n)s.tick();need(s.tasks.size()==1,"R endpoint7 emitted");
 need((s.tasks[0][0]&65535)==0x700,"R descriptor exact");s.complete(s.tasks[0][0]>>16,7,0,77);s.wait_end();need(s.cfg(false,0x48)==77,"R completion accepted");
 }
'''+b[at:]
 out=bench.with_name('test_'+role+'.cpp');assert not out.exists();out.write_text(b,encoding='utf-8')
 rows.append(dict(model=role,top=new,parent=old,parameter=param,value=value,ports=ports,parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),wrapper_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bench_sha256=hashlib.sha256(out.read_bytes()).hexdigest()))
out=repo/'work/YUZE-LU/162/r256-reuse227/backend-configurations.json';assert not out.exists();out.write_text(json.dumps(dict(configurations=rows,source_pr=168,source_commit=rev,physical_qualified=False,scope='Five new named configurations retain exact PR168 parameterized cores. Each owns all its state in its fixed native M1-M10 physical block; no logic/state in M11/M12. Old default21 packages remain baseline, not qualification for these variants.'),indent=2)+'\n')
print(json.dumps(dict(generated_physical_configurations=len(rows),physical_qualified=False)))
