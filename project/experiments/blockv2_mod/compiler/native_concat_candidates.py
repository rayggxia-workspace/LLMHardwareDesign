"""Concat is explicit data movement on a selected U, never a free alias."""
from native_backend import NativeBackend
from native_p_candidates import _storage
from native_transfer_program import load,store
def candidate(task,*,group,regions,profile):
    if task['kind']!='Concat':raise ValueError('not a concat recipe')
    backend=NativeBackend(profile);calls=[]
    for tile in task['tiles']:
        read,=tile['read'];write=tile['write']
        src=regions[read['root']];dst=regions[write['value']]
        _storage(src,read['root'],-16);_storage(dst,write['value'],-16)
        calls.extend(load(read,src,group=group,sram_word=0,backend=backend))
        calls.extend(store(write,dst,group=group,sram_word=0,backend=backend))
    for i,c in enumerate(calls):c['index']=i;c['after']=[] if i==0 else [i-1]
    return {'source_task':task['id'],'binding':task['id']+'@'+group,'group':group,
            'calls':calls,'srams':{group+'.S':{'word':0,'words':512}},
            'completion':'last_destination_DDR_commit'}
