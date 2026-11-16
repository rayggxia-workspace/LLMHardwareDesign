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
if os.environ.get('NS_ROUND')=='dynamic15-1':
    PLANS=[(name,4,2,1,0,1) for name in (
        'historical-dynamic-placeholder-reference','measured15-ideal-3P','measured15-observedstress-3P',
        'measured15-ideal-2P','measured15-observedstress-2P','measured15-ideal-1P',
        'measured15-observedstress-1P','measured15-ideal-3P-repeat')]
if os.environ.get('NS_ROUND')=='native-dot-1':
    PLANS=[(name,4,2,1,0,1) for name in (
        'native32-placeholder-reference','native32-4lane-staged','native32-8lane-staged','native32-16lane-staged',
        'native32-16lane-A-resident','native32-16lane-AB-resident','native32-16lane-AB-two-raw-slots',
        'native32-16lane-AB-two-raw-slots-pressure')]
if os.environ.get('NS_ROUND')=='native-dot-stage64':
    PLANS=[(name,4,2,1,0,1) for name in (
        'old-stage-16lane-AB-two-slots','stage64-16lane-cold-two-slots',
        'stage64-16lane-A-two-slots','stage64-16lane-AB-two-slots',
        'stage64-16lane-AB-one-slot','stage64-16lane-AB-two-slots-source-pressure',
        'stage64-16lane-AB-two-slots-all-pressure','stage64-8lane-AB-two-slots')]
if os.environ.get('NS_ROUND')=='native-dot-av-wave':
    PLANS=[(name,4,2,1,0,1) for name in (
        'stage64-serial-AV-reference','AV-S80-pair-wave1','AV-S80-pair-wave2',
        'AV-S80-pair-wave1-serial-checkpoint','AV-S80-pair-wave2-serial-checkpoint',
        'AV-S80-pair-wave2-one-source-slot','AV-S80-pair-wave2-source-pressure',
        'AV-S80-pair-wave2-all-pressure')]
if os.environ.get('NS_ROUND')=='native-dot-M2':
    PLANS=[(name,4,2,1,0,1) for name in (
        'single-M-serial-AV-reference','single-M-wave-AV-reference','M2-guard15-serial-AV',
        'M2-guard15-wave-AV','M2-guard15-wave-AV-stage-pressure','M2-guard15-wave-AV-all-pressure',
        'M2-guard15-wave-AV-serial-checkpoint','M2-guard15-wave-AV-first-DDR-offer')]
if os.environ.get('NS_ROUND')=='native-dot-refill':
    PLANS=[(name,4,2,1,0,1) for name in (
        'old-serial-AV','refill-serial-AV','old-wave-AV','refill-wave-AV',
        'refill-wave-first-DDR-offer','refill-wave-stage-pressure','refill-wave-all-pressure',
        'refill-wave-serial-checkpoint')]
if os.environ.get('NS_ROUND')=='measured-three-P-FFN':
    PLANS=[(name,4,2,1,0,1) for name in (
        'prior-modeled-serial-AV','prior-modeled-wave-AV','measured-serial-serial-AV',
        'measured-four-W-serial-AV','measured-four-W-wave-AV','measured-four-W-pressured-FFN-wave-AV',
        'measured-four-W-all-pressure','measured-four-W-median-FFN-wave-AV')]
if os.environ.get('NS_ROUND')=='measured-S80':
    PLANS=[(name,4,2,1,0,1) for name in (
        'wave2-historical','wave2-measured-S80','wave2-pressure-historical',
        'wave2-pressure-measured-S80','wave1-measured-S80','wave1-historical',
        'serial-AV-reference','wave2-measured-S80-FFN-pressure')]
if os.environ.get('NS_ROUND')=='programmed-FFN':
    PLANS=[(name,4,2,1,0,1) for name in (
        'unprogrammed-FFN','programmed-baseline','programmed-early','programmed-baseline-pressure',
        'programmed-early-pressure','programmed-early-median','programmed-early-FFN-pressure','programmed-early-serial-AV')]
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
if os.environ.get('NS_ROUND') in ('rf-II1-1','dynamic15-1','native-dot-1','native-dot-stage64','native-dot-av-wave','native-dot-M2','native-dot-refill','measured-three-P-FFN','measured-S80','programmed-FFN'):
    rank = int(os.environ['SLURM_PROCID'])
    env.update(NS_NATIVE='4', NS_GUARD_CYCLES='3', NS_CONTEXT_CYCLES='3',
               NS_RF_CONTEXTS='16', NS_PROJECT_COLS='192', NS_SPILL='0',
               NS_A_PREFETCH=str(int(rank != 6)), NS_BALANCE='1', NS_PRODUCT='1', NS_QUANT='1', NS_G_KNOWN_SHIFT='1',
               NS_DIR_REG='1', NS_RECORD_CREDITS=str(4 if rank == 5 else 6), NS_SCALE_META_CYCLES='4',
               NS_EARLY_STRIPE='1', NS_G_OVERLAP=str(int(rank not in (4, 7))),
               NS_ORDINARY_PIPE_EXTRA='2', NS_HEAD_PIPE_EXTRA=str(16 if rank == 0 else 2),
               NS_HEAD_INPUT_EXTRA=str(8 if rank == 0 else 0), NS_M_PROFILE_JOB=str(102202 if rank == 0 else 102228),
               NS_EXEC_GAP=str(1 if rank in (0, 1, 7) else 3 if rank == 3 else 5))
if os.environ.get('NS_ROUND')=='dynamic15-1':
    rank=int(os.environ['SLURM_PROCID'])
    env.update(NS_HEAD_PIPE_EXTRA='2',NS_HEAD_INPUT_EXTRA='0',NS_M_PROFILE_JOB='102228',NS_EXEC_GAP='5',
               NS_G_OVERLAP='1',NS_A_PREFETCH='1',NS_RECORD_CREDITS='6',
               NS_DYNAMIC=str(int(rank!=0)),NS_DYNAMIC_PCOUNT=str(2 if rank in (3,4) else 1 if rank in (5,6) else 3),
               NS_DYNAMIC_RECORD_CYCLES=str(1483 if rank in (2,4,6) else 1256))
if os.environ.get('NS_ROUND')=='native-dot-1':
    rank=int(os.environ['SLURM_PROCID'])
    env.update(NS_HEAD_PIPE_EXTRA='2',NS_HEAD_INPUT_EXTRA='0',NS_M_PROFILE_JOB='102228',NS_EXEC_GAP='5',
               NS_G_OVERLAP='1',NS_A_PREFETCH='1',NS_RECORD_CREDITS='6',NS_NATIVE_DOT=str(int(rank!=0)),
               NS_DOT_ROWS=str([1,1,2,4,4,4,4,4][rank]),NS_DOT_REUSE=str(2 if rank>=5 else 1 if rank==4 else 0),
               NS_DOT_RAW_SLOTS=str(2 if rank>=6 else 1),NS_DOT_PRESSURE=str(int(rank==7)))
if os.environ.get('NS_ROUND')=='native-dot-stage64':
    rank=int(os.environ['SLURM_PROCID'])
    env.update(NS_HEAD_PIPE_EXTRA='2',NS_HEAD_INPUT_EXTRA='0',NS_M_PROFILE_JOB='102228',NS_EXEC_GAP='5',
               NS_G_OVERLAP='1',NS_A_PREFETCH='1',NS_RECORD_CREDITS='6',NS_NATIVE_DOT='1',
               NS_DOT_ROWS=str(2 if rank==7 else 4),NS_DOT_REUSE=str(0 if rank==1 else 1 if rank==2 else 2),
               NS_DOT_RAW_SLOTS=str(1 if rank==4 else 2),NS_DOT_PRESSURE=str(int(rank==6)),
               NS_DOT_STAGE64=str(int(rank!=0)),NS_DOT_STAGE_PRESSURE=str(int(rank in (5,6))))
if os.environ.get('NS_ROUND')=='native-dot-av-wave':
    rank=int(os.environ['SLURM_PROCID'])
    env.update(NS_HEAD_PIPE_EXTRA='2',NS_HEAD_INPUT_EXTRA='0',NS_M_PROFILE_JOB='102228',NS_EXEC_GAP='5',
               NS_G_OVERLAP='1',NS_A_PREFETCH='1',NS_RECORD_CREDITS='6',NS_NATIVE_DOT='1',
               NS_DOT_ROWS='4',NS_DOT_REUSE='2',NS_DOT_STAGE64='1',
               NS_DOT_RAW_SLOTS=str(1 if rank==5 else 2),NS_DOT_PRESSURE=str(int(rank==7)),
               NS_DOT_AV_CKPT_PAIRS=str(0 if rank==0 else 1 if rank in (1,3) else 2),
               NS_DOT_CKPT_REQ_GAP=str(3 if rank in (3,4) else 1),NS_DOT_STAGE_PRESSURE=str(int(rank in (6,7))))
if os.environ.get('NS_ROUND')=='native-dot-M2':
    rank=int(os.environ['SLURM_PROCID'])
    env.update(NS_HEAD_PIPE_EXTRA='2',NS_HEAD_INPUT_EXTRA='0',NS_M_PROFILE_JOB=str(102480 if rank>=2 else 102228),NS_EXEC_GAP='5',
               NS_G_OVERLAP='1',NS_A_PREFETCH='1',NS_RECORD_CREDITS='6',NS_NATIVE_DOT='1',
               NS_DOT_ROWS='4',NS_DOT_REUSE='2',NS_DOT_STAGE64='1',NS_DOT_RAW_SLOTS='2',
               NS_DOT_PRESSURE=str(int(rank==5)),NS_DOT_AV_CKPT_PAIRS=str(0 if rank in (0,2) else 2),
               NS_DOT_CKPT_REQ_GAP=str(3 if rank==6 else 1),NS_DOT_STAGE_PRESSURE=str(int(rank in (4,5))),
               NS_M2_SHORT_GUARD=str(int(rank>=2)),NS_M2_FIRST_W_OFFER=str(int(rank==7)))
if os.environ.get('NS_ROUND')=='native-dot-refill':
    rank=int(os.environ['SLURM_PROCID'])
    env.update(NS_HEAD_PIPE_EXTRA='2',NS_HEAD_INPUT_EXTRA='0',NS_M_PROFILE_JOB='102480',NS_EXEC_GAP='5',
               NS_G_OVERLAP='1',NS_A_PREFETCH='1',NS_RECORD_CREDITS='6',NS_NATIVE_DOT='1',
               NS_DOT_ROWS='4',NS_DOT_REUSE='2',NS_DOT_STAGE64='1',NS_DOT_RAW_SLOTS='2',
               NS_DOT_PRESSURE=str(int(rank==6)),NS_DOT_AV_CKPT_PAIRS=str(0 if rank in (0,1) else 2),
               NS_DOT_CKPT_REQ_GAP=str(3 if rank==7 else 1),NS_DOT_STAGE_PRESSURE=str(int(rank in (5,6))),
               NS_M2_SHORT_GUARD='1',NS_M2_FIRST_W_OFFER=str(int(rank==4)),NS_DOT_REFILL_NEXT=str(int(rank not in (0,2))))
if os.environ.get('NS_ROUND')=='measured-three-P-FFN':
    rank=int(os.environ['SLURM_PROCID'])
    env.update(NS_HEAD_PIPE_EXTRA='2',NS_HEAD_INPUT_EXTRA='0',NS_M_PROFILE_JOB='102480',NS_EXEC_GAP='5',
               NS_G_OVERLAP='1',NS_A_PREFETCH='1',NS_RECORD_CREDITS='6',NS_NATIVE_DOT='1',
               NS_DOT_ROWS='4',NS_DOT_REUSE='2',NS_DOT_STAGE64='1',NS_DOT_RAW_SLOTS='2',
               NS_DOT_PRESSURE=str(int(rank==6)),NS_DOT_AV_CKPT_PAIRS=str(0 if rank in (0,2,3) else 2),
               NS_DOT_STAGE_PRESSURE=str(int(rank==6)),NS_M2_SHORT_GUARD='1',NS_DOT_REFILL_NEXT='1',
               NS_FFN_REPLAY=str(0 if rank<2 else 1 if rank==2 else 2),
               NS_FFN_TRACE_MODE=str(int(rank in (5,6))),NS_FFN_TRACE_SAMPLE=str(int(rank==7)))
if os.environ.get('NS_ROUND')=='measured-S80':
    rank=int(os.environ['SLURM_PROCID'])
    env.update(NS_HEAD_PIPE_EXTRA='2',NS_HEAD_INPUT_EXTRA='0',NS_M_PROFILE_JOB='102480',NS_EXEC_GAP='5',
               NS_G_OVERLAP='1',NS_A_PREFETCH='1',NS_RECORD_CREDITS='6',NS_NATIVE_DOT='1',
               NS_DOT_ROWS='4',NS_DOT_REUSE='2',NS_DOT_STAGE64='1',NS_DOT_RAW_SLOTS='2',
               NS_DOT_PRESSURE=str(int(rank in (2,3))),NS_DOT_AV_CKPT_PAIRS=str(0 if rank==6 else 1 if rank in (4,5) else 2),
               NS_DOT_STAGE_PRESSURE=str(int(rank in (2,3))),NS_M2_SHORT_GUARD='1',NS_DOT_REFILL_NEXT='1',
               NS_FFN_REPLAY='2',NS_FFN_TRACE_MODE=str(int(rank==7)),NS_DOT_CKPT_MEASURED=str(int(rank in (1,3,4,7))))
if os.environ.get('NS_ROUND')=='programmed-FFN':
    rank=int(os.environ['SLURM_PROCID'])
    pressure=str(int(rank in (3,4)))
    env.update(NS_HEAD_PIPE_EXTRA='2',NS_HEAD_INPUT_EXTRA='0',NS_M_PROFILE_JOB='102480',NS_EXEC_GAP='5',
               NS_G_OVERLAP='1',NS_A_PREFETCH='1',NS_RECORD_CREDITS='6',NS_NATIVE_DOT='1',
               NS_DOT_ROWS='4',NS_DOT_REUSE='2',NS_DOT_STAGE64='1',NS_DOT_RAW_SLOTS='2',
               NS_DOT_PRESSURE=pressure,NS_DOT_AV_CKPT_PAIRS=str(0 if rank==7 else 2),
               NS_DOT_STAGE_PRESSURE=pressure,NS_M2_SHORT_GUARD='1',NS_DOT_REFILL_NEXT='1',NS_DOT_CKPT_MEASURED='1',
               NS_FFN_REPLAY=str(2 if rank==0 else 3 if rank in (1,3) else 4),
               NS_FFN_TRACE_MODE=str(int(rank in (3,4,6))),NS_FFN_TRACE_SAMPLE=str(int(rank==5)))
args = ["queued_pipe_w8", "prefix_pair_combine", "8", "1", "1", "16", "0", "4", "0", "1", "1", "1"]
trace = Path("/public/home/yuzelu/project-circuit/issue248-stream-quant-20261110-40/restored/inputs/decode512.trace")
report = dict(plan=name, passed=False, source_env={k: v for k, v in env.items() if k.startswith(("SQ_", "BN_", "CL_", "NV_", "SX_", "NS_"))},
              job=os.environ["SLURM_JOB_ID"], input_trace_SHA256=hashlib.sha256(trace.read_bytes()).hexdigest(), results=[],
              affinity=affinity, allocated_cpus_per_task=12,
              qualification="S128 sensitivity; operator/control pipelines and energy NOT fully calibrated")
report['round'] = os.environ.get('NS_ROUND', 'reproduce')
if report['round'] in ('native-dot-1','native-dot-stage64','native-dot-av-wave','native-dot-M2','native-dot-refill'):
    report['qualification']='Full-scope timing diagnostic; exact native S32 service RTL fees, bounded source candidates, conditional E/N/LC/physical/energy.'
if report['round']=='measured-three-P-FFN':
    report['qualification']='SystemC sequential phase replay of measured three-P FFN plus separate modeled source, export and other operators. No interfering DMA descriptor measured, no numerical or energy qualification.'
if report['round']=='measured-S80':
    report['qualification']='Measured three-P FFN phases and live checkpoint primitive replay, modeled paired-B and control. No complete AV RTL, 300MHz physical, numerical or energy qualification.'
if report['round']=='programmed-FFN':
    report['qualification']='Measured programmed FFN and live S80 primitive phase replay. Source entry, export, unrelated DMA and remaining operators are modeled separately; no whole-model numerical, physical or energy qualification.'


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
    traces = (("micro", HERE / "generated/micro.trace"), ("decode512", trace))
    for label, current in traces:
        current_env = dict(env, NS_FFN_REPLAY='0') if label=='micro' and env.get('NS_FFN_REPLAY','0')!='0' else env
        with (out / (label + ".log")).open("w") as log:
            subprocess.run([str(HERE / "candidate.exe"), str(current)] + args, env=current_env,
                           stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=True)
        result = [json.loads(line[7:]) for line in (out / (label + ".log")).read_text().splitlines() if line.startswith("RESULT ")]
        assert len(result) == 1
        if report['round']=='measured-S80' and label=='decode512':
            native=result[0]['native_service']
            checkpoint=int(env['NS_DOT_AV_CKPT_PAIRS'])!=0
            exact=env['NS_DOT_CKPT_MEASURED']=='1'
            assert native['dynamic_s32_AV_checkpoint_primitive_RTL_job']==(102600 if exact else 0)
            assert not native['dynamic_s32_AV_checkpoint_RTL_qualified']
            fee=(81 if env['NS_DOT_PRESSURE']=='1' else 56) if exact else 62
            frames=36*2*16*2*3 if checkpoint else 0
            assert native['dynamic_s32_AV_S80_snapshot_service_cycles']==frames*fee
        if report['round']=='programmed-FFN' and label=='decode512':
            ff=result[0]['FFN_measured_replay']
            assert ff['job']==(102564,102604,102603)[int(env['NS_FFN_REPLAY'])-2] and ff['layers']==36
            if ff['job'] in (102604,102603):
                assert ff['actual_programmed_calls']==36*192 and ff['actual_programmed_DDR_read_bytes']==36*71884800
                assert ff['actual_programmed_local_write_receipt_bytes']==36*96256
        if report['round'] in ('native-dot-1','native-dot-stage64','native-dot-av-wave','native-dot-M2','native-dot-refill') and label=='decode512' and env['NS_NATIVE_DOT']=='1':
            native=result[0]['native_service']
            assert native['dynamic_s32_MACs']==73728*128*8 and native['dynamic_s32_calls']==72*3
            assert native['dynamic_s32_S_peak_B']<=16384 and native['dynamic_s32_peak_raw_slots']<=3*int(env['NS_DOT_RAW_SLOTS'])
            if env.get('NS_DOT_STAGE64')=='1':
                assert max(native['dynamic_s32_landing_peak_by_channel'])<=3
                assert native['dynamic_s32_landing_B']==native['dynamic_s32_read_bus_B']
            if int(env.get('NS_DOT_AV_CKPT_PAIRS','0')):
                assert native['dynamic_s32_AV_checkpoint_candidate'] and not native['dynamic_s32_AV_checkpoint_RTL_qualified']
                assert native['dynamic_s32_AV_S80_saves']==native['dynamic_s32_AV_S80_restores']==36*2*16*2*3
                assert native['dynamic_s32_AV_S80_snapshot_S_words']==2*22*native['dynamic_s32_AV_S80_saves']
                assert native['dynamic_s32_AV_paired_DDR_beats']==36*2*8*512
            if env.get('NS_M2_SHORT_GUARD')=='1':
                assert native['M2_short_guard_candidate_EXECs']>0 and not native['M2_short_guard_P2_qualified']
        report["results"].append(dict(label=label, result=result[0]))
        save()
        print("CASE_PASS", name, label, result[0]["tokens_per_second"], flush=True)
    report["passed"] = True
    save()
except Exception as error:
    report["error"] = repr(error)
    save()
    raise
