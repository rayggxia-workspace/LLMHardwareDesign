from copy import deepcopy
import unittest
from canonicalize import canonicalize


def norm_graph():
    rows=[('sq','Pow',['x','two']),('mean','ReduceMean',['sq']),('eps','Add',['mean','epsilon']),
          ('sqrt','Sqrt',['eps']),('inv','Div',['one','sqrt']),('norm','Mul',['x','inv']),
          ('y','Mul',['gamma','norm'])]
    values={n:{'shape':[2,8]} for n in ('x','sq','norm','y')}
    values.update({n:{'shape':[2,1]} for n in ('mean','eps','sqrt','inv')})
    values['gamma']={'shape':[8]}
    values.update({n:{'shape':[],'constant':v} for n,v in [('two',2.),('one',1.),('epsilon',1e-6)]})
    tasks=[{'id':n,'op':op,'inputs':ins,'outputs':[n],
            'attributes':{'axes':[-1],'keepdims':1} if op=='ReduceMean' else {}} for n,op,ins in rows]
    return {'tasks':tasks,'values':values,'outputs':['y'],'weights':['gamma']}


class TestCanonicalize(unittest.TestCase):
    def test_rmsnorm_recognizes_semantics_without_node_names(self):
        m=norm_graph();before=deepcopy(m);result=canonicalize(m)
        self.assertEqual(m,before)
        self.assertEqual(len(result['tasks']),1)
        self.assertEqual(result['tasks'][0]['inputs'],['x','gamma','epsilon'])
        self.assertEqual(result['tasks'][0]['op'],'RMSNorm')
        self.assertEqual(len(result['canonicalization_trace'][0]['covered']),7)

    def test_shared_intermediate_wrong_axes_or_constants_do_not_fuse(self):
        m=norm_graph();m['outputs'].append('sq')
        self.assertEqual(len(canonicalize(m)['tasks']),7)
        m=norm_graph();m['tasks'][1]['attributes']['axes']=[0]
        self.assertEqual(len(canonicalize(m)['tasks']),7)
        for n,v in [('two',3.),('one',2.)]:
            m=norm_graph();m['values'][n]['constant']=v
            self.assertEqual(len(canonicalize(m)['tasks']),7)

    def test_exact_scalar_graph_reference(self):
        import numpy as np
        m=norm_graph();canonical=canonicalize(m)
        data={'x':np.arange(-8,8).reshape(2,8)*.125,'gamma':np.arange(8)*.25+1,
              'two':2.,'epsilon':1e-6,'one':1.}
        for t in m['tasks']:
            args=[data[n] for n in t['inputs']]
            value={'Pow':lambda:args[0]**args[1],
                   'ReduceMean':lambda:np.mean(args[0],axis=-1,keepdims=True),
                   'Add':lambda:args[0]+args[1],'Sqrt':lambda:np.sqrt(args[0]),
                   'Div':lambda:args[0]/args[1],'Mul':lambda:args[0]*args[1]}[t['op']]()
            data[t['outputs'][0]]=value
        x,gamma,epsilon=[data[n] for n in canonical['tasks'][0]['inputs']]
        expected=gamma*x/np.sqrt(np.mean(x*x,axis=-1,keepdims=True)+epsilon)
        np.testing.assert_allclose(data['y'],expected,atol=1e-15)

    def test_silu_shared_sigmoid_and_custom_domain(self):
        m={'tasks':[{'id':'s','op':'Sigmoid','inputs':['x'],'outputs':['s']},
            {'id':'out','op':'Mul','inputs':['s','x'],'outputs':['out']}],
            'values':{n:{'shape':[2,8]} for n in ('x','s','out')},'outputs':['out']}
        self.assertEqual(canonicalize(m)['tasks'][0]['op'],'SiLU')
        m['outputs'].append('s');self.assertEqual(len(canonicalize(m)['tasks']),2)
        m['outputs']=['out'];m['tasks'][1]['domain']='user'
        self.assertEqual(len(canonicalize(m)['tasks']),2)


if __name__=='__main__':unittest.main()
