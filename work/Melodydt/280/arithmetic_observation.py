"""Capture bounded real RMS vectors and complete N leaf counts, without clock events."""
from collections import Counter
import json
from struct import unpack_from

from six_model_observation import ModelObservation


class ArithmeticObservation(ModelObservation):
    def __init__(self, execution):
        super().__init__(execution)
        self.rms_counts = Counter()
        self.samples = []
        self.active = {}
        self.n_counts = {name: [Counter() for _ in execution.n] for name in self.names}
        self.n_initial = [Counter(unit.stats) for unit in execution.n]
        for site, unit in enumerate(execution.n):
            unit.arithmetic_observer = self
            unit.arithmetic_site = site
            unit.leaf = self.n_leaf(site, unit.leaf)

    def n_leaf(self, site, leaf):
        def observe(opcode, cycles, done):
            name = self.window(self.execution.clock.now)
            row = self.n_counts[name][site]
            row[opcode + '_calls'] += 1
            row[opcode + '_modeled_cycles'] += cycles
            return leaf(opcode, cycles, done)
        return observe

    def rms_begin(self, unit, record, shifted_format):
        site = unit.arithmetic_site
        if site in self.active:
            raise ValueError('overlapping RMS capture')
        source, gamma, target, words, epsilon = unpack_from('<4HI', record, 16)
        shift, output_shift = record[28:30] if shifted_format else (0, 0)
        name = self.window(self.execution.clock.now)
        key = '{}:site{}:words{}:eps{}:shift{}:out{}'.format(name, site, words, epsilon, shift, output_shift)
        self.rms_counts[key] += 1
        sample = None
        if self.rms_counts[key] <= 2:
            sample = dict(signature=key, window=name, site=site, words=words, epsilon=epsilon,
                          shift=shift, output_shift=output_shift, shifted_format=shifted_format,
                          descriptor_hex=record.hex(), start_ps=self.execution.clock.now,
                          source=[], gamma=[], expected=[])
            self.samples.append(sample)
        self.active[site] = sample

    def rms_values(self, unit, kind, index, values):
        sample = self.active[unit.arithmetic_site]
        if sample is not None:
            if len(sample[kind]) != 4 * index:
                raise ValueError('RMS capture reordered or duplicated words')
            sample[kind].extend(int(value) for value in values)

    def rms_factor(self, unit, factor, extra):
        sample = self.active[unit.arithmetic_site]
        if sample is not None:
            sample.update(factor=int(factor), extra=int(extra))

    def rms_end(self, unit):
        sample = self.active.pop(unit.arithmetic_site)
        if sample is not None:
            if any(len(sample[key]) != 4 * sample['words'] for key in ('source', 'gamma', 'expected')):
                raise ValueError('incomplete RMS capture')
            sample['end_ps'] = self.execution.clock.now

    def write(self, destination):
        super().write(destination)
        if self.active:
            raise ValueError('unfinished RMS service')
        for site, unit in enumerate(self.execution.n):
            for opcode in set(unit.stats) | set(self.n_initial[site]):
                observed = sum(self.n_counts[name][site][opcode + '_calls'] for name in self.names)
                if observed != unit.stats[opcode] - self.n_initial[site][opcode]:
                    raise ValueError('N leaf accounting mismatch')
        result = dict(scope='TLM actual RMS operands and results, two samples per window/site/shape; complete N leaf counts; not RTL or power acceptance',
                      rms_service_counts=self.rms_counts, n_leaf_by_window=self.n_counts,
                      windows=self.windows, samples=self.samples, n_counts_reconciled=True)
        destination.with_name('arithmetic-observation.json').write_text(json.dumps(result, indent=2) + '\n')
