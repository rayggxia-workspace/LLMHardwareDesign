# Partial native U-region calibration

Run on Slurm using `python3 -B source/project/experiments/u_queue_model/run.py --root "$PWD"`.
Freeze the run42 generated SystemC model, its inputs and result, and the run45
native receipts. Check every deployment/input SHA before execution.

Five cases 脳 four original workloads 脳 shared/idealdual = 40 runs. Sixteen
complete historical RESULT controls must match after removing only the new
evidence field. There are 200 deliberate negative accounting checks. All cases
retain 300 MHz, DDR 17.1 GB/s, shared32KiB, A32B/cycle and the original finite
resource limits. No whole-model RTL or numerical inference claim is made.

For the 36 prefill S16-to-S32 NExp regions (22016 values each), replace old
vector/NExp/S local fees with the measured staged 64-value U-region period
(186 cycles plus one response retirement cycle). Cache/DDR accesses remain.
Input staging/DDR and output eviction are still accounted by the model; native
testbench host staging/checking delays are excluded. The reserved U service
includes its N core and actual single-outstanding S arbiter. Do not charge it
again as separate E/N/S work. All other graph operations retain old conditional
fees. Actual activation values and quantization calibration are unavailable;
the native Q5.10 data is explicitly constructed.

The trace audit finds zero directly eligible pure S16 E operations. Queue depths
0/2/4 therefore receive no extra graph-level E speed credit; their equal model
results are checked. Native command-level gains are reported separately. S32 E
support or a verified conversion/packing graph is a future implementation.
