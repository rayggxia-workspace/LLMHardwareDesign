# Issue97 reproducible server execution

Read `PROTOCOL.md`, `project/rtl/v_consumer/README.md`, `docs/experiments/issue-97-v-consumer.md` and the result index. All actual numerical arrays, RTL, gate and mapping/receivers run on the authorized CPU server in a fresh output directory. PC checks only source/metadata/bytes and `python -B scripts/check_project.py`.

Frozen source bindings contain original Git commit plus SHA-256 of every shipped source. An executed phase is immutable; later HEAD is not a substitute. Set OMP_NUM_THREADS/MKL_NUM_THREADS/OPENBLAS_NUM_THREADS=1. Existing Python/NumPy, Verilator5.042 and Yosys0.63/container are used without installation.

Commands (replace placeholders with explicit frozen server paths, never overwrite an output):

```text
python -B project/experiments/v_consumer/inputs.py --old ORIGINAL74_ROOT --out NEW_INPUT
python -B project/experiments/v_consumer/run.py build --binding BINDING --prefix CONTAINER_ARGV_JSON --suite qualification --out NEW_BUILD
python -B project/experiments/v_consumer/run.py sim --binding BINDING --prefix CONTAINER_ARGV_JSON --suite qualification --build BUILD --input INPUT --stall 0 --out NEW_RUN
python -B project/experiments/v_consumer/receive.py --input INPUT --run RUN --build BUILD --out NEW_RECEIPT_DIR
python -B project/experiments/v_consumer/run.py map --binding BINDING --prefix CONTAINER_ARGV_JSON --library LIBERTY --out NEW_MAP
python -B project/experiments/v_consumer/cost.py --map MAP --out NEW_COST_JSON
```

Repeat the functional run in a separate directory with `--stall 1`; six real cases and two synthetic numeric boundaries are fixed before measuring. Qualification driver executes50 commands, with27 complete successful consumers and2 V-only outputs, error/abort/restart and declared actual-Q boundary injections. Original oracle independently reconstructs MID/A8/delta and full M/join/norm from original74 gate/up plus static weights, checks unchanged old trace and actual new packed bytes. It never imports the RTL builder or uses host intermediate data as executable input.

Selected mapped gate uses `gate.py prepare/build/sim` and `gate_receive.py --root ROOT --out NEW_RECEIPT_DIR`; it exports the exact mapped JSON using the same Liberty logical functions and original behavioral store82. Four runs use `--pilot 1/2 --stall 0/1`, each V-only followed by full consumer; no direct Q injection, abort/error qualification or delay annotation. `run.py` pilot builds and identical pilot arguments provide exact same-driver RTL rows. The gate receiver compares every field and independently recomputes original numerics; it does not remove fields to manufacture equivalence.

`work/Liangruizhi/97/execution.json` records exact argv/resources/jobs, and the result index gives full and selected archives. Full primary remains on authorized shared storage; selected metadata can be verified locally with `work/Liangruizhi/97/verify_delivery.py --index INDEX --archive SELECTED --out NEW_JSON` and original Git blobs with `verify_sources.py --repository REPO --index INDEX --selected SELECTED --expected-phases N --out NEW_JSON`. Archive/file hashes do not replace mathematical or hardware acceptance.
