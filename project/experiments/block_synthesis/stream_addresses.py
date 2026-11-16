"""Scalar record address programs for streaming kernels and tensor views.

Resolved integer offsets are in 128-bit records. No host transpose/packing is
performed. Each generated access can traverse any number of read-only views.
"""
import math
from layout_views import broadcast_index,coordinates,flat,view


class Addresses:
    def __init__(self,model,regions):
        self.values=model['values'];self.regions=regions;self.alias={}
        for t in model.get('offline_weight_recipes',[]):self.alias[t['outputs'][0]]=view(t,self.values)
        for t in model['tasks']:
            if t['op'] in ('Reshape','Transpose','Slice','Unsqueeze','Squeeze','Expand','Identity'):
                self.alias[t['outputs'][0]]=view(t,self.values)

    def locate(self,name,index):
        visited=set()
        while name in self.alias:
            if name in visited:raise ValueError('cyclic address view')
            visited.add(name);name,index=self.alias[name](index)
        if not 0<=index<math.prod(self.values[name]['shape']):raise ValueError('scalar address outside tensor')
        return self.regions[name]['address_words']+index

    def element(self,name,output_shape,index):
        return self.locate(name,broadcast_index(index,output_shape,self.values[name]['shape']))

    def dot(self,task,output_index,k):
        a,b=task['inputs'];ashape=self.values[a]['shape'];bshape=self.values[b]['shape']
        if len(ashape)<2 or len(bshape)<2 or ashape[-1]!=bshape[-2]:raise ValueError('matrix address rank/K')
        outshape=self.values[task['outputs'][0]]['shape'];coord=coordinates(output_index,outshape)
        if not 0<=k<ashape[-1]:raise ValueError('dot address K outside extent')
        batchshape=outshape[:-2];batch=flat(coord[:-2],batchshape)
        ap=broadcast_index(batch,batchshape,ashape[:-2]) if ashape[:-2] else 0
        bp=broadcast_index(batch,batchshape,bshape[:-2]) if bshape[:-2] else 0
        ai=(ap*ashape[-2]+coord[-2])*ashape[-1]+k
        bi=(bp*bshape[-2]+k)*bshape[-1]+coord[-1]
        return self.locate(a,ai),self.locate(b,bi)

    def gather(self,task,output_index,indices):
        import numpy as np
        source,index=task['inputs'];shape=self.values[source]['shape'];ishape=self.values[index]['shape']
        if tuple(np.shape(indices))!=tuple(ishape) or np.asarray(indices).dtype.kind not in 'iu':
            raise ValueError('Gather index shape/type')
        axis=task.get('attributes',{}).get('axis',0)%len(shape)
        coord=coordinates(output_index,self.values[task['outputs'][0]]['shape'])
        ic=coord[axis:axis+len(ishape)];value=int(np.asarray(indices)[tuple(ic)])
        if not -shape[axis]<=value<shape[axis]:raise ValueError('Gather index outside source')
        if value<0:value+=shape[axis]
        sc=coord[:axis]+[value]+coord[axis+len(ishape):]
        return self.locate(source,flat(sc,shape)),self.locate(index,flat(ic,ishape))


def check_program_addresses(model,regions):
    """Boundary/stride samples, not a substitute for numerical graph replay."""
    a=Addresses(model,regions);samples=0
    for t in model['tasks']:
        out=t['outputs'][0];n=math.prod(model['values'][out]['shape'])
        for i in sorted({0,n//2,n-1}):
            if t['op']=='MatMul':
                length=model['values'][t['inputs'][0]]['shape'][-1]
                for k in sorted({0,length//2,length-1}):a.dot(t,i,k);samples+=2
            elif t['op'] in ('Add','Sub','Mul','Neg','SiLU'):
                for name in t['inputs']:
                    a.element(name,model['values'][out]['shape'],i);samples+=1
            else:a.locate(out,i);samples+=1
    return {'passed':True,'sampled_record_addresses':samples,
        'scope':'shape, broadcasting, composed view and stride boundary checks; scalar records avoid free packing'}


def check_primitive_addresses(model,program,regions,primitive_regions,samples=()):
    values={k:dict(v) for k,v in model['values'].items()};views=[]
    for node in program['instructions']:
        values[node['id']]={'shape':node['shape']}
        if node['op']=='Constant':values[node['id']]['constant']=node['attributes']['raw']
        if node['op']=='View':views.append({'op':node['attributes']['view_op'],'inputs':node['inputs'],
            'outputs':[node['id']],'attributes':node['attributes']['source_attributes']})
        if node['op']=='Mask':
            source=node['inputs'][0]
            views.append({'op':'Identity','inputs':[source],'outputs':[node['id']]})
    for name,p in program.get('predicates',{}).items():values[name]={'shape':p['shape']}
    combined={'values':values,'tasks':views,'offline_weight_recipes':model.get('offline_weight_recipes',[])}
    a=Addresses(combined,{**regions,**primitive_regions});count=0
    for node in program['instructions']:
        op=node['op'];shape=node['shape'];n=math.prod(shape);attrs=node['attributes']
        for i in {0,n//2,n-1}:
            if op=='Dot':
                t={'inputs':node['inputs'],'outputs':[node['id']]}
                for k in {0,attrs['length']//2,attrs['length']-1}:a.dot(t,i,k);count+=2
            elif op=='Gather' and node['inputs'][1]=='input_ids':
                t={'inputs':node['inputs'],'outputs':[node['id']],'attributes':attrs}
                for ids in samples:a.gather(t,i,ids);count+=2
            elif op in ('Sum','SquareSum','Max','NFactor'):
                for k in {0,attrs['length']//2,attrs['length']-1}:
                    a.locate(node['inputs'][0],i*attrs['length']+k);count+=1
            elif op not in ('Constant','View','Mask','Gather','Concat'):
                for name in node['inputs']:a.element(name,shape,i);count+=1
            if attrs.get('predicate_source'):
                a.element(attrs['predicate_source'],shape,i);count+=1
    return {'passed':True,'sampled_record_addresses':count,'scope':'emitted primitive operand and predicate address programs'}
