# Server model completion and independent PR36 intake (Issue61)

User now authorizes this session to complete the formerly delegated model batch
on the existing CPU server. This supersedes the old wait-for-notification and
local-only scheduling restrictions for this task. No other member jobs/directories
are touched. Initial job replays existing actual tensors; it is not a full-model
rerun or CUDA measurement.

`experiment.json` fixes source commit, compressed input SHA, thresholds and scope.
`replay.py` uses Torch only for weights_only tensor loading; integer products use
NumPy INT64, recurrent updates use a separate NumPy FP64 implementation.
Floating QK normalization/exp/auxiliary reductions are explicit, not integer RTL.
Six adjacent captured state pairs must retain bit-equal final/initial values.
It verifies the saved windows, not every intervening long-sequence token.

```powershell
python scripts/check_project.py
<existing-local-venv-python> -B -m unittest discover -s project/experiments/server_models -p test_replay.py -v
```

After clean commit, bundle sources, binding and the three pinned gzip inputs.
Copy only to `/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023`;
verify archive SHA before extracting. `sbatch source/job.sh run01` requests8 CPUs
on c96, three parallel single-thread processes,20min limit. A new `run02` may
repeat it, never overwrite. Reuse the existing Issue53 CPU venv read-only.
Each result records versions, host, input SHA, source binding and measured time.
Record Slurm state/exit and return file SHA before reporting success.

The per-model acceptance ledger will distinguish actual/reusable/failed/blocked/
conditional-skip/not-executed. First reuse Qwen2.5/Qwen3.5 source evidence after
checking artifacts. Gemma text local/global/window/KV is primary; access and CPU
backend require checking, not silently substituting another model. Phi may be
captured/sealed, never used to tune partition strategy before freeze. Optional
12B/8B/R1-distill runs need explicit latest task scope and a decision they resolve.
Qwen3-4B is not automatically restored as mandatory. No original huge DeepSeek.
