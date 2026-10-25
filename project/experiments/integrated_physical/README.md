# Actual integrated kernel physical evidence

Issue98 executes immutable upstream93/97 admission, exact gate replay, source-bound inventory, then bounded placement/RC/CTS/routing with independent reception. Current actual progress and limitations are in [the experiment report](../../../docs/experiments/issue-98-integrated-physical.md). Frozen policies and revisions are in [PROTOCOL.md](PROTOCOL.md).

Run only on the authorized server with a source binding and8CPU Slurm allocation. Entrypoints include `prepare.py`, `gate.py`, `flow.py`, `receive_gate.py`, `receive_physical.py`, and `negative.py`. Each requires its explicitly named input/output paths; never overwrite an earlier result directory. Complete commands, source commits and SHA are saved with every execution.

A reception PASS verifies evidence, not automatic timing closure. No full-core Fmax, real SRAM or manufacturing qualification is implied.
