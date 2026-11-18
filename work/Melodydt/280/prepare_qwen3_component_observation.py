"""Install non-scheduling probes in a private copy of the frozen source."""
from pathlib import Path
import sys


def replace(source, before, after):
    text = source.read_text()
    if text.count(before) != 1:
        raise ValueError(f"unknown frozen source anchor in {source}")
    source.write_text(text.replace(before, after))


root = Path(sys.argv[1])
qwen = root / "qwen3_short.py"
replace(qwen, "    result = execution.run(trace_layers=args.trace_layers)",
        "    from qwen3_component_observation import Observation\n"
        "    observation = Observation(execution)\n"
        "    result = execution.run(trace_layers=args.trace_layers)\n"
        '    observation.write(args.output / "component-observation.json")')
proj = root / "pr272_native_projection.py"
replace(proj, "                        self.edge(finish_group, 8 + 8 * (8 if head16 else 1))",
        "                        cycles = 8 + 8 * (8 if head16 else 1)\n"
        "                        self.target.component_observation.m_group(self.target, self.clock.now, cycles)\n"
        "                        self.edge(finish_group, cycles)")
