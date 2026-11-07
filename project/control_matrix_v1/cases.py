"""Bounded boundary/saturation/length cases for all nine current control targets."""
from pathlib import Path
import copy,sys
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'control_task_compiler_v1'))
from fixtures import example,TARGETS,pack

CASES=('baseline','signed','saturating','boundary','length1','length2','length3','length4','continuous','pm_error0','pm_error1','pm_error2','pm_lost0','pm_lost1','pm_lost2','crc_fault','max_identity')

def cases_for(target):
    return [c for c in CASES if not(c.startswith('length') and target.startswith('five/') and target!='five/J')]

def make(target,case):
    task,inputs=example(target,0);kind=target.split('/')[1]
    if case=='continuous':
        task,inputs=make(target,'saturating');task['name']+='_continuous';return task,inputs
    if case=='signed':
        for item in inputs:
            if item['buffer'].endswith('_a') and kind=='U':item['words']=[pack([-2,2]*4)]
            elif item['buffer'].endswith('_b') and kind in ('F','C'):item['words']=[pack([-1024,1024])]
            elif item['buffer'].endswith('_left'):item['words']=[pack([-120-3*i]*8) for i in range(4)]
            elif item['buffer'].endswith('_right'):item['words']=[pack([30+i]*8) for i in range(4)]
            elif item['buffer'].endswith('_gx'):item['words']=[pack([-10000,10000])]
    elif case=='saturating':
        for item in inputs:
            if item['buffer'].endswith('_a') and kind=='U':item['words']=[pack([300,-300]*4)]
            elif item['buffer'].endswith('_b') and kind=='U':item['words']=[pack([300]*8)]
            elif item['buffer'].endswith('_b') and kind in ('F','C'):item['words']=[pack([30000,-30000])]
            elif item['buffer'].endswith('_gx'):item['words']=[pack([30000,30000])]
            elif item['buffer'].endswith('_gg'):item['words']=[pack([32767,32767])]
            elif item['buffer'].endswith('_left'):item['words']=[pack([32760,-32760]*4)]*4
            elif item['buffer'].endswith('_right'):item['words']=[pack([100,-100]*4)]*4
    elif case=='boundary':
        # Same relative native layout placed against the last S word.
        high=max(b['base_bytes']+16*b['words'] for b in task['buffers']);delta=16384-high
        if kind=='P':delta-=delta%64
        for b in task['buffers']:b['base_bytes']+=delta
    elif case.startswith('length'):
        count=int(case[-1])
        if kind=='J':
            for b in task['buffers']:
                if b['space'].startswith('J_'):b['words']=count
            for item in inputs:
                if item['buffer'].endswith(('_left','_right')):item['words']=item['words'][:count]
            if task['transfers']:
                task['transfers'][0]['words']=count
                dst=task['transfers'][0]['destination'];next(b for b in task['buffers'] if b['name']==dst)['words']=count
        elif task['transfers']:
            e=task['transfers'][0];name='b0_carrier'
            task['buffers'].append(dict(name=name,block=0,base_bytes=70*16,words=count,space='S',format='RAW128',initial=True))
            inputs.append(dict(buffer=name,words=[pack([100+i,-100-i]+[0]*6) for i in range(count)]))
            e.update(source=name,words=count);next(b for b in task['buffers'] if b['name']==e['destination'])['words']=count
        else:
            # Same-type targets have no transport; exercise legal one/four-word feeder/input spans.
            task['call_order']=[1,0] if count==1 else [0,1];task['tokens']=[0,7] if count==1 else [6,4]
    elif case=='max_identity':
        task.update(epoch=255 if kind=='J' else 0xffffffff,generation=0xffffffff,job=0xffffffff,sequence=0xffffffff)
        for t in task['tasks']:
            for op in t['operations']:
                if op['op']=='join':op['tag']=0xffffff
    elif case!='baseline' and not case.startswith(('pm_error','pm_lost','crc_fault')):raise ValueError(case)
    task['name']+='_'+case
    task['image_ids']=[0xfffffffd,0xfffffffe,0xffffffff] if case=='max_identity' else [x+2000+CASES.index(case)*10 for x in task['image_ids']]
    return task,inputs

def partial_producer(target='recovery/F'):
    task,_=make(target,'baseline');e=task['transfers'][0];e['words']=4
    for b in task['buffers']:
        if b['name'] in (e['source'],e['destination']):b['words']=4
    return task
