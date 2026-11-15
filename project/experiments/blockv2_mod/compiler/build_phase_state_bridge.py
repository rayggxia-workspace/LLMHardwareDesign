"""Declare exact source indices for external short-stage state materialization.

This is a runtime scene bridge, not a generated hardware copy instruction. Its
relocation/loading cost is excluded and must not be called request throughput.
"""
import json,sys
from pathlib import Path
from math import prod
from value_layout import contiguous_runs
from native_package_runtime import load
def build(source_package,destination_package,source_graph,source_layout,destination_graph):
 sm,sp,_=load(source_package);dm,dp,_=load(destination_package)
 if (sm['graph_sha256']!=source_graph['source_model_sha256'] or
     sm['graph_sha256']!=source_layout['source_model_sha256'] or
     dm['graph_sha256']!=destination_graph['source_model_sha256']):
  raise ValueError('phase bridge source graph/package mismatch')
 src=json.loads(sp['storage.json']);dst=json.loads(dp['storage.json'])
 entries={};runtime_inputs=set(destination_graph['inputs'])-{'input_ids'}
 for task in destination_graph['tasks']:
  if task['kind']!='Concat':continue
  if len(task['inputs'])!=2:raise ValueError('unsupported state concatenation')
  old,new=task['inputs']
  if old not in runtime_inputs:continue
  layout=source_layout['values'][new]
  if layout['shape']!=destination_graph['values'][old]['shape']:
   raise ValueError('previous phase state shape mismatch '+old)
  region=src['regions'][layout['root']];dest=dst['regions'][old]
  if region['element_bytes']!=4 or dest['element_bytes']!=4 or region['exponent']!=dest['exponent']:
   raise ValueError('state numeric format differs '+old)
  runs=list(contiguous_runs(layout))
  if sum(n for _,_,n in runs)*4!=dest['bytes']:raise ValueError('incomplete state mapping')
  entry={'source_value':new,'source_root':layout['root'],'source_base':region['base'],
   'shape':layout['shape'],'exponent':region['exponent'],'destination_base':dest['base'],
   'bytes':dest['bytes'],'runs':[{'destination_element':a,'source_element':b,'elements':n} for a,b,n in runs]}
  if old in entries and entries[old]!=entry:raise ValueError('ambiguous state producer '+old)
  entries[old]=entry
 if set(entries)!=runtime_inputs:
  raise ValueError('unbound runtime state inputs '+str(runtime_inputs-set(entries)))
 return {'schema':'native-stage-state-bridge/1','source_plan_sha256':sm['plan_sha256'],
  'destination_plan_sha256':dm['plan_sha256'],'source_graph_sha256':sm['graph_sha256'],
  'destination_graph_sha256':dm['graph_sha256'],'states':entries,
  'execution_scope':'external scene materialization from actual committed DDR only',
  'hardware_transfer_instructions_generated':False,'transition_timing_included':False}
if __name__=='__main__':
 source,dest,sg,sl,dg,out=map(Path,sys.argv[1:])
 result=build(source,dest,*[json.loads(p.read_text()) for p in (sg,sl,dg)])
 out.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'state_inputs':len(result['states']),'bytes':sum(x['bytes'] for x in result['states'].values()),
  'hardware_transfer_instructions_generated':False}))
