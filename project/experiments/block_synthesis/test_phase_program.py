from collections import Counter
import random
import unittest

from phase_program import simulate, native_program, cached_dot_program, aggregate
from phase_trace import reference, phases
from test_dot_cache import example
from test_column_shards import fixture, compound, initial
from transition import evaluate_transition


def expand(node):
    if 'sequence' in node:return [p for n in node['sequence'] for p in expand(n)]
    if 'repeat' in node:return expand(node['body'])*node['repeat']
    return [node] if node['ticks'] else []


class TestPhaseProgram(unittest.TestCase):
    def test_random_nested_loops_match_full_independent_event_execution(self):
        for seed in range(200):
            rng = random.Random(seed);channels = rng.randint(1,3)
            def tree(depth):
                if depth == 0:return {'channel':rng.randrange(-1,channels),'ticks':rng.randint(1,7),'kind':str(rng.randint(0,3))}
                if rng.randrange(2):return {'repeat':rng.randint(1,8),'body':tree(depth-1)}
                return {'sequence':[tree(depth-1) for _ in range(rng.randint(1,3))]}
            programs = [tree(3) for _ in range(rng.randint(1,4))]
            workers = [expand(p) for p in programs]
            expected = reference(workers,channels)
            actual = simulate(programs,channels)
            plain = simulate(programs,channels,fast_forward=False)
            self.assertEqual(actual['makespan'],expected['makespan'],seed)
            self.assertEqual(actual['worker_phase_counts'],list(map(len,workers)),seed)
            self.assertEqual(actual['worker_completion'],plain['worker_completion'],seed)
            self.assertEqual(actual['phase_counts'],dict(Counter(p['kind'] for w in workers for p in w)),seed)

    def test_trillion_repeats_do_not_drop_work_or_boundary_tail(self):
        n = 10**12
        body = {'repeat':n,'body':{'sequence':[
            {'channel':0,'ticks':3,'kind':'load'}, {'channel':0,'ticks':8,'kind':'store'}]}}
        result = simulate([body,body],1,event_limit=1000)
        self.assertEqual(result['makespan'],22*n)
        self.assertEqual(result['worker_phase_counts'],[2*n,2*n])
        self.assertEqual(result['phase_counts'],{'load':2*n,'store':2*n})
        self.assertLess(result['executed_events'],1000)
        self.assertGreater(result['skipped_events'],10**12)

    def test_distinct_channels_and_nested_boundary_resets(self):
        programs = [{'repeat':9,'body':{'sequence':[
            {'repeat':31,'body':{'sequence':[{'channel':i,'ticks':3,'kind':'load'},
                                           {'channel':-1,'ticks':7,'kind':'execute'}]}},
            {'channel':-1,'ticks':11,'kind':'tail'}]}} for i in range(2)]
        result = simulate(programs,2)
        self.assertEqual(result['makespan'],9*(31*10+11))
        self.assertEqual(result['worker_phase_counts'],[9*63]*2)
        self.assertGreater(result['fast_forward_jumps'],0)

    def test_inner_fast_forward_preserves_outer_cycle_witnesses(self):
        def worker(outputs,k):
            term = {'sequence':[{'channel':0,'ticks':3,'kind':'load'},
                                {'channel':-1,'ticks':7,'kind':'execute'}]}
            return {'repeat':outputs,'body':{'sequence':[
                {'repeat':k,'body':term}, {'channel':0,'ticks':2,'kind':'store'}]}}
        small = [worker(30,35)]*2
        expected = reference([expand(p) for p in small],1)
        self.assertEqual(simulate(small,1)['makespan'],expected['makespan'])
        large = [worker(10**8,2048)]*2
        result = simulate(large,1,event_limit=10000)
        self.assertEqual(result['worker_phase_counts'],[10**8*(4096+1)]*2)
        self.assertLess(result['executed_events'],10000)

    def test_channel_disjoint_components_preserve_coprime_event_timing(self):
        programs = []
        for channel,compute,repeats in ((0,7,127),(0,11,163),(1,13,179)):
            programs.append({'repeat':repeats,'body':{'sequence':[
                {'channel':channel,'ticks':3,'kind':'load'},
                {'channel':-1,'ticks':compute,'kind':'compute'}]}})
        actual = simulate(programs,2)
        joint = simulate(programs,2,decompose=False)
        self.assertEqual(actual['worker_completion'],joint['worker_completion'])
        self.assertEqual(actual['phase_counts'],joint['phase_counts'])
        self.assertEqual(len(actual['independent_components']),2)
        self.assertEqual(actual['makespan'],reference([expand(p) for p in programs],2)['makespan'])

    def test_unequal_nested_loops_do_not_extrapolate_across_inner_resets(self):
        for seed in range(40):
            rng = random.Random(3000+seed)
            def worker():
                return {'repeat':rng.randint(15,35),'body':{'sequence':[
                    {'repeat':rng.randint(12,31),'body':{'sequence':[
                        {'channel':0,'ticks':rng.randint(1,7),'kind':'load'},
                        {'channel':-1,'ticks':rng.randint(1,13),'kind':'execute'}]}},
                    {'channel':0,'ticks':rng.randint(1,11),'kind':'store'}]}}
            programs = [worker(),worker(),worker()]
            actual = simulate(programs,1,boundary=1)
            expected = reference([expand(p) for p in programs],1)
            self.assertEqual(actual['makespan'],expected['makespan'],seed)
            self.assertEqual(actual['phase_counts'],dict(Counter(p['kind'] for w in programs for p in expand(w))),seed)

    def test_native_lowering_matches_previous_expanded_trace(self):
        ir = example();h = ir['hardware'];meta = h['leaf_inventory']['matrix']
        body = {'sequence':[{'repeat':17,'body':{'call':'partial'}},{'call':'dot_final'}]}
        program = native_program(body,ir['native_templates'],meta,h['virtual_memory'])
        expanded = phases(body,ir['native_templates'],meta,h['virtual_memory'])
        self.assertEqual(expand(program),expanded)
        result = simulate([program,program],2)
        self.assertEqual(result['makespan'],reference([expanded,expanded],2)['makespan'])

    def test_invalid_programs_and_incomplete_runs_fail(self):
        for node in ({'repeat':True,'body':{'channel':0,'ticks':1}}, {'channel':2,'ticks':1},
                     {'channel':0,'ticks':-1}):
            with self.assertRaises(ValueError):simulate([node],1)
        with self.assertRaisesRegex(ValueError,'event limit'):
            simulate([{'repeat':100,'body':{'channel':0,'ticks':1}}],1,fast_forward=False,event_limit=4)
        self.assertEqual(simulate([{'repeat':10**12,'body':{'sequence':[]}}],1)['makespan'],0)

    def test_cached_program_conserves_current_selected_cost_and_traffic(self):
        for shared in (False,True):
            ir = fixture(shared=shared);b = compound(ir);h = ir['hardware']
            ev = evaluate_transition(initial(ir),b,h,0,retention=('preserve','preserve'))
            programs = []
            for child,row in zip(b['parallel_shards']['children'],ev['details']['services']):
                binding = child['binding'];c = binding['read_cache']
                meta = {**h['leaf_inventory'][binding['macro_binding']['M']],
                        'words':h['sites'][c['site']]['words']}
                program = cached_dot_program(binding,row,ir['native_templates'],meta,h['virtual_memory'])
                ticks,counts = aggregate(program)
                self.assertEqual(ticks,row['end']-row['start'])
                self.assertEqual(counts['external-load-until-S-commit'],row['evaluation']['external_read_words'])
                self.assertEqual(counts['external-store-until-ACK'],binding['external_write_words'])
                programs.append(program)
            actual = simulate(programs,h['virtual_memory']['channels'])
            expected = reference([expand(p) for p in programs],h['virtual_memory']['channels'])
            self.assertEqual(actual['makespan'],expected['makespan'])
            self.assertLessEqual(actual['makespan'],ev['duration'])


if __name__ == '__main__':unittest.main()
