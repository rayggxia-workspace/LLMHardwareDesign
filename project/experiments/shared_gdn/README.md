# Issue109 reproducibility

All tensor math, RTL, mapping, raw gate and independent numerical reception run only on the already authorized server. PC runs management, AST and archive/source byte reception only. No model download or environment install.

Start with `python -B scripts/check_project.py`. Read [PROTOCOL.md](PROTOCOL.md) and `docs/experiments/issue-109-shared-gdn.md`. Full actual argv, source phases and Slurm IDs will be sealed in `work/Liangruizhi/109/execution.json`; use new output directories. `inputs.py` verifies original106/104 files and explicitly relocates only GDN metadata pointers; `run.py` builds/runs shared109 and maps the exact source; `receive.py` independently replays97/102/99/104 math and all GDN stages and published snapshots. `qualification.cpp` covers44 commands and RTL-only terminal Q injection. `gate.py` replays unchanged normal driver using actual mapped JSON and Liberty functions; behavioral store82 is retained, no Q injection or physical qualification.

`cost.py` checks unique actual dynamic S8/S32 inventory, constant49 address cell, SRAM shape, native mapped counts and Liberty area. `negative.py` changes actual numerical files and rehashes all artifacts before invoking fresh full receivers. `inventory_negative.py` rejects rehashed resource forgeries. `analyze.py` requires all receipts and exact raw gate/RTL rows/state/stages/protocol byte equality. `collect.py` seals full evidence on server and selected metadata/source in Git.

Byte-only PC reception after final archiving:

```text
python -B work/Liangruizhi/109/verify_delivery.py --index INDEX --archive SELECTED_ZIP --out NEW_RECEIPT
python -B work/Liangruizhi/109/verify_sources.py --repository REPO --index INDEX --selected SELECTED_ZIP --expected-phases 8 --out NEW_RECEIPT
```

Original failure/staging logs and superseded43command and final44command scopes remain archived. Failed2400s gate is not accepted evidence. Same-binary one6000s replay is explicitly bounded. Functional/mapped evidence does not cover SRAM macros, physical timing, power, routing or complete model quality.
