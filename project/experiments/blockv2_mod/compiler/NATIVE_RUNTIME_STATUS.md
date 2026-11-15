> Architecture review 2026-11-15: previous flow is diagnostic pending PR185 correction. See evidence/architecture-revision-185/REVIEW.md. Wrapper ports and group positions are not physical endpoint evidence.

# Native package execution boundary

The default two-input entry now invokes native graph selection and machine packaging.
The runtime loader in native_package_runtime.py consumes sealed binary pages and
descriptors only. It accepts a shared scheduler and explicit hardware-service providers;
it does not consume the operator graph or perform mapping.

Evidence: native-binary-114224 passed PR260's actual mother instruction interpreter
over all five binary pages, 139828 CALLs, and 259426 control actions. The observed
trace exactly matched the selected control DAG. This test deliberately does not
model service completion time, arithmetic, or physical controller generations.

Open execution work:
- Bind hardware resource instances and parameterized SRAM interfaces to providers.
- Model counted DLC1/DSC1, dynamic Gather, GSM1 and explicit ranged PFED services.
- Projection must consume the separately issued PFED stream. The older PR260
  Projection default internally reads/quantizes/copies its source; using that
  default would bypass the generated U instructions and is not acceptable.
- Preserve real MC/LC job and session identities over page installation.
- Supply explicit runtime inputs and weights (or explicitly labeled diagnostic data).
- Execute fast prefill and cached decode scenarios; current two-token graph does
  not itself prove cached decode.

All delivery statuses remain false until end-to-end execution evidence exists.

Execution integration added:
- native_streamed_projection.py joins explicit ranged PFED calls to the active P scope.
  Job 114235 verified full K=11008 with six ranges and 86 released windows against
  independent synthetic-matrix arithmetic. It is not a full-graph result.
- native_provider_registry.py admits routes from the packaged hardware and checks
  every selected U/P wire endpoint. Job 114236 bound all 139828 descriptors.
- Native machine packages now include sealed hardware.json from the selected plan.
- run_native_package.py executes all pages on one persistent PR260 scheduler,
  DRAMsim3 instance pair, SRAM set, and provider registry. Job 114238 is the first
  complete-package execution attempt. Read its live handle/log/receipt for status.
- This run uses explicitly synthetic zero input/weight images with valid packed
  scales. It is not Qwen numerical validation. Exact arithmetic memoization does
  not remove DDR or SRAM transactions.
- PM installation and MC/LC generation handoff are not modeled by this run;
  output timing is uncalibrated service execution time, not end-to-end throughput.

Page deployment:
- native_deployment.py now emits explicit LC program installation and MC page
  ready/valid configuration sequences, including actual PM readback, per-page
  LC session generations, and persistent MC per-target CALL sequence ranges.
- Package 114250 includes this recipe. It does not silently reload local kernels.
- Job 114251 replayed all five actual MC binary pages on mc_native_controller RTL
  and its PM model: 139828 CALLs, five results, zero protocol faults. Every target
  and descriptor address was compared with the generated package.
- This MC test uses timed LC peer fixtures. It does not certify real LC session
  handshakes or the full U/P datapath; those remain separate acceptance items.

LC page-session evidence:
- Job 114263 replayed the entire package across four actual native LC instances.
  Each installed the same kernel once, then accepted all five session generations.
  All 139828 descriptors were fetched/CRC-checked and matched at the service port;
  279656 physical DDR beat responses and all terminal identities were checked.
- This is sequential LC control replay with finite service peers, not combined
  simultaneous MC/LC arithmetic execution. MC and TLM evidence remain separate.

Cached decode work:
- Added explicit U load/store candidates for Concat. KV concatenation is a real
  allocated output and real transfer sequence, not a free alias.
- Attention operand recipes now derive visible prefix length from the source
  mask, allowing distinct query/KV lengths without assuming token+1.
- Full cached-decode ONNX export/check is job 114276; full prefill compilation
  regression is job 114277. Check actual receipts before claiming either passed.

Cached decode complete graph:
- Job 114276 exported the entire model with 72 past K/V inputs and 73 outputs.
  Its 2572-node ONNX passed FP32 HF/ORT checks and comparison of cached logits
  against uncached [1,2,3] execution. This is frontend, not macro numerical proof.
- Job 114287 compiled that graph through the same two-input native Algo1 entry:
  615 selected compute/copy tasks, 540 views, 61706 calls, four MC pages.
  The extra 72 tasks are explicit KV Concat copies.
- Job 114288 executes the generated decode package with frozen zero diagnostic
  past KV. It is not a prefill-generated-KV continuity or real-weight test.
- Job 114289 checks all actual decode binary control instructions against its plan.
