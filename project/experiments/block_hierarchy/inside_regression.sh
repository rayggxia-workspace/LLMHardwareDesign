#!/usr/bin/env bash
# Original fixed-source VECTOR RTL regression; not a netlist equivalence check.
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
: "${LLHD_ATTEMPT:?LLHD_ATTEMPT must name a new isolated attempt}"
: "${NUM_CORES:?NUM_CORES must come from the Slurm allocation}"
[[ "$NUM_CORES" =~ ^[1-9][0-9]*$ ]]
cd "$LLHD_ATTEMPT"

export CCACHE_DIR="$LLHD_ATTEMPT/regression-cache"
export TMPDIR="$LLHD_ATTEMPT/regression-tmp"
export XDG_CACHE_HOME="$LLHD_ATTEMPT/regression-xdg-cache"
mkdir -p "$CCACHE_DIR" "$TMPDIR" "$XDG_CACHE_HOME"
export VERILATOR_ROOT=/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator
verilator_exe=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
test -x "$verilator_exe"
test -x /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator_bin
test -f source/tb/vec/Makefile
test -f source/include/llaccel/luts.h

"$verilator_exe" --version > verilator-version.txt 2>&1
g++ --version > regression-cxx-version.txt 2>&1
{
  sha256sum "$verilator_exe" /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator_bin
  sha256sum "$(command -v make)" "$(command -v g++)" /usr/bin/g++ "$(command -v python3)"
} > regression-tools.sha256
sha256sum source/tb/vec/Makefile source/tb/vec/tb_vec_top.sv source/tb/vec/tb_vec.cpp \
  source/tb/vec/tb_math_top.sv source/tb/vec/tb_math.cpp source/tb/common/sram_stub.sv \
  source/rtl/llaccel_pkg.sv source/rtl/llaccel_luts_pkg.sv source/rtl/vec_engine.sv \
  source/rtl/isqrt.sv source/rtl/udiv.sv source/include/llaccel/numerics.h \
  source/include/llaccel/isa.h source/include/llaccel/luts.h > regression-source.sha256

# Keep the fixed archive unchanged. GCC 11 rejects the original signed literal
# in a uint32_t initializer; change only its type in a separate test work copy.
# The intended 0x80000000 edge value, cases, assertions and RTL stay unchanged.
test ! -e regression-source
python3 - <<'PYCOMPAT'
import difflib
import hashlib
from pathlib import Path
import shutil

baseline = Path("source")
working = Path("regression-source")
relative = Path("tb/vec/tb_math.cpp")
before = (baseline / relative).read_bytes()
old, new = b"1 << 31", b"1u << 31"
assert before.count(old) == 1, "Expected exactly one signed edge32 literal"
assert b"const uint32_t edge32[]" in before
shutil.copytree(baseline, working, copy_function=shutil.copy2)
after = before.replace(old, new, 1)
(working / relative).write_bytes(after)
baseline_files = {p.relative_to(baseline) for p in baseline.rglob("*") if p.is_file()}
working_files = {p.relative_to(working) for p in working.rglob("*") if p.is_file()}
assert baseline_files == working_files, "Compatibility copy changed the file set"
changed = {p for p in baseline_files if (baseline / p).read_bytes() != (working / p).read_bytes()}
assert changed == {relative}, "Only the testbench literal may differ; RTL must match"
assert (baseline / relative).read_bytes() == before, "Source archive changed"
patch = "".join(difflib.unified_diff(
    before.decode().splitlines(keepends=True), after.decode().splitlines(keepends=True),
    fromfile="source/" + relative.as_posix(), tofile="regression-source/" + relative.as_posix(),
))
assert patch, "Compatibility patch must be recorded"
Path("compat-patch.diff").write_text(patch)
Path("compat-inputs.sha256").write_text(
    hashlib.sha256(before).hexdigest() + "  source/" + relative.as_posix() + "\n" +
    hashlib.sha256(after).hexdigest() + "  regression-source/" + relative.as_posix() + "\n"
)
print("Compatibility copy: one tb_math.cpp literal -> 1u << 31 (uint32_t 0x80000000); archive and RTL unchanged")
PYCOMPAT

# BUILD overrides the Makefile's source-tree default; -j1 serializes the two
# builds, each using NUM_CORES. Keep every original case and fixed random seed.
set +e
make -j1 -C "$LLHD_ATTEMPT/regression-source/tb/vec" \
  BUILD="$LLHD_ATTEMPT/regression-build" VERILATOR="$verilator_exe" \
  JOBS="$NUM_CORES" SEED=1 run 2>&1 | tee regression.log
pipeline_codes=("${PIPESTATUS[@]}")
set -e
python3 - "${pipeline_codes[0]}" "${pipeline_codes[1]}" <<'PY'
import json
from pathlib import Path
import re
import sys

make_exit, tee_exit = map(int, sys.argv[1:3])
log = Path("regression.log").read_text(errors="replace")
vector = re.search(r"^tb_vec: (\d+) cases, (\d+) failures -> (PASS|FAIL)\s*$", log, re.M)
math = re.search(r"^tb_math: (\d+) operand sets \([^\n]*\), (\d+) failures\s*$", log, re.M)
rows = re.findall(r"^(VEC_\S+)\s+deny=\s*(\d+)%: (\d+) cases, (\d+) failures,", log, re.M)
expected_ops = {"VEC_SILU", "VEC_MUL", "VEC_ADD", "VEC_QUANT", "VEC_RMSNORM", "VEC_ROPE"}
expected_grid = {(op, deny) for op in expected_ops for deny in (0, 30)}
seen_grid = {(op, int(deny)) for op, deny, _, _ in rows}
grid_ok = (len(rows) == 12 and seen_grid == expected_grid
           and all(int(cases) == 100 and int(fails) == 0 for _, _, cases, fails in rows))
vector_ok = bool(vector and int(vector[1]) == 1203 and int(vector[2]) == 0 and vector[3] == "PASS")
math_ok = bool(math and int(math[1]) == 12000 and int(math[2]) == 0)
rounding_ok = "rounding: 16384 full-width cases checked against 128-bit oracle" in log
passed = make_exit == 0 and tee_exit == 0 and vector_ok and grid_ok and math_ok and rounding_ok
submission = json.loads(Path("submission.json").read_text())
result = {
    "schema_version": 1,
    "kind": "original_vector_rtl_regression",
    "status": "pass" if passed else "fail",
    "source_commit": submission.get("source_commit"),
    "random_seed": 1,
    "make_exit_code": make_exit,
    "log_tee_exit_code": tee_exit,
    "expected_vector_cases": 1203,
    "vector_cases": int(vector[1]) if vector else None,
    "vector_failures": int(vector[2]) if vector else None,
    "vector_summary_pass": vector_ok,
    "all_12_operation_denial_groups_pass": grid_ok,
    "math_operand_sets": int(math[1]) if math else None,
    "math_failures": int(math[2]) if math else None,
    "math_summary_pass": math_ok,
    "rounding_16384_cases_reported": rounding_ok,
    "runtime_executed": bool(vector or math or rounding_ok),
    "runtime_execution_evidence": {
        "vector_summary_present": bool(vector),
        "math_summary_present": bool(math),
        "rounding_summary_present": rounding_ok,
        "note": "Summary presence confirms execution; absence does not prove that a failing binary never started",
    },
    "reference": "regression-source/include/llaccel/numerics.h and regression-source/include/llaccel/luts.h, byte-identical to source archive",
    "compatibility": {
        "working_copy": "regression-source",
        "source_archive_modified": False,
        "changed_file": "tb/vec/tb_math.cpp",
        "unique_replacement": "1 << 31 -> 1u << 31",
        "expected_uint32_value": "0x80000000",
        "reason": "GCC 11/C++20 rejects signed-int narrowing in the original uint32_t initializer; unsigned literal preserves the intended edge value",
        "other_source_files_and_rtl_identical": True,
        "global_warning_suppression_added": False,
    },
    "intended_coverage": [
        "Six original VEC operations, 100 random cases each at 0% and 30% grant denial",
        "Three original directed RMSNorm/RoPE cases; full 1 MiB SRAM image comparison",
        "Original request/payload hold assertions, completion pulse/tag/busy checks",
        "Original isqrt/udiv and rounding testbench",
    ],
    "not_performed": [
        "Full-core or real SRAM-macro simulation",
        "Original RTL-to-synthesized/routed-netlist formal equivalence",
        "Gate-level or post-route simulation",
    ],
    "evidence": ["regression.log", "verilator-version.txt", "regression-cxx-version.txt",
                 "regression-tools.sha256", "regression-source.sha256",
                 "compat-patch.diff", "compat-inputs.sha256"],
}
Path("regression-result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
raise SystemExit(0 if passed else 1)
PY
