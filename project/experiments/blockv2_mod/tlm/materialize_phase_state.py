"""Read state bytes from completed prefill, preserving compiled view addressing."""
import argparse,json
from pathlib import Path
from macro_state import load
from macro_assets import filehash
def main():
 p=argparse.ArgumentParser()
 for name in ('bridge','state','source_receipt','output'):p.add_argument(name,type=Path)
 a=p.parse_args();bridge=json.loads(a.bridge.read_text());receipt=json.loads(a.source_receipt.read_text())
 meta,words=load(a.state)
 if receipt.get('status')!='all_instructions_executed' or meta['plan_sha256']!=bridge['source_plan_sha256'] or receipt['plan_sha256']!=meta['plan_sha256']:
  raise ValueError('requires successful matching prefill execution')
 if receipt['committed_state']['sha256']!=meta['sha256']:raise ValueError('prefill state identity')
 a.output.mkdir(exist_ok=False);inputs={}
 for i,(name,spec) in enumerate(bridge['states'].items()):
  data=bytearray(spec['bytes']);covered=bytearray(spec['bytes'])
  for run in spec['runs']:
   for n in range(run['elements']):
    address=spec['source_base']+4*(run['source_element']+n);destination=4*(run['destination_element']+n)
    raw=words[address//64*64].slice(address%64,4).require()
    if any(covered[destination:destination+4]):raise ValueError('state copy overlap')
    data[destination:destination+4]=raw;covered[destination:destination+4]=b'\x01'*4
  if not all(covered):raise ValueError('unwritten state input')
  path=a.output/f'state-{i:03d}.i32le';path.write_bytes(data)
  inputs[name]={'file':path.name,'sha256':filehash(path),'shape':spec['shape'],
   'exponent':spec['exponent'],'source_root':spec['source_root']}
 result={'schema':'native-runtime-state-inputs/1','destination_plan_sha256':bridge['destination_plan_sha256'],
  'source_state_sha256':meta['sha256'],'source_plan_sha256':meta['plan_sha256'],'inputs':inputs,
  'transition_timing_included':False,'scope':'committed prefill bytes with view-only relocation, no numerical recomputation'}
 (a.output/'runtime-inputs.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'materialized_states':len(inputs),'source_state_sha256':meta['sha256']}))
if __name__=='__main__':main()
