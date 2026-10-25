# Issue104 complete two-head GDN

Read [PROTOCOL](PROTOCOL.md) and [report](../../../docs/experiments/issue-104-gdn-state.md). This is a standalone finite controller, not shared106/whole-model/physical signoff. All numerical inputs/reference/RTL/map/gate commands run only on the authorized CPU server. Use new output directories; never overwrite evidence.

## Local byte-only checks

Run `python -B scripts/check_project.py` first. AST parsing and `verify_archive.py` do not load tensors:

```text
python -B project/experiments/gdn_state/verify_archive.py --archive project/experiments/gdn_state/results/issue-104/selected.zip --index project/experiments/gdn_state/results/issue-104/index.json --kind selected --out D:/Projects/Codex/NEW_TASK/selected-byte-receipt.json
```

## Server replay

Root `R=/public/home/yuzelu/RuizhiLiang/issue104-gdn-state-20261025`, Python `/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python`. Frozen tool entry `R/phase8/project/experiments/gdn_state`. Phase source.zip/binding.json retains original Git source bytes. Exact argv and Slurm jobs are in work104/execution.json and full.zip; wrap commands in only own `lrz-i104-*` Slurm job, independent output. No new models/tools required.

```bash
python -B "$R/phase8/project/experiments/gdn_state/run.py" build --out "$R/NEW_BUILD"
python -B "$R/phase8/project/experiments/gdn_state/run.py" sim --input "$R/input-native3201" --build "$R/NEW_BUILD" --out "$R/NEW_NATIVE" --steps 32 --stall 0
python -B "$R/phase8/project/experiments/gdn_state/verify.py" --input "$R/input-native3201" --run "$R/NEW_NATIVE" --out "$R/NEW_RECEIVE"
```

Portable12 uses `input-portable1201` / `--steps 12`; protocol uses native input, `--mode protocol --steps 2`. Modes do not change core inventory. Per-command stages.bin is `<6I2q`: record,attempt,kind,head,pair,K-index,lo,hi; actual.bin snapshot is root16+metadata64+state131072+Y2048=133200B. Kind0 prediction/1 residual/2 correction/3 proposal/4 Y. Independent receiver consumes complete records and partial prefixes only for known abort outcomes.

Final build02 (RTL d1297fe), real/map phase3, gate prepare/build phase4, actual gate phase5/6, strict receive phase6/7, archive phase8. `gate.py prepare` requires actual map plus accepted continuous portable12 receipt; it derives actual before-state for normal/rescale checkpoint. Gate wrapper uses original store82 behavior with mapped logic. 1200s per checkpoint limit; generation injection exists only in separate control_test.py RTL test.

Formal receipts: strict-{native32,portable12,protocol}-s{0,1}-01; strict-{rtl,gate}-{first,rescale}-s{0,1}-01; cost01 includes re-received14×2 boundaries. Wide01/control01/negative01 supplement function and receiver checks. Full raw large package remains authorized server; selected.zip is metadata/source evidence, not a replacement numerical run.

## Mixed-domain priority supplement

Use current reference (5539590+): any head shift>62 rejects E_FORMAT before either numeric WIDTH rescale, at every attempt. Two complete nonzero checkpoints with shifts[63,-33]/[-33,63] were executed quiet/held against unchanged build02 and independently received; no publication or retry. Main frozen archive intentionally retains old reference; receive additional `results/issue-104/priority-supplement` using `work/Liangruizhi/104/verify_priority_archive.py --kind selected`. Full supplement remains server priority-delivery01, scientific source phase9/e664827; no unaffected gate rerun.
