"""Observe SRAM beats, PM loads, and modeled M intervals without new clock events."""
import json
from collections import Counter
from pathlib import Path
import os


class Observation:
    def __init__(self, execution):
        self.windows = json.loads(Path(os.environ["QWEN3_COMPONENT_WINDOWS"]).read_bytes())
        names = ("prefill",) if execution.plan["mode"] == "prefill" else ("first_token", "decode")
        self.names = names + ("outside",)
        self.sram = {name: [Counter() for _ in execution.sram] for name in self.names}
        self.pm = {name: {"mother": Counter(), "local": Counter()} for name in self.names}
        self.m = {name: [Counter() for _ in execution.sram] for name in names}
        self.m_tail = [0 for _ in execution.sram]
        self.blocks = execution.sram
        for site, bank in enumerate(execution.sram):
            bank.access_beat = self.wrap_memory(site, bank, bank.access_beat)
            bank.component_observation = self
            bank.component_site = site
        scheduler = execution.scheduler
        scheduler.install_pm = self.wrap_pm(scheduler, scheduler.install_pm)

    def window(self, ps):
        for name in self.names[:-1]:
            row = self.windows[name]
            if row["start_ps"] <= ps < row["end_ps"]:
                return name
        return "outside"

    def wrap_memory(self, site, bank, access):
        def observe(word, words, done, payload=None):
            access(word, words, done, payload)
            kind = "read" if payload is None else "write"
            counters = self.sram[self.window(bank.next_port - bank.core_ps)][site]
            counters[f"{kind}_beats"] += 1
            counters[f"{kind}_{128 * words}bit"] += 1
            counters[f"{kind}_bytes"] += 16 * words
            for index in range(word, word + words):
                counters[f"{kind}_bank{index % 4}"] += 1
        return observe

    def wrap_pm(self, scheduler, install):
        def observe(address, image_bytes, *, mother):
            start = scheduler.clock.now
            install(address, image_bytes, mother=mother)
            name = self.window(start)
            row = self.pm[name]["mother" if mother else "local"]
            row["images"] += 1
            row["bytes"] += image_bytes
            row["ddr_reads"] += (image_bytes + 63) // 64
            row["pm_write_beats"] += (image_bytes + scheduler.pm_write_bytes - 1) // scheduler.pm_write_bytes
            row["byte_serial_readback_cycles"] += image_bytes if mother else 0
            row["elapsed_including_ddr_wait_ps"] += scheduler.clock.now - start
        return observe

    def m_group(self, bank, begin, cycles):
        site = bank.component_site
        end = begin + cycles * bank.core_ps - begin % bank.core_ps
        unique_begin = max(begin, self.m_tail[site])
        self.m_tail[site] = max(self.m_tail[site], end)
        for name, per_site in self.m.items():
            window = self.windows[name]
            lo, hi = window["start_ps"], window["end_ps"]
            if lo <= begin < hi:
                per_site[site]["groups_dispatched"] += 1
            per_site[site]["busy_interval_union_ps"] += max(0, min(end, hi) - max(lo, unique_begin))

    def write(self, destination):
        for site, instance in enumerate(self.blocks):
            for key in ("read_beats", "write_beats", "read_bytes", "write_bytes"):
                if sum(groups[site][key] for groups in self.sram.values()) != instance.stats[key]:
                    raise ValueError(f"SRAM observer did not reconcile {site}/{key}")
            for index in range(4):
                if sum(groups[site][f"{op}_bank{index}"] for groups in self.sram.values()
                       for op in ("read", "write")) != instance.stats[f"bank{index}_accesses"]:
                    raise ValueError(f"SRAM observer did not reconcile bank {site}/{index}")
        result = {"scope": "TLM SRAM port start, PM install, and PR272 M group timing including modeled drain",
                  "windows": {name: {"boundaries": self.windows[name], "sram_by_site": self.sram[name],
                                     "modeled_m_by_site": self.m[name], "pm": self.pm[name]}
                              for name in self.names[:-1]},
                  "outside_sram_by_site": self.sram["outside"], "outside_pm": self.pm["outside"]}
        destination.write_text(json.dumps(result, indent=2) + "\n")
