from pathlib import Path
import subprocess,os,json,concurrent.futures,hashlib,re
BASE=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture');P=Path(__file__).resolve().parent;OUT=Path.cwd()/'results';OUT.mkdir(exist_ok=False)
tasks=[('A0',BASE/'attempt001/results/A0-map','block_v1_r'),('A1',BASE/'attempt035/results/A1-map','block_v1_r')]+[('B'+str(c),BASE/('attempt011/results/'+str(c)),'r_stream')for c in [256,512,1024,2048]]
def run(item):
 name,source,top=item;folder=OUT/name;folder.mkdir();v=(source/'mapped.v').read_text();normalized=re.sub(r'\bwire signed\b','wire',v);net=folder/'input.v';net.write_text(normalized);env=os.environ.copy();env.update(INPUT_NETLIST=str(net),INPUT_TOP=top,INPUT_SDC=str(P/'physical.sdc'));result=dict(candidate=name,passed=False,scope='pre-placement pin-load timing; zero interconnect RC, no physical signoff',mapped_json_sha256=hashlib.sha256((source/'mapped.json').read_bytes()).hexdigest())
 m=json.loads((source/'mapped.json').read_text())['modules'][top];labels={};groups={'state_q':[],'state_d':[],'operand_d':[]}
 for label,n in m['netnames'].items():
  if label.startswith(('bank0[','bank1[','operand_a[','operand_b[','operand_state_base[','oa[','ob[','obase[')):
   for b in n['bits']:labels[b]=label
 for cell,c in m['cells'].items():
  if not c['type'].startswith('DFF'):continue
  q=c['connections'].get('Q',[]);label=labels.get(q[0],'')if q else''
  if label.startswith(('bank0[','bank1[')):groups['state_q'].append(cell+'/Q');groups['state_d'].append(cell+'/D')
  elif label:groups['operand_d'].append(cell+'/D')
 pins=folder/'classified.tcl';pins.write_text(''.join('set '+k+' {'+' '.join('{'+x+'}'for x in vs)+'}\n'for k,vs in groups.items()));env['INPUT_CLASSIFICATION']=str(pins);result['classification_counts']={k:len(v)for k,v in groups.items()};del m
 with(folder/'sta.log').open('w')as f:r=subprocess.run(['openroad','-exit',str(P/'sta_probe.tcl')],stdout=f,stderr=subprocess.STDOUT,env=env)
 result.update(passed=r.returncode==0,exit=r.returncode,log_sha256=hashlib.sha256((folder/'sta.log').read_bytes()).hexdigest());(folder/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');return result
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(run,tasks))
(OUT/'STA_RECEIPTS.json').write_text(json.dumps(rows,indent=2)+'\n');assert all(x['passed']for x in rows)
