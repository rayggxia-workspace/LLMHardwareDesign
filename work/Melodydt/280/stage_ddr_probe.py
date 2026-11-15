"""Add the read-only DDR energy probe to copies of the original sources."""
import argparse
from pathlib import Path
from shutil import copytree


def replace(path, anchor, replacement):
    source = path.read_text(encoding="utf-8")
    if source.count(anchor) != 1:
        raise ValueError(f"{path}: expected exactly one anchor {anchor!r}")
    path.write_text(source.replace(anchor, replacement), encoding="utf-8")


def before(path, anchor, insertion):
    replace(path, anchor, insertion + anchor)


def add_library_probe(src):
    before(src / "simple_stats.h", "    void PrintEpochStats();",
           "    nlohmann::json EnergySnapshot() const;\n")
    before(src / "controller.h", "    void PrintEpochStats();",
           "    nlohmann::json EnergySnapshot() const { return simple_stats_.EnergySnapshot(); }\n")
    before(src / "dram_system.h", "    void PrintStats();",
           "    nlohmann::json EnergySnapshot() const;\n")
    before(src / "memory_system.h", "    void PrintStats() const;",
           "    std::string EnergySnapshot() const;\n")
    before(src / "dram_system.cc", "void BaseDRAMSystem::PrintStats()",
           """nlohmann::json BaseDRAMSystem::EnergySnapshot() const {
    auto channels = nlohmann::json::array();
    for (const auto* controller : ctrls_) {
        channels.push_back(controller->EnergySnapshot());
    }
    return channels;
}

""")
    before(src / "memory_system.cc", "void MemorySystem::PrintStats()",
           """std::string MemorySystem::EnergySnapshot() const {
    return dram_system_->EnergySnapshot().dump();
}

""")
    probe = Path(__file__).with_name("ddr_snapshot.inc").read_text(encoding="utf-8")
    before(src / "simple_stats.cc", "}  // namespace dramsim3", probe + "\n")


def add_replay_probe(replay):
    bridge = replay / "fast_tlm_dram.cpp"
    before(bridge, "#include <limits>", "#include <fstream>\n")
    before(bridge, "    void finish() {", r"""    void energy_snapshot(const char* path) const {
        std::ofstream out(path);
        out << "{\"device_ps\":" << now_ << ",\"tick_ps\":" << ddr_ps << ",\"devices\":["
            << channels_[0].device->EnergySnapshot() << ","
            << channels_[1].device->EnergySnapshot() << "]}\n";
        out.close();
        if (!out) {
            throw std::runtime_error("could not write DDR energy snapshot");
        }
    }

""")
    before(bridge, 'extern "C" int fast_dram_close', """extern "C" int fast_dram_energy_snapshot(void* handle, const char* path) noexcept {
    return guard([&]() { transport(handle).energy_snapshot(path); return 1; }, 0);
}

""")
    py_bridge = replay / "fast_tlm_replay.py"
    before(py_bridge, "        self.handle = self.lib.fast_dram_open(", """        self.energy_directory = output
        self.lib.fast_dram_energy_snapshot.argtypes = (pointer, char)
        self.lib.fast_dram_energy_snapshot.restype = integer
""")
    before(py_bridge, "    def close(self):", """    def capture_energy(self, mark):
        path = self.energy_directory / f"energy-{mark}.json"
        self.check(self.lib.fast_dram_energy_snapshot(self.handle, str(path).encode()) == 1)
        data = json.loads(path.read_bytes())
        data["replay_ps"] = self.clock.now
        path.write_text(json.dumps(data, indent=2) + "\\n", encoding="utf-8")

""")
    model = replay / "qwen3_short.py"
    before(model, '        addr = self.plan["local"]["address"]',
           '        self.dram.capture_energy("start")\n')
    before(model, "            residual = self.read(U, 0, self.hidden//4)", """            if not decode and step == 1:
                self.dram.capture_energy("prefill_end")
""")
    before(model, '            (self.output / "progress.json").write_text(', """                self.dram.capture_energy(f"retire_{step+1}")
""")
    before(model, "        self.dram.close()", '        self.dram.capture_energy("end")\n')
    launcher = replay / "fast_qwen3_short.sbatch"
    replace(launcher, '"$bridge/run-113164.dram.so"', '"${MDT_280_DDR_LIBRARY:?set the instrumented DDR library path}"')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="frozen DRAMsim3 source tree")
    parser.add_argument("output", type=Path, help="new isolated directory")
    parser.add_argument("--replay", type=Path,
                        help="frozen replay directory containing the bridge and model sources")
    args = parser.parse_args()
    args.output.mkdir()
    library = args.output / "dramsim3"
    copytree(args.source, library, ignore=lambda _, names: {".git"} & set(names))
    add_library_probe(library / "src")
    if args.replay:
        replay = args.output / "replay"
        replay.mkdir()
        for name in ("fast_tlm_dram.cpp", "fast_tlm_replay.py", "qwen3_short.py", "fast_qwen3_short.sbatch"):
            (replay / name).write_bytes((args.replay / name).read_bytes())
        add_replay_probe(replay)


if __name__ == "__main__":
    main()
