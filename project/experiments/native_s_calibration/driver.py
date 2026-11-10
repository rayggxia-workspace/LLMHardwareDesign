"""Eight same-work port diagnostics. No numerical/DDR/workload changes."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

PLANS = [
    ("legacy-Xreg", 0, 0, 1, 0, 1),
    ("legacy-NoPool", 4, 0, 1, 0, 1),
    ("P128-Xreg", 0, 1, 1, 0, 1),
    ("P128-NoPool", 4, 1, 1, 0, 1),
    ("all128-Xreg", 0, 2, 1, 0, 1),
    ("all128-NoPool", 4, 2, 1, 0, 1),
    ("all128-NoPool-response1-ACK2", 4, 2, 1, 1, 2),
    ("all128-NoPool-word2", 4, 2, 2, 0, 1),
]
if os.environ.get('NS_ROUND', 'reproduce') == 'native-1':
    PLANS = [('historical-NoPool', 4, 0, 1, 0, 1),
             ('width-only-NoPool', 4, 2, 1, 0, 1),
             ('G107-NoPool', 4, 2, 1, 0, 1),
             ('Kmajor-core12-guard0', 4, 2, 1, 0, 1),
             ('Kmajor-core12-guard3', 4, 2, 1, 0, 1),
             ('Kmajor-core12-guard7', 4, 2, 1, 0, 1),
             ('Kmajor-core12-guard11', 4, 2, 1, 0, 1),
             ('Kmajor-core12-guard3-response1', 4, 2, 1, 1, 1)]
if os.environ.get('NS_ROUND') == 'stripe-1':
    PLANS = [(name, 4, 2, 1, 0, 1) for name in (
        'Kmajor-guard3-reference', 'stripe16-guard3', 'stripe16-guard7',
        'stripe16-guard11', 'stripe8-guard3', 'stripe8-guard7',
        'stripe16-guard3-repeat', 'stripe16-guard7-repeat')]
if os.environ.get('NS_ROUND') == 'tile-1':
    PLANS = [(name, 4, 2, 1, 0, 1) for name in (
        'native128-spill-reference', 'candidate128-spill', 'candidate192-spill',
        'candidate128-stripe', 'candidate192-stripe', 'candidate192-stripe-guard7',
        'candidate192-spill-guard7', 'candidate192-spill-repeat')]
if os.environ.get('NS_ROUND') == 'lookahead-1':
    PLANS = [(name, 4, 2, 1, 0, 1) for name in (
        'tile192-spill-reference', 'tile192-spill-lookahead', 'tile192-spill-lookahead-balanced',
        'tile192-stripe-reference', 'tile192-stripe-lookahead', 'tile192-stripe-lookahead-balanced',
        'tile192-spill-lookahead-balanced-guard7', 'tile192-spill-lookahead-balanced-guard11')]
if os.environ.get('NS_ROUND') == 'product-1':
    PLANS = [(name, 4, 2, 1, 0, 1) for name in (
        'oldcore192stripe-reference', 'product192spill-quant95',
        'product192stripe-quant95', 'product192stripe-known60',
        'product192stripe-known60-credit4', 'product192stripe-known60-meta8',
        'product192stripe-known60-no-lookahead', 'product128stripe-known60')]
if os.environ.get('NS_ROUND') == 'consumer-1':
    PLANS = [(name, 4, 2, 1, 0, 1) for name in (
        'product192stripe-reference', 'early-consumer-stripe', 'Kmajor-image-codesign',
        'early-consumer-Kmajor-image', 'pipeline-2-16-reference', 'pipeline-2-16-early-consumer',
        'early-consumer-credit4', 'early-consumer-unbalanced')]
if os.environ.get('NS_ROUND') == 'G-overlap-1':
    PLANS = [(name, 4, 2, 1, 0, 1) for name in (
        'pipeline3-reference', 'pipeline3-G-overlap', 'pipeline3-G-overlap-barrier',
        'pipeline3-G-overlap-credit4', 'pipeline3-G-overlap-no-Alookahead',
        'oldpipeline-reference', 'oldpipeline-G-overlap', 'pipeline3-G-overlap128')]
if os.environ.get('NS_ROUND') == 'rf-II1-1':
    PLANS = [(name, 4, 2, 1, 0, 1) for name in (
        'oldRF-II3-reference', 'RFII1-preparse-gap1-candidate', 'RFII1-measured-guard-gap5',
        'RFII1-fast-guard-gap3-candidate', 'RFII1-gap5-no-G-overlap', 'RFII1-gap5-credit4',
        'RFII1-gap5-no-Alookahead', 'RFII1-gap1-no-G-overlap-candidate')]
name, mode, scope, word_cycles, response_cycles, ack = PLANS[int(os.environ["SLURM_PROCID"])]
# Singularity on this host resets inherited CPU affinity. Restore the exact
# srun allocation captured outside the container, then assert it again inside.
os.sched_setaffinity(0, {int(cpu) for cpu in os.environ['NS_AFFINITY_CSV'].split(',')})
affinity = sorted(os.sched_getaffinity(0))
assert len(affinity) == 12, affinity
HERE = Path.cwd()
out = HERE / name
out.mkdir(exist_ok=False)
base = {k: v for k, v in os.environ.items() if not k.startswith(("SQ_", "BN_", "CL_", "NV_", "SF_", "SX_", "NS_"))}
env = dict(base, SQ_DIRECT="1", SQ_ABITS="16", SQ_BREAD="128", SQ_PCOUNT="3",
           SQ_CORE_K="16", SQ_BEAT="64", SQ_STRIPE="1", BN_RELEASE="2", CL_MODE="6",
           CL_ISSUE="2", CL_BANKS="4", CL_HEAD_GROUP="16", NV_BITS="32", NV_EXTRA="1",
           NV_MID="1", SQ_BW_MB="51200", SX_MODE=str(mode), SX_DESC_CYCLES="2",
           SX_LATENCY="2", SX_LOCAL_WIDTH="16", SX_LOCAL_LATENCY=str(ack),
           SX_SLOTS="2", SX_RETIRE_CYCLES="1", SX_PHASE_CYCLES="4", SX_EARLY=str(int(mode == 4)),
           SX_A_SLOTS="2", SX_COPY_LATENCY=str(ack), NS_PORT_SCOPE=str(scope),
           NS_WORD_CYCLES=str(word_cycles), NS_RESPONSE_CYCLES=str(response_cycles))
if os.environ.get('NS_ROUND', 'reproduce') == 'native-1':
    rank = int(os.environ['SLURM_PROCID'])
    env.update(NS_NATIVE=str(0 if rank < 2 else 1 if rank == 2 else 3),
               NS_GUARD_CYCLES=str({3: 0, 4: 3, 5: 7, 6: 11, 7: 3}.get(rank, 3)),
               NS_CONTEXT_CYCLES='3')
if os.environ.get('NS_ROUND') == 'stripe-1':
    rank = int(os.environ['SLURM_PROCID'])
    env.update(NS_NATIVE=str(3 if rank == 0 else 4),
               NS_GUARD_CYCLES=str([3, 3, 7, 11, 3, 7, 3, 7][rank]),
               NS_RF_CONTEXTS=str(8 if rank in (4, 5) else 16),
               NS_CONTEXT_CYCLES='3')
if os.environ.get('NS_ROUND') == 'tile-1':
    rank = int(os.environ['SLURM_PROCID'])
    env.update(NS_NATIVE=str(3 if rank == 0 else 4),
               NS_GUARD_CYCLES=str(7 if rank in (5, 6) else 3),
               NS_RF_CONTEXTS='16', NS_CONTEXT_CYCLES='3',
               NS_SPILL=str(int(rank in (1, 2, 6, 7))),
               NS_PROJECT_COLS=str(192 if rank in (2, 4, 5, 6, 7) else 128))
if os.environ.get('NS_ROUND') == 'lookahead-1':
    rank = int(os.environ['SLURM_PROCID'])
    env.update(NS_NATIVE='4', NS_GUARD_CYCLES=str(7 if rank == 6 else 11 if rank == 7 else 3),
               NS_RF_CONTEXTS='16', NS_CONTEXT_CYCLES='3', NS_PROJECT_COLS='192',
               NS_SPILL=str(int(rank not in (3, 4, 5))),
               NS_A_PREFETCH=str(int(rank not in (0, 3))),
               NS_BALANCE=str(int(rank in (2, 5, 6, 7))))
if os.environ.get('NS_ROUND') == 'product-1':
    rank = int(os.environ['SLURM_PROCID'])
    env.update(NS_NATIVE='4', NS_GUARD_CYCLES='3', NS_CONTEXT_CYCLES='3',
               NS_RF_CONTEXTS='16', NS_PROJECT_COLS=str(128 if rank == 7 else 192),
               NS_SPILL=str(int(rank == 1)), NS_A_PREFETCH=str(int(rank != 6)), NS_BALANCE='1',
               NS_PRODUCT=str(int(rank != 0)), NS_QUANT=str(int(rank != 0)),
               NS_G_KNOWN_SHIFT=str(int(rank >= 3)), NS_DIR_REG=str(int(rank != 0)),
               NS_RECORD_CREDITS=str(4 if rank == 4 else 6), NS_SCALE_META_CYCLES=str(8 if rank == 5 else 4))
if os.environ.get('NS_ROUND') == 'consumer-1':
    rank = int(os.environ['SLURM_PROCID'])
    env.update(NS_NATIVE='4', NS_GUARD_CYCLES='3', NS_CONTEXT_CYCLES='3',
               NS_RF_CONTEXTS='16', NS_PROJECT_COLS='192', NS_SPILL='0', NS_A_PREFETCH='1',
               NS_BALANCE=str(int(rank != 7)), NS_PRODUCT='1', NS_QUANT='1', NS_G_KNOWN_SHIFT='1',
               NS_DIR_REG='1', NS_RECORD_CREDITS=str(4 if rank == 6 else 6), NS_SCALE_META_CYCLES='4',
               NS_EARLY_STRIPE=str(int(rank in (1, 3, 5, 6, 7))), NS_WEIGHT_LAYOUT=str(int(rank in (2, 3))),
               NS_ORDINARY_PIPE_EXTRA=str(2 if rank in (4, 5) else 0), NS_HEAD_PIPE_EXTRA=str(16 if rank in (4, 5) else 0),
               NS_HEAD_INPUT_EXTRA=str(8 if rank in (4, 5) else 0))
if os.environ.get('NS_ROUND') == 'G-overlap-1':
    rank = int(os.environ['SLURM_PROCID'])
    new_pipeline = rank not in (5, 6)
    env.update(NS_NATIVE='4', NS_GUARD_CYCLES='3', NS_CONTEXT_CYCLES='3',
               NS_RF_CONTEXTS='16', NS_PROJECT_COLS=str(128 if rank == 7 else 192), NS_SPILL='0',
               NS_A_PREFETCH=str(int(rank != 4)), NS_BALANCE='1', NS_PRODUCT='1', NS_QUANT='1', NS_G_KNOWN_SHIFT='1',
               NS_DIR_REG='1', NS_RECORD_CREDITS=str(4 if rank == 3 else 6), NS_SCALE_META_CYCLES='4',
               NS_EARLY_STRIPE=str(int(rank != 2)), NS_G_OVERLAP=str(int(rank not in (0, 5))),
               NS_ORDINARY_PIPE_EXTRA=str(2 if new_pipeline else 0), NS_HEAD_PIPE_EXTRA=str(16 if new_pipeline else 0),
               NS_HEAD_INPUT_EXTRA=str(8 if new_pipeline else 0))
if os.environ.get('NS_ROUND') == 'rf-II1-1':
    rank = int(os.environ['SLURM_PROCID'])
    env.update(NS_NATIVE='4', NS_GUARD_CYCLES='3', NS_CONTEXT_CYCLES='3',
               NS_RF_CONTEXTS='16', NS_PROJECT_COLS='192', NS_SPILL='0',
               NS_A_PREFETCH=str(int(rank != 6)), NS_BALANCE='1', NS_PRODUCT='1', NS_QUANT='1', NS_G_KNOWN_SHIFT='1',
               NS_DIR_REG='1', NS_RECORD_CREDITS=str(4 if rank == 5 else 6), NS_SCALE_META_CYCLES='4',
               NS_EARLY_STRIPE='1', NS_G_OVERLAP=str(int(rank not in (4, 7))),
               NS_ORDINARY_PIPE_EXTRA='2', NS_HEAD_PIPE_EXTRA=str(16 if rank == 0 else 2),
               NS_HEAD_INPUT_EXTRA=str(8 if rank == 0 else 0), NS_M_PROFILE_JOB=str(102202 if rank == 0 else 102228),
               NS_EXEC_GAP=str(1 if rank in (0, 1, 7) else 3 if rank == 3 else 5))
args = ["queued_pipe_w8", "prefix_pair_combine", "8", "1", "1", "16", "0", "4", "0", "1", "1", "1"]
trace = Path("/public/home/yuzelu/project-circuit/issue248-stream-quant-20261110-40/restored/inputs/decode512.trace")
report = dict(plan=name, passed=False, source_env={k: v for k, v in env.items() if k.startswith(("SQ_", "BN_", "CL_", "NV_", "SX_", "NS_"))},
              job=os.environ["SLURM_JOB_ID"], input_trace_SHA256=hashlib.sha256(trace.read_bytes()).hexdigest(), results=[],
              affinity=affinity, allocated_cpus_per_task=12,
              qualification="S128 sensitivity; operator/control pipelines and energy NOT fully calibrated")
report['round'] = os.environ.get('NS_ROUND', 'reproduce')


def save():
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")


try:
    if os.environ.get('NS_ROUND') in ('product-1', 'consumer-1', 'G-overlap-1', 'rf-II1-1'):
        check_env = dict(env, NS_CHECK_QUANT='1')
        with (out / 'measured-service-check.log').open('w') as log:
            subprocess.run([str(HERE / 'candidate.exe'), str(HERE / 'generated/micro.trace')] + args,
                           env=check_env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=True)
        assert 'QUANT_TRACE_MATCH fallback95 known60 read96 write32 owners2 source102168' in (out / 'measured-service-check.log').read_text()
        report['measured_quantizer_and_copy_selfcheck'] = True
    for label, current in (("micro", HERE / "generated/micro.trace"), ("decode512", trace)):
        with (out / (label + ".log")).open("w") as log:
            subprocess.run([str(HERE / "candidate.exe"), str(current)] + args, env=env,
                           stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=True)
        result = [json.loads(line[7:]) for line in (out / (label + ".log")).read_text().splitlines() if line.startswith("RESULT ")]
        assert len(result) == 1
        report["results"].append(dict(label=label, result=result[0]))
        save()
        print("CASE_PASS", name, label, result[0]["tokens_per_second"], flush=True)
    report["passed"] = True
    save()
except Exception as error:
    report["error"] = repr(error)
    save()
    raise
