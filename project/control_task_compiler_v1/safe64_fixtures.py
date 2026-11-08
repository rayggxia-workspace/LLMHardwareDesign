"""Supervised two-endpoint tasks including U round-trip echo and J->P."""
from main64_fixtures import example as main_example,PAIRS
from fixtures import example as legacy_example

def example(pair,variant=0):
    if pair==('J','P'):
        task,inputs=legacy_example('recovery/J',variant);task['call_order']=[0,1]
    else:task,inputs=main_example(pair,variant)
    task['schema']='safe64-native-tasks/1';task['target']='safe64/'+'/'.join(pair);task['name']='safe64_'+''.join(pair).lower()+'_'+str(variant)
    if pair==('U','U'):
        offset=(0,80,200)[variant]
        for block in (0,1):
            task['buffers'].append(dict(name=f'b{block}_receive',block=block,base_bytes=(60+offset)*16,words=2,space='S',format='RAW128',initial=False))
        task['transfers']=[dict(source=f'b{b}_out',destination=f'b{1-b}_receive',words=1,format='RAW128') for b in (0,1)]
    return task,inputs

