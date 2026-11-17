"""Add ordinary projection occupancy without changing scheduling or numerics."""
from collections import Counter
import json
from qwen3_component_observation import Observation as BaseObservation


class Observation(BaseObservation):
    def __init__(self, execution):
        super().__init__(execution)
        self.native = {name: [Counter() for _ in execution.sram] for name in self.names[:-1]}
        self.native_tail = [0] * len(execution.sram)

    def m_group(self, bank, begin, cycles):
        if begin < self.native_tail[bank.component_site]:
            raise ValueError('ordinary and FFN M intervals overlap')
        super().m_group(bank, begin, cycles)

    def native_m_group(self, bank, begin, cycles):
        site = bank.component_site
        if begin < self.m_tail[site]:
            raise ValueError('FFN and ordinary M intervals overlap')
        end = begin + cycles * bank.core_ps - begin % bank.core_ps
        unique_begin = max(begin, self.native_tail[site])
        self.native_tail[site] = max(self.native_tail[site], end)
        for name, per_site in self.native.items():
            lo, hi = (self.windows[name][key] for key in ('start_ps', 'end_ps'))
            if lo <= begin < hi:
                per_site[site]['groups_dispatched'] += 1
            per_site[site]['busy_interval_union_ps'] += max(0, min(end, hi) - max(lo, unique_begin))

    def write(self, destination):
        super().write(destination)
        data = json.loads(destination.read_text())
        data['ordinary_and_ffn_intervals_disjoint'] = True
        for name in self.names[:-1]:
            data['windows'][name]['ordinary_projection_m_by_site'] = self.native[name]
        destination.write_text(json.dumps(data, indent=2) + '\n')
