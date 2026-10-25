"""Independent server reception of full gate math and declared timing scope."""
import argparse,copy,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'project/experiments/cache_share'))
from verify import reference,check

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def need(b,s):
 if not b:raise ValueError(s)
def exact_protocol(p):
 need(isinstance(p,dict)and set(p)=={'actual_M_active_reset','no_stale_completion','SRAM_retained'}and all(type(v)is bool and v for v in p.values()),'actual typed complete protocol')
def chain_bind(g,b,p,v,s):
 need(g['variant']==v and g['stall']==s and b['variant']==v and p['variant']==v,'variant/stall at every dependency')
 need(g['status']=='PASS_GATE_REPLAY_ALL_OBSERVABLES_AND_RESET'and b['status']=='GATE_BINARY_BUILT_NOT_EXECUTED'and p['status']=='EXACT_MAPPED_NETLIST_EXPORTED_WITH_DECLARED_STORE_CUT','dependency status')
def verify_artifacts(root):
 m=load(root/'manifest.json')
 for e in m['artifacts']:need(sha(root/e['path'])==e['sha256'],'artifact SHA '+str(root/e['path']))
 return m

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--prior',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);bd=load(ROOT/'binding.json')
 for n,h in bd['sources'].items():need(sha(ROOT/n)==h,'receiver frozen source')
 im=verify_artifacts(a.prior/'input01');cases=load(a.prior/'input01/cases.json');case=cases[0];gates=[];timings=[];refs={cache:reference(a.prior/'input01',case,cache)for cache in(0,1)}
 need(refs[0]==refs[1],'cache packing preserves complete numeric function')
 for v in range(4):
  prep=a.root/f'prepare-v{v}01';pm=verify_artifacts(prep);prior_map=verify_artifacts(a.prior/f'map-v{v}03')
  need(prior_map['profile']==v and prior_map['status']=='LOGIC_ONLY_MAPPED_NOT_PPA','original mapping variant/status');need(pm['mapping_manifest_sha256']==sha(a.prior/f'map-v{v}03/manifest.json'),'original mapped SHA');need((prep/'mapped.json').read_bytes()==(a.prior/f'map-v{v}03/mapped.json').read_bytes(),'exact old mapped bytes')
  orig=load(prep/'mapped.json')['modules']['chain84'];cut=load(prep/'cut.json')['modules']['chain84'];store=[n for n,c in orig['cells'].items()if c['type']=='store82'];need(len(store)==1,'one store')
  expected={n:c for n,c in orig['cells'].items()if n!=store[0]};need(cut['cells']==expected,'cut preserves all logic cells and connections');need(cut['netnames']==orig['netnames'],'no hidden net change')
  for n,p in orig['ports'].items():need(cut['ports'][n]==p,'original port unchanged')
  expected_cut={}
  for n,b in orig['cells'][store[0]]['connections'].items():
   if n in('clk','reset'):continue
   expected_cut['store_'+n]={'direction':'input'if orig['cells'][store[0]]['port_directions'][n]=='output'else'output','bits':b}
  need({n:p for n,p in cut['ports'].items()if n not in orig['ports']}==expected_cut,'every storage boundary bit exposed exactly')
  for s in(0,1):
   folder=a.root/f'gate-v{v}s{s}01';gm=verify_artifacts(folder);need(gm['status']=='PASS_GATE_REPLAY_ALL_OBSERVABLES_AND_RESET','gate completed');bm=verify_artifacts(a.root/f'build-v{v}01');need(gm['build_manifest_sha256']==sha(a.root/f'build-v{v}01/manifest.json'),'exact gate binary chain');need(bm['prepared_manifest_sha256']==sha(prep/'manifest.json'),'exact mapped gate build');chain_bind(gm,bm,pm,v,s)
   actual=[json.loads(x)for x in(folder/'actual.jsonl').read_text().splitlines()];need(len(actual)==1 and actual[0]['name']==case['name'],'selected entire original case');row=actual[0];check(row,refs[v//2],v//2)
   goldroot=a.prior/f'rtl-v{v}s{s}02';goldm=verify_artifacts(goldroot);gold=json.loads((goldroot/'actual.jsonl').read_text().splitlines()[0]);need(row==gold,'all source RTL observable values and config match');need(goldm['input_manifest_sha256']==sha(a.prior/'input01/manifest.json'),'source RTL input binding');need(goldm['profile']==v and goldm['stall']==s,'original variant/stall');need(gm['variant']==v and gm['stall']==s,'gate variant/stall')
   need((folder/'vectors.tsv').read_text()==(a.prior/'input01'/f'vectors-c{v//2}.tsv').read_text().splitlines()[0]+'\n','actual exact selected vector')
   proto=load(folder/'actual.jsonl.protocol.json');exact_protocol(proto)
   negative=copy.deepcopy(row);negative['out'][0]^=1;nf=a.out/f'negative-v{v}s{s}.json';nf.write_text(json.dumps(negative)+'\n');rejected=False
   try:check(load(nf),refs[v//2],v//2)
   except ValueError:rejected=True
   need(rejected,'rehash output mutation rejected');gates.append({'variant':v,'stall':s,'name':case['name'],'cycles':row['cycles'],'run_manifest_sha256':sha(folder/'manifest.json'),'negative_sha256':sha(nf),'status':'PASS_INDEPENDENT_FULL_INTEGER_GATE_OUTPUTS'})
  folder=a.root/f'sta-v{v}03';tm=verify_artifacts(folder);need(tm['status']=='DECLARED_CUT_LOGIC_TIMING_EXECUTED','actual STA');summary=load(folder/'timing-summary.json');need(summary['prepared_manifest_sha256']==sha(prep/'manifest.json'),'STA exact source')
  for sc in summary['scenarios']:
   log=(folder/f"sta-load{sc['output_load_fF']}.log").read_text();need('Error:'not in log and 'Warning:'not in log,'STA parse/link constraints');need(log.split('BEGIN_CHECK_SETUP')[1].split('END_CHECK_SETUP')[0].strip()=='','check_setup flags absent');need(sc['r2r_endpoints_analyzed']==sc['mapped_DFF_cells'],'all DFF endpoints R2R covered')
   slew=log.split('max slew\n',1)[1].split('max capacitance\n',1)[0];caps=log.split('max capacitance\n',1)[1];counts={'max_slew_violations':slew.count('(VIOLATED)'),'max_capacitance_violations':caps.count('(VIOLATED)')}
   where={}
   for role in('startpoint','endpoint'):
    cell=sc['worst_r2r_path'][role].split('/')[0];bits=set(orig['cells'][cell]['connections'].get('Q',[]));where[role]=sorted(n for n,w in orig['netnames'].items()if bits.intersection(w['bits'])and not n.startswith('$'))[:20]
   timings.append({'variant':v,**sc,**counts,'unconstrained_or_no_clock_endpoints_reported':0,'mapped_register_context':where,'acceptance':'DIAGNOSTIC_ONLY_ELECTRICAL_VIOLATIONS_NOT_CLOSED','status':'PASS_DECLARED_LOGIC_CUT_COVERAGE'})
 bad_cases=[]
 for key in ('gate','build','prepared'):
  values=[copy.deepcopy(gm),copy.deepcopy(bm),copy.deepcopy(pm)];values[('gate','build','prepared').index(key)]['variant']=99;bad_cases.append((key,values))
 for key,values in bad_cases:
  nf=a.out/f'negative-binding-{key}.json';nf.write_text(json.dumps(values)+'\n')
  try:chain_bind(*load(nf),v,s)
  except ValueError:pass
  else:raise ValueError('binding mutation accepted')
 for i,bad in enumerate(({}, {'actual_M_active_reset':True}, dict(proto,SRAM_retained=1), dict(proto,extra=True))):
  nf=a.out/f'negative-protocol-{i}.json';nf.write_text(json.dumps(bad)+'\n')
  try:exact_protocol(load(nf))
  except ValueError:pass
  else:raise ValueError('protocol mutation accepted')
 result={'status':'PASS_GATE_MATH_AND_DECLARED_TIMING_RECEPTION','source':bd,'input_manifest_sha256':sha(a.prior/'input01/manifest.json'),'gates':gates,'timing':timings,'limits':['Eight selected complete zero-delay gate replays, not formal all-state equivalence.','One behavioral SRAM wrapper retained in gate simulation, entirely removed and exposed in STA.','No wire RC/clock tree/physical SRAM/ROM/target process or full-chip Fmax.','Electrical slew/cap violations remain; diagnostic period ratios cannot qualify speedup.','Only original Issue84 four variants, not newer Issue85 runtime mode/epoch hardware.']}
 (a.out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
if __name__=='__main__':main()