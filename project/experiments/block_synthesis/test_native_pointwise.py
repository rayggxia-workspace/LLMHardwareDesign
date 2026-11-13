from collections import Counter
from copy import deepcopy
import json
import random
import unittest
from unittest.mock import patch

from native_pointwise import counts,execute,lower,regions
from streaming_ir import counts as old_counts,native_operand_components,primitive_body,templates


def node(name,op,args,shape=(3,),bits=32,**attributes):
    return {'id':name,'kernel':'test','op':op,'inputs':args,'shape':list(shape),
            'bits':bits,'exponent':0,'attributes':attributes}


def signed32(word):
    value=word&0xffffffff
    return value-(1<<32) if value&(1<<31) else value


def reference(program,initial,index):
    # Whole-instruction math independent of decomposition/native IR helpers.
    from layout_views import broadcast_index
    values=dict(initial);shapes={k:v['shape'] for k,v in program['initial_formats'].items()};out={}
    for n in program['instructions']:
        a=n['attributes'];shape=n['shape'];args=[]
        for name in n['inputs']:
            at=broadcast_index(index,shape,shapes[name]);args.append(values[name][at])
        if n['op']=='Add':value=sum(x*s for x,s in zip(args,a['signs']))
        elif n['op']=='Product':value=args[0]*args[1]
        elif n['op']=='Convert':value=args[0]
        else:raise ValueError('reference only called for pointwise test programs')
        shift=a.get('shift',0)
        if shift>0:
            q,r=divmod(value,1<<shift)
            value=q+int(2*r>1<<shift or (2*r==1<<shift and q%2))
        elif shift<0:value*=1<<-shift
        bits=n['bits'];value=max(-(1<<(bits-1)),min((1<<(bits-1))-1,value))
        values[n['id']]=[value]*(__import__('math').prod(shape));shapes[n['id']]=shape;out[n['id']]=value
    return out


class TestNativePointwise(unittest.TestCase):
    def program(self):
        ns=[node('a','Add',['x','y','x'],signs=[1,-1,1]),
            node('p','Product',['a','y'],shift=29),
            node('s','Convert',['p'],bits=16,shift=11),
            node('u','Product',['s','one'],shift=-1),
            node('z','Add',['u','a'],signs=[-1,1])]
        return {'instructions':ns,'outputs':{'out':'z'},'initial_formats':{
            'x':{'bits':32,'shape':[3]},'y':{'bits':32,'shape':[3]},
            'one':{'bits':16,'shape':[],'literal':1}}}

    def test_native_words_against_independent_full_integer_and_broadcast(self):
        rng=random.Random(220140);p=self.program();names=[n['id'] for n in p['instructions']]
        for trial in range(80):
            initial={name:[rng.randrange(-(1<<31),1<<31) for _ in range(3)] for name in ('x','y')}
            if trial<4:initial['x']=[(-2147483648,2147483647,-32769,32768)[trial]]*3
            initial['one']=[1]
            for at in range(3):
                g=json.loads(json.dumps(lower(p,names,at)))
                records=execute(g,{(name,i):int(x) for name,v in initial.items() for i,x in enumerate(v)})
                self.assertEqual({name:signed32(records[key]) for name,key in g['primitive_outputs'].items()},reference(p,initial,at))
                self.assertEqual(set(g['live_out']),{'z'})

    def test_original_native_command_and_operand_work_conserved(self):
        p=self.program();g=lower(p,[n['id'] for n in p['instructions']]);original=Counter()
        with patch('streaming_ir.duration',return_value=1):library=templates({})
        c=native_operand_components(p)
        for n in p['instructions']:
            body,_=primitive_body(n,c[n['id']]);original.update(old_counts(body,library))
        self.assertEqual(counts(g),{k:v//3 for k,v in original.items() if k.endswith((':read',':write',':commands')) and v})
        # Repeated x uses still prepare separately: no hidden CSE or hoist.
        self.assertGreater(sum(n['kind']=='E' for n in g['operations']),2)

    def test_convex_regions_and_external_fanout_lifetime(self):
        p=self.program();p['instructions'].insert(2,node('barrier','NExp',['a']))
        self.assertEqual(regions(p),[['a','p'],['s','u','z']])
        g=lower(p,['a','p']);self.assertEqual(set(g['live_out']),{'a','p'})
        with self.assertRaisesRegex(ValueError,'crosses'):lower(p,['a','p','s'])
        p=self.program();p['instructions'].insert(1,node('scalar','Constant',[],shape=(),raw=9))
        self.assertEqual(len(regions(p)),1)
        p['instructions'][-1]['shape']=[1,3]
        self.assertEqual(len(regions(p)),2)

    def test_rejects_overflow_order_missing_identity_and_invalid_encoding(self):
        p=self.program();names=[n['id'] for n in p['instructions']]
        for ids,index in ((names,-1),(names,3),(list(reversed(names)),0),(names+['a'],0)):
            with self.assertRaises(ValueError):lower(p,ids,index)
        p['instructions'][0]['attributes']['signs'][0]=0
        with self.assertRaisesRegex(ValueError,'scale'):lower(p,names)
        p=self.program();p['instructions'][0]['inputs'][0]='z'
        with self.assertRaisesRegex(ValueError,'defined'):lower(p,names)
        p=self.program();p['instructions'][1]['attributes']['shift']=-20
        with self.assertRaisesRegex(ValueError,'scale'):lower(p,names)
        p=self.program();g=lower(p,names)
        with self.assertRaisesRegex(ValueError,'S32'):execute(g,{('x',0):1<<31,('y',0):0})
        bad=deepcopy(g);bad['operations'][0]['terms'][0]['coefficient']=1<<60
        with self.assertRaisesRegex(ValueError,'S64'):execute(bad,{('x',0):2147483647,('y',0):1})


if __name__=='__main__':unittest.main()
