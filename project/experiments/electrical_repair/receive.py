"""Server independent electrical-repair reception, functional graph and measured gates."""
import argparse,collections,copy,csv,hashlib,json,re,subprocess,sys
from decimal import Decimal
from pathlib import Path
from probe import ROOT,LIB,LEF,TECH,sha
from structure import library,certificate,input_loads,need
sys.path.insert(0,str(ROOT/'project/experiments/cache_share'))
from verify import reference,check
R84=Path('/public/home/yuzelu/RuizhiLiang/issue84-cache-share-20261025')
R86=Path('/public/home/yuzelu/RuizhiLiang/issue86-gate-sta-20261025')
def load(p):return json.loads(p.read_text())
def put(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def artifacts(p):
 m=load(p/'manifest.json')
 for e in m['artifacts']:
  q=p/e['path'];need(q.parent==p and q.is_file(),'direct artifact');need(q.stat().st_size==e['bytes']and sha(q)==e['sha256'],'artifact bytes SHA '+str(q))
 return m

def same_int(x,y):return type(x)is int and x==y
def protocol(p):need(isinstance(p,dict)and set(p)=={'actual_M_active_reset','no_stale_completion','SRAM_retained'}and all(type(v)is bool and v for v in p.values()),'complete typed protocol')
def csvrows(p):return list(csv.DictReader(p.read_text().splitlines(),delimiter='\t'))
def electrical(log):
 need(log.count('BEGIN_ELECTRICAL_REPORT')==1 and log.count('END_ELECTRICAL_REPORT')==1,'actual unique report execution markers')
 log=log.split('BEGIN_ELECTRICAL_REPORT')[1].split('END_ELECTRICAL_REPORT')[0];ans={}
 for section,nextsection,key in(('max slew','max capacitance','slew'),('max capacitance','END_NOT_PRESENT','cap')):
  match=re.search(r'(?m)^'+section+r'\s*$',log)
  block=log[match.end():]if match else''
  end=re.search(r'(?m)^(max capacitance|max delay/setup|min delay/hold)\s*$',block)
  if end:block=block[:end.start()]
  ans[key+'_violations']=block.count('(VIOLATED)')
 return ans

def audit(a,v,lib):
 repair=a.root/(f'pilot-v{v}04'if v==3 else f'repair-v{v}04');prep=a.root/f'prepare-v{v}04';old=R86/f'prepare-v{v}01'
 rm=artifacts(repair);pm=artifacts(prep);om=artifacts(old)
 need(same_int(rm['variant'],v) and same_int(pm['variant'],v) and rm['status']=='REPAIR_EXECUTED_NOT_RECEIVED'and pm['status']=='EXACT_MAPPED_NETLIST_EXPORTED_WITH_DECLARED_STORE_CUT','repair/prep typed variant and status')
 need(rm['prior_prepared_manifest_sha256']==pm['prior_prepared_manifest_sha256']==sha(old/'manifest.json'),'original source manifest binding')
 need(pm['repair_manifest_sha256']==sha(repair/'manifest.json')and pm['repair_directory']==str(repair),'actual repaired source binding')
 for p in(LIB,TECH,LEF):need(rm['inputs'][str(p)]==sha(p),'exact unchanged research view')
 need(load(prep/'cut-contract.json')==load(old/'cut-contract.json'),'unchanged SRAM cut contract')
 # Independent reparse of ORIGINAL Verilog, not trusting the repairer's intermediate JSON.
 ys=a.out/f'independent-v{v}.ys';original_json=a.out/f'independent-v{v}.json'
 ys.write_text(f'read_liberty -lib {LIB}\nread_verilog {old}/cut.v\nhierarchy -top chain84\ncheck -assert\nwrite_json {original_json}\n')
 cmd=['/public/software/singularity-ce-4.3.4/bin/singularity','exec','--bind','/public/home/yuzelu/opt/eda:/eda:ro','--pwd',str(a.out),'/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif','yosys','-s',str(ys)]
 with (a.out/f'independent-v{v}.log').open('w')as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=120,stdin=subprocess.DEVNULL)
 need(r.returncode==0,'independent original parse');put(a.out/f'independent-v{v}-command.json',{'argv':cmd,'exit':r.returncode})
 before=load(original_json)['modules']['chain84'];after=load(prep/'cut.json')['modules']['chain84'];need(before==load(repair/'baseline.json')['modules']['chain84'],'repair baseline equals independent original parse')
 cert=certificate(before,after,lib)
 stat=load(prep/'stat.json');need(Decimal(str(stat['design']['area']))==Decimal(cert['after_area_um2']),'independent Liberty/Yosys area equality')
 # Persist one actual mutated-netlist file and reread to exercise the structural rejection gate.
 bad=copy.deepcopy(after);bit=cert['constant_output_bits'][0];bad['ports'][bit['port']]['bits'][bit['bit']]=str(1-bit['value']);path=a.out/f'negative-net-v{v}.json';put(path,bad)
 try:certificate(before,load(path),lib)
 except ValueError:pass
 else:raise ValueError('constant output mutation accepted')
 cert['negative_netlist_sha256']=sha(path);cert['prepared_manifest_sha256']=sha(prep/'manifest.json')
 bad=copy.deepcopy(after);ff=next(n for n,c in bad['cells'].items()if c['type'].startswith('DFF'));oldbit=bad['cells'][ff]['connections']['D'][0];bad['cells'][ff]['connections']['D'][0]='1'if oldbit=='0'else'0';nf=a.out/f'negative-dff-v{v}.json';put(nf,bad)
 try:certificate(before,load(nf),lib)
 except ValueError:pass
 else:raise ValueError('DFF data connection mutation accepted')
 cert['negative_DFF_connection_sha256']=sha(nf)
 loads={'before':input_loads(before,lib),'after':input_loads(after,lib),'external_load_assumptions_fF':[1,10],'capacitance_policy':'nominal pin capacitance plus separate max(nominal,rise,fall); no wires; output aliases multiply each declared external load','upstream_driver_impedance':'not modeled; fixed input waveform and ideal clock do not qualify upstream or clock tree'}
 put(a.out/f'inputs-v{v}.json',loads);put(a.out/f'structure-v{v}.json',cert)
 return cert,pm

def timing(a,v,cert):
 folder=a.root/f'sta-v{v}05';tm=artifacts(folder);sm=load(folder/'timing-summary.json');need(same_int(tm['variant'],v) and tm['status']=='DECLARED_CUT_LOGIC_TIMING_EXECUTED','STA actual variant/status');need(sm['prepared_manifest_sha256']==cert['prepared_manifest_sha256']and sm['library_sha256']==sha(LIB),'STA exact repaired input')
 net=load(a.root/f'prepare-v{v}04/cut.json')['modules']['chain84'];dffs={n+'/D'for n,c in net['cells'].items()if c['type'].startswith('DFF')};outs=set()
 for n,p in net['ports'].items():
  if p['direction']=='output':outs.update(n if len(p['bits'])==1 else n+'['+str(i)+']'for i in range(len(p['bits'])))
 excluded={e['port']+'['+str(e['bit'])+']'for e in cert['constant_output_bits']};expected=dffs|(outs-excluded);scenarios=[]
 need([s['output_load_fF']for s in sm['scenarios']]==[1,10],'both frozen output loads')
 for sc in sm['scenarios']:
  load_ff=sc['output_load_fF'];log=(folder/f'sta-load{load_ff}.log').read_text();need('Error:'not in log and'Warning:'not in log,'STA errors/warnings');need(log.split('BEGIN_CHECK_SETUP')[1].split('END_CHECK_SETUP')[0].strip()=='','no-clock/unconstrained checks empty')
  rr=csvrows(folder/f'r2r-load{load_ff}.tsv');setup=csvrows(folder/f'setup-all-load{load_ff}.tsv');hold=csvrows(folder/f'hold-load{load_ff}.tsv')
  for rows,exp,label in((rr,dffs,'R2R'),(setup,expected,'all setup'),(hold,expected,'all hold')):
   names=[r['endpoint']for r in rows];need(len(names)==len(set(names))and set(names)==exp,'exact endpoint coverage '+label)
  row={**sc,**electrical(log),'independent_all_setup_violating_endpoints':sum(Decimal(r['slack'])<0 for r in setup),'independent_all_hold_violating_endpoints':sum(Decimal(r['slack'])<0 for r in hold),'unconstrained_or_no_clock_endpoints_reported':0,'all_setup_hold_endpoint_count':len(expected),'constant_output_exclusions':sorted(excluded),'original_DFFs_covered':len(dffs),'external_upstream_clock_load_qualification':False}
  need(row['independent_all_setup_violating_endpoints']==sc['all_setup_violating_endpoints']and row['independent_all_hold_violating_endpoints']==sc['hold_violating_endpoints'],'recomputed summary violations')
  row['acceptance']='PASS_DECLARED_INTERNAL_ELECTRICAL_SETUP_HOLD'if not any(row[k]for k in('slew_violations','cap_violations','independent_all_setup_violating_endpoints','independent_all_hold_violating_endpoints'))else'RESIDUAL_VIOLATIONS_NOT_CLOSED'
  scenarios.append(row)
 return scenarios

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--variants',default='0,1,2,3');p.add_argument('--structure-only',action='store_true');a=p.parse_args();a.out.mkdir(exist_ok=False);bd=load(ROOT/'binding.json')
 for n,h in bd['sources'].items():need(sha(ROOT/n)==h,'receiver source SHA')
 lib=library(LIB);tech=TECH.read_text();lef=LEF.read_text();db=re.search(r'DATABASE\s+MICRONS\s+(\d+)',tech);need(bool(db),'LEF database unit declared')
 macros={}
 for match in re.finditer(r'(?m)^MACRO\s+(\S+)',lef):
  n=match.group(1);body=lef[match.end():];end=re.search(r'(?m)^END\s+'+re.escape(n)+r'\s*$',body);need(bool(end),'LEF macro termination');body=body[:end.start()];size=re.search(r'SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)',body)
  if size:macros[n]=Decimal(size.group(1))*Decimal(size.group(2))
 used=set()
 for v in map(int,a.variants.split(',')):used.update(c['type']for c in load(a.root/f'prepare-v{v}04/cut.json')['modules']['chain84']['cells'].values())
 for n in used:need(n in macros and macros[n]==lib[n]['area'],'Liberty/LEF cell area agreement '+n)
 put(a.out/'view-units.json',{'liberty_time_unit':'ns','liberty_capacitance_unit':'fF','LEF_size_unit':'um','LEF_database_units_per_micron':int(db.group(1)),'all_used_cell_LEF_and_Liberty_areas_equal':True,'used_cell_types':len(used),'library_sha256':sha(LIB),'tech_lef_sha256':sha(TECH),'cell_lef_sha256':sha(LEF)})
 im=artifacts(R84/'input01');case=load(R84/'input01/cases.json')[0];refs={}if a.structure_only else{c:reference(R84/'input01',case,c)for c in(0,1)}
 if refs:need(refs[0]==refs[1],'cache packing invariant function')
 rows=[]
 for v in map(int,a.variants.split(',')):
  cert,pm=audit(a,v,lib);ts=timing(a,v,cert);gates=[]
  if not a.structure_only:
   bm=artifacts(a.root/f'build-v{v}04');need(bm['status']=='GATE_BINARY_BUILT_NOT_EXECUTED'and same_int(bm['variant'],v) and bm['prepared_manifest_sha256']==cert['prepared_manifest_sha256'],'actual build binding');need(sha(a.root/f'build-v{v}04/obj/Vchain84')==bm['binary_sha256'],'actual binary')
   for stall in(0,1):
    f=a.root/f'gate-v{v}s{stall}04';gm=artifacts(f);need(gm['status']=='PASS_GATE_REPLAY_ALL_OBSERVABLES_AND_RESET'and same_int(gm['variant'],v) and same_int(gm['stall'],stall) and gm['build_manifest_sha256']==sha(a.root/f'build-v{v}04/manifest.json'),'gate complete dependency variant/stall')
    actual=[json.loads(s)for s in(f/'actual.jsonl').read_text().splitlines()];need(len(actual)==1 and actual[0]['name']==case['name'],'selected complete case');row=actual[0];check(row,refs[v//2],v//2)
    goldroot=R84/f'rtl-v{v}s{stall}02';goldm=artifacts(goldroot);need(same_int(goldm['profile'],v) and same_int(goldm['stall'],stall) and goldm['input_manifest_sha256']==sha(R84/'input01/manifest.json'),'original config/input binding');need(row==json.loads((goldroot/'actual.jsonl').read_text().splitlines()[0]),'all original RTL observables')
    src=R84/'input01'/f'vectors-c{v//2}.tsv';need((f/'vectors.tsv').read_text()==src.read_text().splitlines()[0]+'\n'and gm['vectors_source_sha256']==sha(src),'exact original input vector bytes');need(gm['baseline_output_sha256']==sha(goldroot/'actual.jsonl'),'baseline SHA');protocol(load(f/'actual.jsonl.protocol.json'))
    neg=copy.deepcopy(row);neg['out'][0]^=1;nf=a.out/f'negative-gate-v{v}s{stall}.json';put(nf,neg)
    try:check(load(nf),refs[v//2],v//2)
    except ValueError:pass
    else:raise ValueError('gate mutation accepted')
    gates.append({'stall':stall,'cycles':row['cycles'],'status':'PASS_INDEPENDENT_COMPLETE_INTEGER_OUTPUTS_CONFIG_AND_RESET','manifest_sha256':sha(f/'manifest.json'),'negative_sha256':sha(nf)})
  rows.append({'variant':v,'structure':cert,'timing':ts,'gates':gates})
 for i,bad in enumerate(({}, {'actual_M_active_reset':True},{'actual_M_active_reset':True,'no_stale_completion':True,'SRAM_retained':1},{'actual_M_active_reset':True,'no_stale_completion':True,'SRAM_retained':True,'extra':True})):
  nf=a.out/f'negative-protocol-{i}.json';put(nf,bad)
  try:protocol(load(nf))
  except ValueError:pass
  else:raise ValueError('protocol mutation accepted')
 config_negatives=[True,False,'0',0.0,None,-1,99];nf=a.out/'negative-config-types.json';put(nf,config_negatives);need(all(not same_int(x,0)for x in load(nf)),'strict configuration integer rejection')
 result={'all_variants_internal_electrical_setup_hold_closed':all(t['acceptance']=='PASS_DECLARED_INTERNAL_ELECTRICAL_SETUP_HOLD'for row in rows for t in row['timing']),'status':'PASS_STRUCTURE_AND_TIMING_RECEPTION_ONLY'if a.structure_only else'PASS_REPAIRED_GRAPH_GATE_MATH_AND_DECLARED_TIMING_RECEPTION','source':bd,'input_manifest_sha256':sha(R84/'input01/manifest.json'),'views':{str(p):sha(p)for p in(LIB,TECH,LEF)},'variants':rows,'limits':['Typical research library only; ideal clock and no wire parasitics or placement/routing.','Entire store82 timing cut; behavioral memory only in gate replay. No target SRAM/ROM qualification.','Fixed input waveform, no upstream driving cell or source impedance. Full input sink costs reported separately.','Zero-delay selected gate replay plus all original cell-pin/port structural function certificate; not transistor/PVT or CDC signoff.','Tie Boolean models/cell area exist; tie timing/maximum load not specified by these Liberty cells.','Only original Issue84 hardware; Issue85/92 runtime epoch hardware excluded.']}
 put(a.out/'receipt.json',result);print(result['status'])
if __name__=='__main__':main()