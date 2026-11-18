"""Preserve the accepted Qwen3 disjoint-M checks while adding RMS observation."""
import json
from arithmetic_observation import ArithmeticObservation


class Observation(ArithmeticObservation):
    def m_group(self, bank, begin, cycles):
        if begin < self.native_tail[bank.component_site]:
            raise ValueError('ordinary and FFN M intervals overlap')
        super().m_group(bank, begin, cycles)

    def native_m_group(self, bank, begin, cycles):
        if begin < self.m_tail[bank.component_site]:
            raise ValueError('FFN and ordinary M intervals overlap')
        super().native_m_group(bank, begin, cycles)

    def write(self, destination):
        super().write(destination)
        data = json.loads(destination.read_text())
        data['ordinary_and_ffn_intervals_disjoint'] = True
        destination.write_text(json.dumps(data, indent=2) + '\n')
