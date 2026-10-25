"""Read-only exact driver comparison between accepted GRT and actual detailed RCX."""
import argparse,re
from decimal import Decimal
from common import *
from receive_physical import library,block,def_name
from route_audit import incidence,same_wiring
p=argparse.ArgumentParser();p.add_argument('--before',type=Path,required=True);p.add_argument('--before-strict',type=Path,required=True);p.add_argument('--after',type=Path,required=True);p.add_argument('--after-strict',type=Path,required=True);p.add_argument('--driver',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);inst,pin=a.driver.rsplit('/',1);mods=[load(s/'final.json')['modules']for s in(a.before,a.after)];top=next(n for n in mods[0]if n in('chain93','chain97'));nets=[m[top]for m in mods];identity=same_wiring(*nets);lib=library(LIB);result=[]
for stage,strict,net in zip((a.before,a.after),(a.before_strict,a.after_strict),nets):
 sm=artifacts(stage);artifacts(strict);proof=load(strict/'receipt.json');need(proof['stage_manifest_sha256']==sha(stage/'manifest.json'),'full strict evidence exact stage');c=net['cells'][inst];b=c['connections'][pin][0];refs,dirs,_=incidence(net);dn=None
 for name,body in re.findall(r'(?s)-\s+(\S+)\s+(.*?);',block((stage/'placed.def').read_text(),'\nNETS ','END NETS').split(';',1)[1]):
  ps={(def_name(n),def_name(pn))for n,pn in re.findall(r'\(\s*(\S+)\s+(\S+)\s*\)',body.split('+',1)[0])}
  if(inst,pin)in ps:need(dn is None,'unique exact driver net');dn=def_name(name);defbody=body
 need(dn is not None,'actual physical net');log=(strict/'probe.log').read_text();row=[]
 for k in(1,10):
  section=block(log,f'BEGIN_FULL_max_capacitance_{k}',f'END_FULL_max_capacitance_{k}');found=[x.split()for x in section.splitlines()if x.split()and x.split()[0]==a.driver];need(len(found)==1,'one full actual driver row');row.append({'load_fF':k,'limit_fF':found[0][1],'actual_fF':found[0][2],'slack_fF':found[0][3]})
 text=(stage/'route.spef').read_text();scale=Decimal(1000)if sm['stage']=='drt'else Decimal(1);names={}
 if sm['stage']=='drt':
  for q in text.split('*NAME_MAP\n',1)[1].split('*PORTS',1)[0].split('*D_NET',1)[0].splitlines():
   m=re.fullmatch(r'\*(\d+) (.+)',q)
   if m:names[m[1]]=def_name(m[2])
 def resolved(x):return names.get(x.removeprefix('*'),x)if x.startswith('*')else def_name(x)
 sections=[m for m in re.finditer(r'(?ms)^\*D_NET (\S+) (\S+)\n(.*?)^\*END\s*$',text)if resolved(m[1])==dn];need(len(sections)==1,'one exact actual RC section');q=sections[0];caps=q[3].split('*CAP\n',1)[1].split('*RES\n',1)[0].strip().splitlines();ground=sum((Decimal(x.split()[-1])for x in caps if len(x.split())==3),Decimal(0))*scale;coupling=sum((Decimal(x.split()[-1])for x in caps if len(x.split())==4),Decimal(0))*scale;sinks=[]
 for ref in sorted(refs[b]-{inst+':'+pin}):
  if ref.startswith('PORT:'):sinks.append({'pin':ref,'external_load':'dual1/10fF'})
  else:n,pn=ref.rsplit(':',1);sinks.append({'pin':ref,'master':net['cells'][n]['type'],'liberty_cap_fF':{k:str(v)for k,v in lib[net['cells'][n]['type']]['pins'][pn]['cap'].items()}})
 result.append({'stage':str(stage),'stage_manifest_sha256':sha(stage/'manifest.json'),'strict_manifest_sha256':sha(strict/'manifest.json'),'model':'actual detailed RCX readback'if sm['stage']=='drt'else'actual GRT estimate','master':c['type'],'net':dn,'all_pins':sorted(refs[b]),'sinks':sinks,'strict_driver_rows':row,'RC_D_NET_fF':str(Decimal(q[2])*scale),'written_ground_fF':str(ground),'written_coupling_fF':str(coupling),'DEF_net_body_sha256':hashlib.sha256(defbody.encode()).hexdigest()})
contract=load(HERE/'margin_contract.json');selected=[x['pin']for x in contract['targets'][top.removeprefix('chain')]['drivers']];put(a.out/'comparison.json',{'status':'READONLY_EXACT_DRIVER_GRT_VS_RCX','source':sources(),'driver':a.driver,'electrical_identity':identity,'final_verilog_byte_identical':sha(a.before/'final.v')==sha(a.after/'final.v'),'already_in_margin80_batch':a.driver in selected,'rows':result,'BUF_X4_input_max_fF':str(max(lib['BUF_X4']['pins']['A']['cap'].values())),'BUF_X4_area_um2':str(lib['BUF_X4']['area']),'limits':['GRT and detailed RCX are different geometry/RC models; no attribution solely to route length.','GRT writtenCAP omits pin-access terms, reported D_NET and actual STA load retained separately.','No repair executed; same precision, area budget and full endpoint constraints remain.']});print('READONLY_EXACT_DRIVER_GRT_VS_RCX')
