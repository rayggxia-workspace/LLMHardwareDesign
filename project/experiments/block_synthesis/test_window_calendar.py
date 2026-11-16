from copy import deepcopy
import random
from types import SimpleNamespace
import unittest

from loop_dp import search
from test_loop_dp import binding
from verify_loop_dp import verify
from window_calendar import earliest,insert,evaluate,resources


class TestWindowCalendar(unittest.TestCase):
    def test_integer_interval_insertion_matches_brute_force(self):
        rng=random.Random(22091)
        for _ in range(300):
            bookings={};claims={}
            for resource in ('a','b','c'):
                at=0;intervals=[]
                for _ in range(4):
                    at+=rng.randint(1,6);end=at+rng.randint(1,6)
                    intervals.append((at,end));at=end
                bookings[resource]=tuple(intervals)
                lo=rng.randint(0,10);claims[resource]=(lo,lo+rng.randint(1,8))
            ready=rng.randint(0,20)
            expected=next(at for at in range(ready,100) if all(
                all(not(at+lo<b and a<at+hi) for a,b in bookings[r]) for r,(lo,hi) in claims.items()))
            self.assertEqual(earliest(bookings,claims,ready),expected)
            updated=insert(bookings,claims,expected)
            self.assertTrue(all(all(x[1]<=y[0] for x,y in zip(xs,xs[1:])) for xs in updated.values()))

    def fixture(self):
        h={'resources':{'primary':1,'aux':1},'sites':{'S':{'words':8}},'nets':{},
           'window_calendar':{'kind':'fixed-offset-calendar-v1','resources':['aux']}}
        state=SimpleNamespace(resources={'primary':(20,),'aux':(0,)},cache={},nets=frozenset(),
                              makespan=20,windows={})
        return h,state

    def test_future_booking_keeps_idle_prefix_and_is_pure(self):
        h,s=self.fixture();before=deepcopy(vars(s));a=binding('a','primary',10);a['resources'].append('aux')
        first=evaluate(s,a,h,0)
        self.assertEqual((first['start'],first['end']),(20,30));self.assertEqual(vars(s),before)
        next_state=SimpleNamespace(**{k:first[k] for k in ('resources','cache','nets','makespan','windows')})
        second=evaluate(next_state,binding('b','aux',12),h,0)
        self.assertEqual((second['start'],second['end']),(0,12))
        self.assertEqual(second['windows']['aux'],((0,12),(20,30)))
        busy=deepcopy(next_state);busy.windows={'aux':((0,20),(20,30))}
        delayed=evaluate(busy,binding('b','aux',12),h,0)
        self.assertEqual(delayed['start'],30)

    def test_gap_position_is_future_visible_even_with_same_latest_end(self):
        self.assertEqual(earliest({'x':((0,10),(20,30))},{'x':(0,10)},0),10)
        self.assertEqual(earliest({'x':((10,30),)},{'x':(0,10)},0),0)

    def test_search_and_independent_resource_rejection(self):
        h,_=self.fixture()
        a=binding('a','primary',20);a['resources'].append('aux')
        tasks=[{'id':'a','bindings':[a]},{'id':'b','bindings':[binding('b','aux',5)]}]
        for width in (1,8):
            plan=search(tasks,h,width=width);self.assertTrue(verify(tasks,h,plan)['passed'])
            bad=deepcopy(plan);bad['tasks'][1]['resource_windows']['aux'][0]+=1
            with self.assertRaisesRegex(ValueError,'resource windows differ'):verify(tasks,h,bad)
            bad=deepcopy(plan);bad['tasks'][1]['start']=0;bad['tasks'][1]['end']=5
            bad['tasks'][1]['resource_windows']['aux']=[0,5]
            with self.assertRaisesRegex(ValueError,'window contention'):verify(tasks,h,bad)

    def test_cache_order_and_capacity_fail_closed(self):
        h,_=self.fixture();h['resources']['aux']=2
        with self.assertRaisesRegex(ValueError,'exclusive'):resources(h)
        h['resources']['aux']=1;h['leaf_inventory']={'p':{'macros':['M'],'io_resource':'aux'}}
        with self.assertRaisesRegex(ValueError,'cache decision order'):resources(h)

    def test_noncalendar_multislot_assignment_does_not_shift_unrelated_slot(self):
        h,s=self.fixture();h['resources']['primary']=2;s.resources['primary']=(0,40)
        s.windows={'aux':((0,20),)};b=binding('b','primary',10);b['resources'].append('aux')
        ev=evaluate(s,b,h,0)
        self.assertEqual(ev['start'],20);self.assertEqual(ev['resources']['primary'],(30,40))

    def test_supplied_order_is_shared_and_recomputed_not_a_frozen_schedule(self):
        h,_=self.fixture();tasks=[{'id':'a','bindings':[binding('a','primary',20)]},
            {'id':'b','after':['a'],'bindings':[binding('b','aux',5)]}]
        for width in (1,8):
            p=search(tasks,h,width=width,decision_order=['a','b'])
            self.assertEqual(p['makespan'],25);verify(tasks,h,p)
        for order in (['a'],['a','a'],['b','a']):
            with self.assertRaises(ValueError):search(tasks,h,decision_order=order)

    def test_delayed_compound_internal_events_and_independent_projection(self):
        from test_phased_compounds import example,candidate
        ir=example(columns=9);h=ir['hardware']
        h['window_calendar']={'kind':'fixed-offset-calendar-v1','resources':[
            r for r in h['resources'] if r.startswith('virtual-memory.channel.')]}
        task=next(t for t in ir['tasks'] if t['id']=='v');task['bindings']=[candidate(ir)]
        channel=h['window_calendar']['resources'][0]
        blocker=binding('block',channel,100000);blocker['site']=next(iter(h['sites']));blocker['scratch_words']=0
        tasks=[{'id':'block','bindings':[blocker]}]+ir['tasks']
        order=[t['id'] for t in tasks]
        plan=search(tasks,h,width=8,decision_order=order)
        result=verify(tasks,h,plan)
        self.assertEqual(result['cooperative_phase_audit']['cooperative_compounds'],1)
        self.assertTrue(result['window_audit']['passed'])
        self.assertGreaterEqual(plan['tasks'][-1]['start'],100000)
