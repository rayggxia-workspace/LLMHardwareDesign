# Five-block native local control

This integration reuses the #180 mother controller, local PC, program memory interface,
image codec and task/response protocol. It adds a bounded native execution profile
for P16, U16, C16, F16 and J16. Native commands retire on the block's own result
or writeback. A static word link pins the source until the destination SRAM
reports storage. The receive reservation is independent of the local service wait.

## Source staging

From the repository root with the pinned #180, #189 and #190 Git objects available:

```text
python -B project/control_native_v1/stage.py . <bundle>/staged --qualified-s <qualified-source>
```

Copy this directory to `<bundle>/design`. The qualified source is the #186 SRAM
acceptance source tree used by #190. The staging script derives P4/N4 SRAM wrappers
from its generator and checks the common leaf RTL against #189. The run checks
the accepted OpenRAM Verilog bank SHA-256 before compilation. The staged copies
are reproducible input artifacts and should stay outside the repository.

## RTL regression

On Slurm, change to the uploaded bundle directory and submit one array. Each
element builds a native test harness and writes independent logs and a source
manifest. The pair element runs normal, request/ACK backpressure, native-command
error and coordinated reset with an SRAM response pending. The other elements
exercise F activation and elementwise writeback, P feeder/M/G writeback, and J
two-branch join and lease release.

```bash
sbatch --job-name=yzl-lc193 --partition=c64 --array=0-3%6 \
  --ntasks=1 --cpus-per-task=10 --time=00:30:00 design/slurm.sh
sbatch --job-name=yzl-lc193 --partition=c96 --array=0-3%8 \
  --ntasks=1 --cpus-per-task=12 --time=00:30:00 design/slurm.sh
```

Use one partition per regression sweep. The harness preloads operands, installs and
reads back program memory, and checks real native SRAM transactions. The C/U
payload rides the synthesizable transport, with only ready/valid stalls applied
by the fixture. The initial static link profile covers one word per direction
at a time, with coordinated endpoint reset. The regression does not establish
nine-instance integration, native layout, or parent-layer timing.
