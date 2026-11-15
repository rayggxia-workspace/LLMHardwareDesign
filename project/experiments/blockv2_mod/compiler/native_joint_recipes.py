"""Expose existing native commit units; no arithmetic or hardware is invented."""
from copy import deepcopy

def cut_access(access,first,count):
 result={**access,'elements':count,'segments':[]}
 for segment in access['segments']:
  lo=max(first,segment['destination_element']);hi=min(first+count,segment['destination_element']+segment['elements'])
  if hi>lo:result['segments'].append({'destination_element':lo-first,
   'source_element':segment['source_element']+lo-segment['destination_element'],'elements':hi-lo})
 if sum(s['elements'] for s in result['segments'])!=count:raise ValueError('range read coverage')
 return result

def lower(recipes):
 result=deepcopy(recipes);tasks=[]
 for task in result['tasks']:
  if task['kind']=='Add':
   tiles=[]
   for tile in task['tiles']:
    n=tile['write']['elements']
    if n%128:raise ValueError('native Add range alignment')
    for first in range(0,n,128):
     tiles.append({**tile,'read':[cut_access(a,first,128) for a in tile['read']],
      'write':{**tile['write'],'element_offset':tile['write']['element_offset']+first,'elements':128}})
   task['tiles']=tiles
  if task['kind']!='SwiGLUFFN':tasks.append(task);continue
  name=task['id'];names={p:name+':native:'+p for p in ('gate','up','mid')}
  ids={p:name+'::stage::'+p for p in ('gate','up','gated')}
  projections={}
  for part in ('gate','up','down'):
   stage={'id':name if part=='down' else ids[part],'kind':'MatMul',
    'after':[ids['gated']] if part=='down' else list(task['after']),
    'storage_parent':name,'source_operator':name,'tiles':[]}
   for row,t in enumerate(task['tiles']):
    hidden,mid=t['hidden'],t['intermediate'];k,n=(mid,hidden) if part=='down' else (hidden,mid)
    source=t['read'][0] if part!='down' else {'value':names['mid'],'root':names['mid'],'elements':mid,
     'segments':[{'destination_element':0,'source_element':row*mid,'elements':mid}]}
    value=t['write']['value'] if part=='down' else names[part]
    offset=t['write']['element_offset'] if part=='down' else row*mid
    for first in range(0,n,128):
     stage['tiles'].append({'read':[source],'weight':{'value':t['weights'][{'gate':0,'up':1,'down':2}[part]],
      'k':k,'first_column':first,'columns':128},'write':{'value':value,'element_offset':offset+first,'elements':128}})
   projections[part]=stage
  gated={'id':ids['gated'],'kind':'Gated','source_operator':name,'after':[ids['gate'],ids['up']],'tiles':[]}
  for row,t in enumerate(task['tiles']):
   for first in range(0,t['intermediate'],128):
    offset=row*t['intermediate']+first
    gated['tiles'].append({'read':[{'value':names[p],'root':names[p],'elements':128,
     'segments':[{'destination_element':0,'source_element':offset,'elements':128}]} for p in ('gate','up')],
     'write':{'value':names['mid'],'element_offset':offset,'elements':128}})
  tasks.extend([projections['gate'],projections['up'],gated,projections['down']])
 result['tasks']=tasks;return result
