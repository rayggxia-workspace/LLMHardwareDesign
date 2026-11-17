"""Read-only model-specific counters extending the Qwen3 component probe."""
from collections import Counter
import json

from qwen3_component_observation import Observation


class ModelObservation(Observation):
    def __init__(self, execution):
        super().__init__(execution)
        self.execution = execution
        self.events = {name: Counter() for name in self.names}
        self.native_m = {name: [Counter() for _ in execution.sram] for name in self.names[:-1]}
        self.native_tail = [0] * len(execution.sram)
        execution.energy_observation = self
        install = execution.scheduler.install_pm

        def pm(address, image_bytes, *, mother):
            name = self.window(execution.clock.now)
            self.events[name]["pm_{}_bytes_{}".format("mother" if mother else "local", image_bytes)] += 1
            return install(address, image_bytes, mother=mother)
        execution.scheduler.install_pm = pm
        for site, unit in enumerate(execution.e):
            unit.leaf = self.wrap_leaf(site, unit.leaf)

    def wrap_leaf(self, site, leaf):
        def observe(opcode, cycles, done):
            self.events[self.window(self.execution.clock.now)]["leaf_{}_{}_cycles{}".format(site, opcode, cycles)] += 1
            return leaf(opcode, cycles, done)
        return observe

    def activation(self, site, words, gelu, sigmoid, scaled):
        kind = "gelu" if gelu else "sigmoid" if sigmoid else "scaled_silu" if scaled else "silu"
        self.events[self.window(self.execution.clock.now)]["activation_{}_site{}_words{}".format(kind, site, words)] += 1

    def native_m_group(self, bank, begin, cycles):
        site = bank.component_site
        end = begin + cycles * bank.core_ps - begin % bank.core_ps
        unique_begin = max(begin, self.native_tail[site])
        self.native_tail[site] = max(self.native_tail[site], end)
        for name, per_site in self.native_m.items():
            lo, hi = (self.windows[name][key] for key in ("start_ps", "end_ps"))
            if lo <= begin < hi:
                per_site[site]["groups_dispatched"] += 1
            per_site[site]["busy_interval_union_ps"] += max(0, min(end, hi) - max(lo, unique_begin))

    def write(self, destination):
        super().write(destination)
        data = json.loads(destination.read_text())
        data["scope"] += "; activation kind including nested MoE, exact PM page sizes, U leaf calls; ordinary projection intervals recorded separately"
        for name in self.names[:-1]:
            data["windows"][name]["model_events"] = self.events[name]
            data["windows"][name]["ordinary_projection_m_by_site"] = self.native_m[name]
        data["outside_model_events"] = self.events["outside"]
        destination.write_text(json.dumps(data, indent=2) + "\n")
