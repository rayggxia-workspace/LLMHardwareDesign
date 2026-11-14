"""Retry exactly the same diagnosed toy nets without a repeater."""

import argparse
from pathlib import Path

from geometry import NativePins
from resource_search import estimated_load, length
import search
import weighted
from study import area, compact, electrical_inputs, geometry_result, read, verify, write


def main(handoff, study, output, weight, jumps):
    weighted.enable(weight, jumps)
    spec = read(handoff/"algorithm2-input.json")
    direct = read(study/"direct.json")
    summary = read(study/"summary.json")
    trials = read(study/"trials.json")
    nets = {net["id"]: net for net in spec["nets"]}
    model = electrical_inputs(summary["model"], spec)
    routes = dict(direct["routes"])
    failed = dict(direct["failed"])
    native = NativePins(spec)
    evidence = []
    for row in trials:
        name = row["net"]
        net = nets[name]
        old = row["direct_load"]
        trial = area(spec, routes, omit=name)
        budget = 2*summary["method"]["repair_budget"]*summary["method"]["candidates"]
        new, reason, expanded, _ = search.route_net(net, spec, trial, {}, budget, native)
        load = (estimated_load(net, new, model["driver_limits_ff"], model["sink_caps_ff"], model)
                if new else None)
        keep = load is not None and (old is None or load["over_ff"] < old[0]["over_ff"])
        if keep:
            failed.pop(name, None)
            routes[name] = compact(new, net, spec)
        evidence.append({"net": name, "diagnosis": row["reason"], "accepted": keep, "load": load,
                         "expanded": expanded, "budget": budget, "reason": reason,
                         "wire_um": length(new)/2000 if new else None})
        print(name, keep, expanded, flush=True)
    result = geometry_result(spec, routes, failed)
    result["geometry_check"] = verify(spec, result)
    output.mkdir()
    write(output/"routes.json", result)
    write(output/"summary.json", {"geometry": result["geometry_check"], "trials": evidence})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("handoff", type=Path)
    parser.add_argument("study", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--weight", type=int, required=True)
    parser.add_argument("--jumps", action="store_true")
    args = parser.parse_args()
    main(args.handoff, args.study, args.output, args.weight, args.jumps)
