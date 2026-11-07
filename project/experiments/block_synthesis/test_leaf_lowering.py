"""Recipe invariants with explicitly artificial timing; not RTL evidence."""
from copy import deepcopy
import json
import unittest

from leaf_catalog import inventory
from leaf_lowering import lower
from run import compile_model
from solver import Unsupported
from numeric import Format, pack, unpack
from frontend import audit
from memory import profile_from_source
from test_memory import SOURCE


def fixture():
    # Tiny numbers make state, spill and interface bugs easy to exercise.
    measurements={}
    def add(kind, ticks=2, **parameters):
        measurements[kind+':'+json.dumps(parameters,sort_keys=True,separators=(',',':'))]=ticks
    for fn in range(4):
        for gated in range(2): add('G',function=fn,gated=gated)
    for op in (0,1,2,7,10,13):
        for shift in range(32): add('E',op=op,shift=shift)
    for columns in (1,2,4,8):
        for k in range(1,33): add('M',columns=columns,k=k)
    for kind in ('M_READ','M_SCALE'): add(kind)
    for mode in range(3):
        for op in range(7):
            for count in range(9): add('N',mode=mode,op=op,count=count)
    for rows in range(1,33): add('R_GDN',rows=rows)
    for kind in ('R_PREDICT','R_UPDATE'):
        for rows in range(1,33): add(kind,rows=rows)
    for kind in ('R_BEGIN','R_ERROR','R_FINISH'): add(kind)
    add('T',words=1,stall=0)
    h={'external':'MEM','sites':{},'resources':{},'services':{},'nets':{},'routes':{},
       'virtual_memory':profile_from_source(SOURCE)}
    groups={name:{'site':name+'.S','words':1024,'io_resource':name+'.IO',
                  'io_read_ticks':2,'io_write_ticks':2,'memory_group':i,'macros':macros}
            for i,(name,macros) in enumerate((('P0',['M','G']),('U0',['N','E']),
                                             ('C0',['R','G','E']),('F0',['G','E']),('J0',['E','T'])))}
    return inventory(h,{'measurements':measurements,'scope':'unit-test fixture only'},groups)


def mixed_model():
    f={'bits':16,'exponent':-10,'lanes':2}
    values={n:{'shape':dims,'format':deepcopy(f)} for n,dims in {
        'x':[1,8],'gamma':[8],'normalized':[1,8],'w':[8,4],
        'projected':[1,4],'activated':[1,4],'residual':[1,4],
        'sum':[1,4],'out':[1,4]}.items()}
    values['epsilon']={'shape':[],'format':{'bits':32,'exponent':0,'lanes':1}}
    ops=[('norm','RMSNorm',['x','gamma','epsilon'],['normalized']),
         ('project','MatMul',['normalized','w'],['projected']),
         ('act','SiLU',['projected'],['activated']),
         ('residual','Add',['activated','residual'],['sum']),
         ('finish','Handoff',['sum'],['out'])]
    return {'tasks':[{'id':tid,'op':op,'numeric':'INT16','inputs':ins,'outputs':outs} for tid,op,ins,outs in ops],
            'values':values,'outputs':['out'],'weights':['w'],'source':'native integration fixture; not an LLM benchmark'}


class TestLeafLowering(unittest.TestCase):
    def test_mixed_five_class_inventory_compiles_without_preconnections(self):
        model=mixed_model(); hardware=fixture()
        before=deepcopy((model,hardware))
        result=compile_model(model,hardware,seconds=1,rounds=0,cover_limit=1)
        self.assertEqual(result['status'],'planned')
        self.assertTrue(result['verification']['passed'])
        self.assertEqual((model,hardware),before)
        self.assertFalse(any(n.get('fixed') for n in result['resolved_hardware']['nets'].values()))
        programs=[r for r in result['outputs']['program_ir']['requests'] if r['kind']=='service']
        self.assertTrue(all(r['native_program'] and r['owner'] for r in programs))
        self.assertTrue(any(any(p.get('op')==13 for p in r['native_program']) for r in programs))
        self.assertTrue(result['outputs']['program_ir']['state_groups'])

    def test_k_partitions_never_round_intermediate_and_never_migrate(self):
        graph,h=lower(mixed_model(),fixture())
        groups=[g for g in graph['state_groups'] if g['id'].startswith('project:')]
        self.assertEqual(len(groups),2)
        for group in groups:
            tasks=[t for t in graph['tasks'] if t['id'] in group['tasks']]
            self.assertTrue(all(not t['outputs'] for t in tasks[:-1]))
            self.assertEqual(sum(t['attributes']['last'] for t in tasks),1)
            for t in tasks[:-1]:
                self.assertTrue(all(p['command']!='ReadFinal' for p in h['services'][t['alternatives'][0]]['native_program']))

    def test_native_layout_is_not_reinterpreted_as_float_or_unsigned_math(self):
        m=mixed_model();m['values']['w']['format']['unsigned']=True
        with self.assertRaises(Unsupported):lower(m,fixture())
        graph,h=lower(mixed_model(),fixture())
        reads=[p for t in graph['tasks'] for p in h['services'][t['alternatives'][0]]['native_program'] if p.get('command')=='ReadFinal']
        self.assertTrue(reads)
        self.assertTrue(all(p['width']==16 and p['pack16'] is False for p in reads))

    def test_audit_reports_actual_recipe_coverage_and_format_failure(self):
        m=mixed_model(); result=audit(m,fixture())
        self.assertEqual(result['status'],'recipes_lowered')
        self.assertTrue(all(t['native_tasks'] for t in result['nodes']))
        del m['values']['x']['format']
        result=audit(m,fixture())
        self.assertEqual(result['status'],'blocked_lowering')
        self.assertIn('format missing',result['first_uncovered_reason'])
        self.assertIn('not asserted',result['hardware_missing'])

    def test_capacity_and_instance_names_are_data_not_algorithm(self):
        model=mixed_model(); h=fixture()
        for site in h['sites'].values(): site['words']=12
        for meta in h['leaf_inventory'].values(): meta['words']=12
        result=compile_model(model,h,seconds=1,rounds=0,cover_limit=1)
        self.assertEqual(result['status'],'planned')
        self.assertTrue(result['verification']['passed'])
        # The full normalized row and all M weights need not fit together.
        self.assertTrue(result['plan']['moves'])

    def test_runtime_layout_and_unknown_formats_do_not_get_free_host_work(self):
        m=mixed_model(); m['values']['activated']['format']['lanes']=4
        with self.assertRaises(Unsupported): lower(m,fixture())
        m=mixed_model(); del m['values']['x']['format']
        with self.assertRaisesRegex(Unsupported,'format missing'): lower(m,fixture())
        m=mixed_model(); m['weights']=[]
        with self.assertRaisesRegex(Unsupported,'gather recipe'): lower(m,fixture())

    def test_gdn_uses_physical_r256_and_explicit_unsigned_parameters(self):
        f={'bits':32,'exponent':-16,'lanes':2}
        values={n:{'shape':dims,'format':deepcopy(f)} for n,dims in
                {'old':[32,2],'x':[2],'next':[32,2],'y':[2]}.items()}
        values.update({n:{'shape':[32],'format':{'bits':16,'exponent':-14,'lanes':8}} for n in ('key','query')})
        values['params']={'shape':[2],'format':{'bits':32,'exponent':-31,'lanes':2,'unsigned':True}}
        m={'values':values,'tasks':[{'id':'r','op':'GDNUpdate','numeric':'native',
            'inputs':['old','key','query','x','params'],'outputs':['next','y']}],'outputs':['next','y']}
        graph,h=lower(m,fixture())
        self.assertEqual(len(graph['tasks']),5)
        self.assertEqual({h['services'][s]['state_resource'] for s in graph['tasks'][0]['alternatives']},{'C0.R.context'})
        unsigned=Format(32,-31,2,True)
        self.assertEqual(unpack(pack([1<<31,1<<30],unsigned),unsigned,2),[1<<31,1<<30])
        values['old']['shape']=[128,2]; values['next']['shape']=[128,2]
        values['key']['shape']=values['query']['shape']=[128]
        graph,h=lower(m,fixture())
        self.assertEqual(len(graph['tasks']),11)
        self.assertEqual(len(graph['state_groups']),1)
        self.assertEqual(len(graph['state_groups'][0]['tasks']),11)
        self.assertEqual(len([t for t in graph['tasks'] if t['attributes']['command']=='R_PREDICT']),4)


if __name__=='__main__': unittest.main()
