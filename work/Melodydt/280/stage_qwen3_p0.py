"""Select only P0 for FFN on a copy of the instrumented three-P replay."""
import argparse
from pathlib import Path

from stage_ddr_probe import before, replace


def stage(replay):
    plan = replay / "qwen3_short_plan.py"
    before(plan, "    three_p = False", "    ffn_sites = (P, CONTEXT, MID)\n")
    replace(plan, "        for site in (P, CONTEXT, MID):",
            "        for site in self.ffn_sites:")
    for end in ("width", "self.hidden"):
        replace(plan,
                f"        for first in range(0, {end}, 384):\n"
                f"            items = list(zip((P, CONTEXT, MID), range(first, min(first+384, {end}), 128)))",
                f"        for first in range(0, {end}, step):\n"
                f"            items = list(zip(self.ffn_sites, range(first, min(first+step, {end}), 128)))")
    before(plan, "        for first in range(0, width, step):",
           "        step = 128 * len(self.ffn_sites)\n")

    model = replay / "qwen3_short.py"
    before(model, '    parser.add_argument("--trace-layers"',
           '    parser.add_argument("--ffn-p0-only", action="store_true")\n')
    before(model, "    if args.three_p and args.pr272_profile",
           '    if args.ffn_p0_only and (args.model != "qwen3" or not args.three_p):\n'
           '        parser.error("the P0-only FFN experiment requires the Qwen3 three-target runtime")\n')
    before(model, "    plan = compiler.compile()",
           "    if args.ffn_p0_only:\n        compiler.ffn_sites = (P,)\n")
    before(model, "    if args.tiled_attention128:",
           '    if args.ffn_p0_only:\n        plan["ffn_p0_only"] = True\n')
    before(model, '    if args.three_p:\n        result["ffn_by_target"]',
           '    if args.ffn_p0_only:\n        result["ffn_p0_only"] = True\n')
    replace(model,
            "        ffn_lanes = list(self.ffn_lane_proj.values()) + list(self.moe_lane_down.values())",
            """        ffn_lanes = list(self.ffn_lane_proj.values()) + list(self.moe_lane_down.values())
        if self.plan.get("ffn_p0_only"):
            if set(self.ffn_lane_proj) != {P, CONTEXT, MID} or any(
                    self.ffn_lane_proj[site].stats.get(key, 0)
                    for site in (CONTEXT, MID)
                    for key in ("weight_records_consumed", "weight_read_issues", "weight_read_returns")):
                raise ValueError("the P0-only execution did not preserve idle P1/P2")
            ffn_lanes = [self.ffn_lane_proj[P]]""")

    launch = replay / "fast_qwen3_short.sbatch"
    before(launch, '    if [[ ${MDT_274_TRACE_LAYERS:-0}',
           '    if [[ ${MDT_280_FFN_P0_ONLY:-0} == 1 ]]; then options+=(--ffn-p0-only); fi\n')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("replay", type=Path, help="isolated copy of the verified instrumented replay")
    stage(parser.parse_args().replay)
