# Standard command-pipeline regression

Required scenario: history512, token840, frozen-zero initial historical KV;
second decode consumes first decode's actual appended KV and sampled token.
No prefill; no 128-step decode; no history2 fixture substitution.

After the main task freezes and admits the new hardware/TLM contract:
1. Submit command_pipeline_compile.sbatch twice with arguments
   HISTORY OUTPUT HARDWARE SERVICES (HISTORY=512 and 513, OUTPUT=PLANS/HISTORY).
2. Submit command_pipeline_package.sbatch PLANS PACKAGES HARDWARE after both.
   The assembly builder is protected by flock because it writes shared generated RTL.
3. Submit command_pipeline_run.sbatch PACKAGES PLANS RUN_DIRECTORY after package.
   Both complete programs execute and each has an independent integer graph oracle.
4. command_pipeline_accept.py rejects disconnected state/token, wrong scenario,
   incomplete calls, failed 73-liveout comparison, or changed timing source/config.

The compile and package Python signatures were checked against the current
Frontend/select/materialize/package APIs. Fresh base was structurally admitted; complete history512/two-step run is tracked
in evidence/command-pipeline/full-decode512-two-step/jobs.json.
ActivationLoad production-model tests: job115392 passed; source:
tests/command_pipeline_activation.py; runner audits/command_pipeline_tests.sbatch.
These tests cover 15 burst/delay combinations, including deliberately reordered
DDR returns, and do not constitute full RTL equivalence or full-model acceptance.

Current execution framework installs each phase separately and materializes its
committed state into the next phase's address layout. External phase loading time
is excluded. The acceptance receipt states this explicitly; cumulative modeled
retirements are not a calibrated continuous hardware-request throughput result.

Base regeneration caution: build_projection_local_contract.py regenerates
endpoints but resets admission. Regenerate actual structure/assembly evidence
after source changes; do not edit stored hashes to bypass admission.

## Fresh admission (no frozen job-ID fallback)
- Run command_pipeline_controls.sbatch CONTROL_OUT SEED_HARDWARE to freeze
  pre-elaboration source hashes, elaborate all p/n/e parents, and admit the fresh XML.
- After a real full selected assembly, command_pipeline_seal.py binds the passed
  RTL behavior receipts to that assembly's exact source closure. Model-only weight
  tests cannot qualify hardware. Expected evidence fields: passed=true,
  evidence_kind=rtl_behavior or rtl_tlm_differential, source_sha256,
  verified_capabilities, testbench_sources, and execution-log hashes in evidence.
- build_shared_memory_inventory.py now requires --seed, --assembly-receipt,
  --control-receipt, --control-xml-directory, --capacity-evidence and --output.
  Memory/DMA generated metadata must already match source; no stale-hash bypass.
- The new hardware contains control_admission_evidence and service_pipeline.
  Algorithm entry now fails closed if fresh control evidence is absent.
- command_pipeline_submit.py validates the new base/scenario and submits the
  complete dependent regression/compile/package/two-step-execution chain.

Regression entry audits/command_pipeline_full_tests.sbatch runs production TLM
and real RTL command-pipeline tests, including shared read arbitration, activation
pair/cancel, source prefetch, weight credits, quantization, and dot caches.
Contract/causal-chain negative tests passed in job115408: serial capacity
mutations, missing/failed/model-only evidence, independent second decode, and
fixed second token are rejected. Synthetic fixtures test validation only.
No history2 speedup is accepted as a history512/two-step performance baseline.


Current fresh admission:
- p/n/e controls: job115466, final-controls/receipt.json.
- Whole selected assembly: job115465 XML, admitted by115468 after independent
  family-XML composition registration; all30 functional macros and9 LC IDs,
  hidden-macro negative case,86 source files.
- Behavioral seal: final-capacity.json; hardware.json base ID
  blockv2-mod-pr185-memory-3fa694340b33bf0b.
- Services: services.json contains9 controllers actually present in that assembly.
  The old rms_s32 controller is absent; RMS uses N plus rms_apply.
- Store:115446 real writer+wrapper tests cover double buffering,2 SRAM reads,
 1 DDR write, error/held-offer draining, wrong tag followed by actual ACK,
 cancellation and retained completion. Store TLM115426 covers1/2/8/128 bursts.
- Admission115479:10 production-boundary and causal-chain checks,17 Python files parsed.

Fresh regeneration uses explicit evidence arguments:
command_pipeline_freeze_base.sbatch CONTROL_DIRECTORY ASSEMBLY_DIRECTORY
SEED_HARDWARE OUTPUT_DIRECTORY RTL_PROOF_JSON...
The seed supplies inventory, not behavioral permission; fresh control XML,
assembly closure and behavioral proof hashes are required.
