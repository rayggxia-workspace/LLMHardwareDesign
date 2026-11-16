"""Capture accepted G32 activity on historical Qwen gate/up tensor packets."""
import argparse
import hashlib
import json
from pathlib import Path

from e_activity import normalize_period
from native import LIB, LIB_SHA


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(source, out, prior, delivery):
    old_vectors = prior / "vectors.txt"
    oracle = json.loads((prior / "oracle.json").read_text())
    assert oracle["actual_model_packets"] == 2048 and sha(old_vectors) == oracle["vector_sha256"]
    prior_function = json.loads((prior / "final-function.json").read_text())
    assert prior_function["passed"] and sha(prior / "physical-functional.v") == prior_function["full_final_netlist"]["full_view_sha256"]
    selected = old_vectors.read_text().splitlines()[-2048:][:256]
    assert all(row.split()[2:4] == ["1","3"] and row.split()[5] == "0" for row in selected)
    (out / "actual-model-vectors.txt").write_text(str(len(selected)) + "\n" + "\n".join(selected) + "\n")
    text = source.read_text()
    definitions = "    string vector_file;"
    assert text.count(definitions) == 1
    text = text.replace(definitions, definitions + "\n    string activity_file;\n    integer activity_start;")
    start = "        reset = 0;\n        while (received < count) begin"
    assert text.count(start) == 1
    text = text.replace(start, """        reset = 0;
        repeat (4) @(negedge clk);
        activity_start = cycle;
        if (!$value$plusargs("activity=%s", activity_file)) $fatal(1, "activity file required");
        $dumpfile(activity_file);
        $dumpvars;
        if ($test$plusargs("activity_idle")) begin
            repeat (256) @(negedge clk);
            $display("G_ACTIVITY cycles=%0d packets=0", cycle - activity_start);
            $finish;
        end
        while (received < count) begin""")
    end = "        $finish;\n    end"
    assert text.count(end) == 1
    text = text.replace(end, """        $display("G_ACTIVITY cycles=%0d packets=%0d", cycle - activity_start, received);
""" + end)
    (out / "test_g_s32_activity.sv").write_text(text)
    final = json.loads((delivery / "delivery.json").read_text())
    assert final["native_leaf_accepted"] and sha(LIB) == LIB_SHA
    inputs = {name: final["final_files"][name] for name in ("6_final.odb", "6_final.sdc", "6_final.spef")}
    for row in inputs.values():
        assert sha(Path(row["path"])) == row["sha256"]
    assert inputs["6_final.odb"]["sha256"] == prior_function["final_odb_sha256"]
    scope = "test_g_s32/dut"
    for mode in ("active","idle"):
        script = f"""read_liberty {{{LIB}}}
read_db {{{inputs['6_final.odb']['path']}}}
read_sdc {{{inputs['6_final.sdc']['path']}}}
read_spef {{{inputs['6_final.spef']['path']}}}
read_vcd -scope {{{scope}}} {{{out / (mode+'-tt300.vcd')}}}
report_activity_annotation
report_power -digits 12
"""
        (out / f"{mode}-power.tcl").write_text(script)
    (out / "inputs.json").write_text(json.dumps(dict(
        vectors_256_sha256=sha(out/"actual-model-vectors.txt"), parent_vectors_sha256=sha(old_vectors),
        actual_scope=oracle["actual_model_groups"][0], native=inputs,
        functional_netlist_sha256=sha(prior/"physical-functional.v"), liberty_sha256=LIB_SHA),indent=2)+"\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path)
    p.add_argument("--prior", type=Path)
    p.add_argument("--delivery", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--normalize", action="store_true")
    a = p.parse_args()
    if a.normalize:
        for mode in ("active","idle"):
            normalize_period(a.out / f"{mode}.vcd", a.out / f"{mode}-tt300.vcd")
    else:
        prepare(a.source, a.out, a.prior, a.delivery)


if __name__ == "__main__":
    main()
