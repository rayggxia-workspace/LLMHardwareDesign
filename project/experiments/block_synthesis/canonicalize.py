"""Semantic graph recognition before quantization and native recipe selection.

Patterns use graph edges, verified constants, axes and shapes, never model/node
names. Shared intermediates are boundaries. Recognition does not itself grant
a native format, latency or numerical qualification.
"""
from collections import defaultdict
from copy import deepcopy
import math


def canonicalize(model):
    m=deepcopy(model); trace=[]
    while True:
        producers={n:t for t in m['tasks'] for n in t['outputs']}
        users=defaultdict(set)
        for t in m['tasks']:
            for n in t['inputs']:users[n].add(t['id'])
        def node(name,op):
            t=producers.get(name)
            return t if t and t['op']==op and t.get('domain','')=='' and len(t['outputs'])==1 else None
        def scalar(name,value=None):
            v=m['values'].get(name,{})
            x=v.get('constant')
            while isinstance(x,list) and len(x)==1:x=x[0]
            return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and (value is None or x==value)
        def shape(name):return m['values'].get(name,{}).get('shape')
        def replace(root,members,op,inputs):
            ids={t['id'] for t in members}
            for t in members:
                if t is root:continue
                for n in t['outputs']:
                    if n in m['outputs'] or users[n]-ids:return False
            replacement={**root,'op':op,'inputs':inputs,'attributes':{},
                         'canonical_sources':[t['id'] for t in members]}
            m['tasks']=[replacement if t['id']==root['id'] else t for t in m['tasks']
                        if t['id'] not in ids or t['id']==root['id']]
            trace.append({'op':op,'root':root['id'],'covered':replacement['canonical_sources']})
            return True
        changed=False
        for root in list(m['tasks']):
            if root['op']!='Mul' or root.get('domain','') or root.get('attributes') or len(root['inputs'])!=2:continue
            left,right=root['inputs']
            # SiLU = x * sigmoid(x).
            for x,s in ((left,right),(right,left)):
                sigmoid=node(s,'Sigmoid')
                if sigmoid and not sigmoid.get('attributes') and sigmoid['inputs']==[x] and shape(x)==shape(root['outputs'][0]):
                    if replace(root,[sigmoid,root],'SiLU',[x]):changed=True;break
            if changed:break
            # RMSNorm = gamma * x / sqrt(mean(x^2, last_axis)+epsilon).
            for gamma,normalized in ((left,right),(right,left)):
                norm=node(normalized,'Mul'); direct=node(normalized,'Div')
                if norm and not norm.get('attributes'):
                    options=[(a,node(b,'Div')) for a,b in (norm['inputs'],norm['inputs'][::-1])]
                    options=[(x,d,True) for x,d in options if d and scalar(d['inputs'][0],1)]
                elif direct:
                    options=[(direct['inputs'][0],direct,False)]
                else:continue
                for x,divide,reciprocal in options:
                    if divide.get('attributes'):continue
                    sqrt=node(divide['inputs'][1],'Sqrt')
                    if not sqrt or sqrt.get('attributes'):continue
                    add=node(sqrt['inputs'][0],'Add')
                    if not add or add.get('attributes'):continue
                    for mean_name,eps in (add['inputs'],add['inputs'][::-1]):
                        mean=node(mean_name,'ReduceMean')
                        if not mean or not scalar(eps):continue
                        attributes=mean.get('attributes',{})
                        rank=len(shape(x) or [])
                        if set(attributes)-{'axes','keepdims'} or attributes.get('keepdims',1)!=1 or attributes.get('axes') not in ([-1],[rank-1]):continue
                        square=node(mean['inputs'][0],'Pow')
                        if not square or square.get('attributes') or square['inputs'][0]!=x or not scalar(square['inputs'][1],2):continue
                        if not shape(x) or shape(gamma)!=[shape(x)[-1]] or shape(root['outputs'][0])!=shape(x):continue
                        members=[square,mean,add,sqrt,divide]+([norm] if reciprocal else [])+[root]
                        if replace(root,members,'RMSNorm',[x,gamma,eps]):changed=True;break
                    if changed:break
                if changed:break
            if changed:break
        if not changed:break
    m['canonicalization_trace']=trace
    return m
