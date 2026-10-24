# Reference asset adapter, Issue 63

This is an offline reference importer, not final Block capability validation.
ACT20/MXU20 are old openTPU macro views; GEMM20 is an old llaccel macro view.
They do not represent two complete designs or the newer #55 physical base.

The original source and tests were recovered from chat text and matched their
previous SHA256 records. They were not compared with server files.
Subsequent local fixes prevent empty or unavailable catalogs from reporting pass;
the restored 29 tests passed first, and all 32 current tests then passed with no skips.
See `recovery_record.json` and `validation_record.json`. This continuation uses only the independently
created local repository and authenticated GitHub HTTPS; no server was contacted.

API:
- `import_assets(dependency_root, sources_path=None)`
- `validate_catalog(catalog, dependency_root=None)`
- `bind(catalog, request, physical=False, dependency_root=None)`

The source lock selects three exact LEFs. The importer checks original SHA/size
and preserves PIN/PORT/LAYER/RECT, OBS, raw micron strings and integer DBU.
Real catalog verification rereads the fixed original source, reparses it and
compares every geometry field. A caller cannot authenticate modified geometry
by updating its own hash. Missing original bytes give blocked, not pass.
Catalog-provided paths never select source files.

Bindings declare exact project/case/commit/run/master/file-SHA identities,
complete ordered bit vectors (scalar [null]), resource endpoints, direction,
protocol and format. Connections declare ordered bit pairs. Synthetic fixtures
have explicit logical contracts. The real LEF binding profile has no imported
protocol/format contract and remains blocked for those checks. Unknown logical
order is not silently accepted as verified order.

`reference_binding.example.json` checks the observed ACT pin named clk. Its raw
LEF says USE SIGNAL; its name is not proof of a qualified clock interface.
PR20 was acquired during local continuation and independently audited against
its old Yosys/LEF bit sources. This audit does not add a protocol to the binding
catalog, verify Liberty timing, or promote any old macro to the #55 version.

Physical requests remain blocked: no same-version frozen base, placed transform,
fixed M8 escape/landing identities, qualified vias, or PG/clock integrity proof
was acquired. M1-M8 are fixed; M9/M10 and qualified 8-9/9-10 vias are the custom
scope. M11/M12 are separate fallback. M5/M6 pins do not provide M8 access.

The unmodified `reference_lef_profile.py` comes from fixed PR18 and is SHA-checked
before use. The original ZIP files and full LEFs stay in ignored
`.local/dependencies/reference_assets`; only source locks, code and small summaries
are selected for GitHub. No runtime network calls or automatic downloads occur.

Actual local test command, from the repository root (PowerShell):
```powershell
$env:WORKLOAD_ASSET_ROOT = (Resolve-Path .local/dependencies/reference_assets).Path
python -B -m unittest discover -s project/analysis/workload_mapping -p test_assets.py -v
```
For task-local temporary files, set TMPDIR/TMP/TEMP to a new directory under
`.local/runs/` before running. Without WORKLOAD_ASSET_ROOT the real-source tests
are explicitly skipped; that is not a real-asset validation pass.

Offline import and independent selected PR20 bit audit:
```powershell
python -B project/analysis/workload_mapping/assets/replay_reference_import.py --reference-root .local/dependencies/reference_assets --output .local/runs/assets-import-new
```
The output directory must be new and inside this repository. The script emits
a deterministic selected summary and separate execution receipt. It does not
run the original PR18/PR20 entire pipelines or any EDA flow.
