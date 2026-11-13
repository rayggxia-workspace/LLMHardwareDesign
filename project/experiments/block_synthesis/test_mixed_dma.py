from copy import deepcopy
import unittest

from cover_frontier import search
from dma_read import Profile, Read
from event_execution import Model
from event_replay import Operation, Phase, replay_branch
from event_replay_plan import Decision, delivery_at
from test_event_execution import binding, stage, task
from verify_cover_frontier import verify


def mixed_problem():
    def route(src, dst, client):
        return {'src': src, 'dst': dst, 'claims': {}, 'setup': 0, 'bytes_per_tick': 64,
                'typed_dma': {'client': client, 'record_beats': 2},
                'phases': {'issue': {'ticks': 1, 'claims': {}}, 'ack': {'ticks': 2, 'claims': {}},
                           'hold_claims': {}}}

    sites = {'P0': {'words': 64, 'bytes': 1024}, 'P1': {'words': 64, 'bytes': 1024}}
    hw = {'sites': sites, 'resources': {}, 'nets': {}, 'event_model': {
        'kind': 'qualified-event-model-v1', 'timing': 'replay',
        'typed_dma': {'return_latency': [7, 8], 'mixed': {'queue': 4, 'write_latency': 9},
                      'addresses': {'kv0': 0x10000, 'weight': 0x20000}},
        'windows': {name: {'site': site, 'offset': offset, 'bytes': size} for name, site, offset, size in
                    [('kv-slot', 'P0', 0, 128), ('next-kv', 'P1', 0, 128), ('weight-slot', 'P1', 128, 512)]},
        'value_bytes': {'kv0': 128, 'kv1': 128, 'weight': 512},
        'initial_backing': ['weight'], 'initial_copies': {'kv-slot': 'kv0'},
        'routes': {'store-kv': route('P0', 'DDR', 3), 'load-kv': route('DDR', 'P1', 4)},
        'services': {'produce': {'ticks': 1, 'claims': {}}, 'consume': {'ticks': 1, 'claims': {}}},
        'live_out': ['kv0', 'kv1'],
    }}
    tasks = [task('token-1-update', binding('produce', stage('produce', outputs={'kv-slot': 'kv1'}))),
             task('token-2-history', binding('consume', stage('consume', inputs={'next-kv': 'kv0'})),
                  after=('token-1-update',))]
    return tasks, hw


class MixedDmaTests(unittest.TestCase):
    def test_prefetch_overlaps_previous_compute_but_waits_for_window_custody(self):
        for reuses_window in (False, True):
            with self.subTest(reuses_window=reuses_window):
                _, hw = mixed_problem()
                spec = hw['event_model']
                spec['live_out'] = []
                spec['initial_backing'].append('kv0')
                spec['initial_copies']['next-kv'] = 'kv0'
                spec['services']['compute'] = {'ticks': 80, 'claims': {}}
                predecessor = task('release', binding('release', stage('produce')))
                inputs = {'next-kv': 'kv0'} if reuses_window else {}
                dst = 'next-kv' if reuses_window else 'weight-slot'
                # Both windows fit a 128 B tile. Only next-kv is read by the old stage.
                spec['value_bytes']['weight'] = 128
                stages = [stage('compute', inputs=inputs),
                          {**stage('consume', inputs={dst: 'weight'}), 'prefetch': [dst]}]
                tasks = [predecessor, task('attention', binding('prefetch', *stages), after=('release',))]
                plan = search(tasks, hw, width=8)
                verify(tasks, hw, (), plan)
                first, load, consume = plan['tasks'][1]['evaluation']['events']
                self.assertEqual(load['start'], first['end'] if reuses_window else first['start'])
                self.assertEqual(consume['start'], max(first['end'], load['end']))
                bad = deepcopy(plan)
                del bad['tasks'][1]['evaluation']['events'][1]['prefetch']
                with self.assertRaisesRegex(ValueError, 'prefetch inputs differ|invalid event interval'):
                    verify(tasks, hw, (), bad)

    def test_prefetch_waits_for_explicit_ddr_publication(self):
        _, hw = mixed_problem()
        hw['event_model']['live_out'] = []
        publish = {**stage('produce', inputs={'kv-slot': 'kv0'}), 'persist': ['kv-slot']}
        prefetch = {**stage('consume', inputs={'next-kv': 'kv0'}), 'prefetch': ['next-kv']}
        tasks = [task('publication', binding('publish', publish)),
                 task('attention', binding('prefetch', stage('produce'), prefetch))]
        plan = search(tasks, hw, width=8)
        verify(tasks, hw, (), plan)
        store = plan['tasks'][0]['evaluation']['events'][0]
        first, load, consumer = plan['tasks'][1]['evaluation']['events']
        self.assertLess(first['end'], store['end'])
        self.assertEqual(load['start'], store['end'])
        self.assertEqual(consumer['start'], load['end'])

    def test_route_probe_scores_prefetch_ack_inside_longer_compute(self):
        _, hw = mixed_problem()
        spec = hw['event_model']
        spec['live_out'] = []
        spec['value_bytes']['weight'] = 128
        spec['transport_limit'] = 2
        spec['typed_dma']['client_ready'] = [(0, 44, 4095 ^ (1 << 4))]
        slow = spec['routes'].pop('load-kv')
        fast = deepcopy(slow)
        fast['typed_dma']['client'] = 5
        spec['routes'].update({'a-slow': slow, 'z-fast': fast})
        spec['services']['compute'] = {'ticks': 90, 'claims': {}}
        prefetched = {**stage('consume', inputs={'weight-slot': 'weight'}), 'prefetch': ['weight-slot']}
        tasks = [task('attention', binding('prefetch', stage('compute'), prefetched))]
        plan = search(tasks, hw, width=1)
        verify(tasks, hw, (), plan)
        compute, load, _ = plan['tasks'][0]['evaluation']['events']
        self.assertLess(load['end'], compute['end'])
        self.assertEqual(load['route'], 'z-fast')
        model = Model(hw)
        delivered = []
        for route in ('a-slow', 'z-fast'):
            row = {'id': 'attention', 'covers': ['attention'],
                   'evaluation': {'events': [compute, {**load, 'route': route}]}}
            delivered.append(delivery_at(model, (), Decision(row, frozenset()), None))
        self.assertLess(delivered[1], delivered[0])
        self.assertLess(delivered[0], compute['end'])

    def test_explicit_kv_persist_waits_for_ack_without_eviction(self):
        _, hw = mixed_problem()
        hw['event_model']['live_out'] = ['kv0']
        publish = {**stage('produce', inputs={'kv-slot': 'kv0'}), 'persist': ['kv-slot']}
        tasks = [task('token-1-publish', binding('publish', publish)),
                 task('token-2-history', binding('consume', stage('consume', inputs={'next-kv': 'kv0'})))]
        plan = search(tasks, hw, width=8)
        verify(tasks, hw, (), plan)
        store, publish = plan['tasks'][0]['evaluation']['events']
        load = plan['tasks'][1]['evaluation']['events'][0]
        self.assertEqual(publish['start'], store['end'])
        self.assertEqual(load['start'], store['end'])
        self.assertEqual((plan['external_read_bytes'], plan['external_write_bytes']), (128, 128))
        bad = deepcopy(plan)
        bad['tasks'][0]['evaluation']['events'][1].pop('persist')
        with self.assertRaisesRegex(ValueError, 'persist windows differ'):
            verify(tasks, hw, (), bad)

    def test_kv_write_ack_precedes_overwrite_and_next_token_read(self):
        tasks, hw = mixed_problem()
        plan = search(tasks, hw, width=8)
        verify(tasks, hw, (), plan)
        (update, next_token) = [row['evaluation']['events'] for row in plan['tasks']]
        store, produce = update
        load, consume = next_token
        self.assertEqual((store['route'], load['route']), ('store-kv', 'load-kv'))
        self.assertTrue(all(beat['write'] for beat in store['dma_beats']))
        self.assertEqual(store['phases'][1]['end'], max(b['delivered'] for b in store['dma_beats']) + 1)
        self.assertEqual(produce['start'], store['end'])
        self.assertGreaterEqual(load['start'], store['end'])
        self.assertEqual(load['end'], consume['start'])
        self.assertEqual((plan['external_read_bytes'], plan['external_write_bytes']), (128, 128))
        altered = deepcopy(plan)
        altered['tasks'][0]['evaluation']['events'][0]['dma_beats'][0].pop('write')
        with self.assertRaisesRegex(ValueError, 'DMA handshakes'):
            verify(tasks, hw, (), altered)

    def test_write_checkpoint_retimes_old_reads_without_losing_bank_or_turnaround_state(self):
        profile = Profile.from_spec({'ffn_provider': {'mode': 0, 'seed': 0},
                                     'mixed': {'queue': 4, 'write_latency': 9}})
        read = Operation((Phase('read', 1, dma_read=Read(4, 0x20000, 4096, 2)),))
        write = Operation((Phase('write', 1, dma_read=Read(3, 0x10000, 1024, 2, True)),), release=65)
        prefix = replay_branch([read], {}, dma_profile=profile)
        boundary = next(cp for cp in prefix.checkpoints if cp.tick == 64)
        self.assertTrue(boundary.fabric.active)
        branch = replay_branch([read, write], {}, dma_profile=profile, previous=prefix)
        full = replay_branch([read, write], {}, dma_profile=profile, save_checkpoints=False)
        self.assertEqual(branch.grants, full.grants)
        self.assertGreater(branch.grants[0][0].end, prefix.grants[0][0].end)
        self.assertEqual(len(branch.grants[1][0].dma_beats), 16)
        self.assertTrue(all(b.write for b in branch.grants[1][0].dma_beats))
