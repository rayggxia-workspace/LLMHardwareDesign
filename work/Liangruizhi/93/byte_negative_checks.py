"""Metadata-only negative reception tests. No numerical arrays are loaded."""
import argparse,copy,json,sys
from pathlib import Path
import verify_delivery
import verify_sources

def main():
 p=argparse.ArgumentParser();p.add_argument('--repository',type=Path,required=True);p.add_argument('--index',type=Path,required=True);p.add_argument('--selected',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--expected-phases',type=int,default=7);a=p.parse_args();a.out.mkdir(exist_ok=False);original=json.loads(a.index.read_text());results=[]
 for name,mutate in [('schema',lambda x:x.update(schema='issue85-delivery-v1')),('root',lambda x:x.update(root='/wrong')),('member_hash',lambda x:x['files'][next(i for i,v in enumerate(x['files'])if v['path']in x['selected_paths'])].update(sha256='0'*64)),('duplicate_entry',lambda x:x['files'].append(x['files'][0]))]:
  bad=copy.deepcopy(original);mutate(bad);f=a.out/(name+'.json');f.write_text(json.dumps(bad),encoding='utf-8',newline='\n');
  try:verify_delivery.verify(f,a.selected)
  except ValueError as e:results.append({'case':name,'status':'REJECTED','error':str(e)})
  else:raise ValueError('invalid bytes contract accepted '+name)
 f=a.out/'selected.zip';raw=bytearray(a.selected.read_bytes());raw[len(raw)//2]^=1;f.write_bytes(raw)
 try:verify_delivery.verify(a.index,f)
 except ValueError as e:results.append({'case':'archive_changed_byte','status':'REJECTED','error':str(e)})
 else:raise ValueError('changed archive accepted')
 bad=copy.deepcopy(original);bad['files'][next(i for i,v in enumerate(bad['files'])if v['path']=='phase6/project/rtl/gamma_stream/norm93.sv')]['sha256']='0'*64
 try:verify_sources.verify(a.repository,bad,a.selected,a.expected_phases)
 except ValueError as e:results.append({'case':'original_git_byte_hash','status':'REJECTED','error':str(e)})
 else:raise ValueError('wrong original source accepted')
 result={'schema':'gamma93-byte-negatives-v1','status':'PASS_ALL_SIX_REJECTED','tests':results,'scope':'bytes/schema/original Git only, separate from server mathematical and RTL negative tests'};(a.out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');print(result['status'])
if __name__=='__main__':main()
