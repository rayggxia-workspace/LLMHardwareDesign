# Shared 32 KiB native RTL validation

Issue #247. This experiment validates real 4 KiB SRAM macro instances, shared A
delivery and native P integration. The native datapath accepts 128-bit A
containers with S8 or S16 elements and 512-bit B beats. It does not implement
S32 A or turn the historical S32/S96 SystemC result into native token/s.

## Server execution

Use a new run directory under the authorized Melodydt server root. Include the
closed RTL/TB source set, `run.py`, `job.sh`, `analyze.py`, and all included M/G
headers in `inputs.json` / `source-files.sha256`. Record the actual source commit.
The runner verifies every declared source SHA and rejects missing required
sources. The real SRAM behavioral view and Liberty hashes are pinned in the
runner. No local EDA is permitted.

```bash
# From the packaged run directory, for the two standalone modules first:
sbatch --export=ALL,SHARED32_COMPONENTS=units,SHARED32_AREA=1 job.sh
# Complete integrated gate when the pair bench/source are present:
sbatch --export=ALL,SHARED32_COMPONENTS=all,SHARED32_AREA=1 job.sh
```

Both commands request four Slurm CPUs and bind the single task. The container
starts the native Verilator build with `--assert` and three initialization
settings `(reset_mode, seed) = (1,247), (2,247), (2,248)`. Each simulation receives
the same explicit `+SEED` for stimulus. Memory additionally runs the production
zero-write-ACK setting `ECHO_WRITE_DATA=0` once with `(1,247)`. Builds and runs have finite timeouts;
timeout terminates the complete spawned process group. Logs and partial JSON
receipts are preserved after each command and each passing seed.

Standalone pool and memory compilation is warning-fatal and uses the actual
macro, including its read/write phase timing. The existing integrated P closure
retains its old nonfatal warning policy, but missing or nonexistent ports are
rejected. Any old bench reused after adding production inputs must explicitly
tie those inputs off; warning suppression is not an acceptable substitute.

`POOL_PASS` and `POOL_MEASURE` report independent scoreboard coverage and physical
services, including deliberately rejected requests. `S16K_1R1W_PASS` and
`S16K_1R1W_MEASURE` report local read/write coverage and real concurrent service.
The pair bench reports `SHARED_PAIR_PASS` / `SHARED_PAIR_MEASURE`; integration
acceptance additionally depends on the bench's native integer numeric oracle,
backpressure, completion and release checks. A process exit alone is not a pass.

The pair builds all four shared-A/local-1R1W combinations, each with three
initializations. Every build executes native S8/B8, S16/B8 and S16/B16 cases,
three A rows, two K segments (including a partial final tile), and eight contexts.
Both P blocks run concurrently with different B contents and common A values.
The scalar integer oracle checks 3,456 raw, rounded and SRAM-readback values.
Shared descriptors cross the 16 KiB group boundary from word 1021; the S16/B8
case explicitly uses a shared prefix and a local suffix. Negative cases cover
epoch, range, shape and reading a released context. When local 1R1W is enabled,
a separate probe requires simultaneous physical wide read/write admission,
blocks writes into an owned B range, and checks the post-ACK SRAM contents.
The existing G/gated-SiLU program is not part of this new pair bench.

Lifecycle probes cover same-edge RELEASE/new shared LOAD, RELEASE one cycle
after a LOAD handshake, and RELEASE requested while both LOAD completions are
held. The new LOAD stays valid through RELEASE and EMPTY, and is accepted only
after refill and SEAL. RELEASE must await the old LOAD completion acknowledgments.
A common cold reset cancels two admitted P loads and the pool object; all
contents are reinitialized, operands are reloaded and 16 independent native
numeric checks confirm recovery. A rejected LOAD may already have changed part
of the operand bank; valid data must be fully reloaded before computation.
The interface does not promise atomic rollback of invalid LOADs.

Pair cycle counts include setup/fill, computed output ACKs, numeric readback,
context release and shared-object release. `compute_cycles` is separately
reported. The sparse boundary fixture deliberately fills unused prefix words;
these microbench numbers must not be used as a transformer speedup estimate.

## Area accounting

Only after all requested functional tests pass, `--area` synthesizes the shared
pool, the new local memory backend, the original plain backend, and actual R4 bank_rw backend using
Yosys and the same Nangate45 typical standard-cell library. Actual SRAM Liberty
cells are blackboxes. All three local backends use production ECHO_WRITE_DATA=0. The mapped netlist must contain eight, eight, four and four SRAM
instances respectively, with no remaining generic logic cells. Standard-cell
area and macro footprints remain separate. This is not placement, routing, STA,
power or chip-area qualification.

The local 1R1W implementation uses an LVT with two physical copies: 16 KiB logical
capacity consumes 32 KiB per P. For two P blocks, one unchanged 16 KiB U and a
shared 32 KiB pool, total physical SRAM is 112 KiB (28 banks), versus 48 KiB
(12 banks). Copying the existing bank footprint gives 2.5889374007 mm² versus
1.1095446003 mm²; the 1.4793928004 mm² increment excludes all standard cells and
interconnect. It must not be described as a real 1R1W macro or full-chip area.

## Results

`results/result.json` contains tool/source hashes, allocation, commands, logs,
all seed measurements, errors and area status. A requested area failure causes
the overall gate to fail while retaining `functional_passed` independently.
Pure JSON postprocessing may run locally:

```bash
python -B project/experiments/shared32_native/analyze.py \
  --result results/result.json --out analysis.json
```

No tests have been claimed passed by creating these files. The source-subset
development worktree lacks management templates by design; management validation
must be run separately in the complete formal repository before delivery.
