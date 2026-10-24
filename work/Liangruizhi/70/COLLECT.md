# Issue70 evidence collector

Run only in the authorized server Issue70 root after dependent jobs finish:

```
python -B work/Liangruizhi/70/collect.py --root ISSUE70_ROOT \
  --out ISSUE70_ROOT/delivery01 --binding FROZEN_BINDING.json
```

Binding requires the actual40-character `commit` and `collect_sha256`. Output
must be new and under the Issue70 root. The standard-library tool enumerates only
the four named captures/numeric/diagnostic directories, `audit-*` (including
negative examples), `transport-*`, phase1..10 source capsules/bindings, root
`*.log`, and two permitted receipt filenames under models-relay/granite/falcon.
It rejects symlinks, path escapes, nonregular files and weight-file extensions.
No model weights are opened, parsed, hashed or archived.

`full-results.zip` uses ZIP_STORED; `contents.json` lists each original file's
bytes/SHA. Every archived member is streamed back and independently hashed after
writing. Names preserve the Issue70 root directory prefix. Collector and exact
binding are also included under `_collector/`.

`selected.zip` includes the Granite integer witnesses/metrics/manifests, small
Falcon projection/report/config/manifest, the24 calendars from final transport01
plus metrics/manifests, and the five specified final audit receipts. Large
Falcon/Granite captures stay in the full archive. Original manifests can refer to
omitted large files; selected delivery is explicitly partial, not a full replay
claim. Repeat02 calendars and earlier failures remain in the full archive.

`receipt.json` records archive sizes/SHA, frozen source, host and Slurm job.
Its status **ARCHIVE_BYTES_VERIFIED_ONLY** says nothing about model acceptance;
original FAIL/PARTIAL and scientific limitations remain unchanged. No archived
source/result is rewritten. Own stdout may gain the final receipt after the
snapshot; the archive index states this timing boundary.
