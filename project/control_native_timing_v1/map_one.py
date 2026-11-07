"""Map explicit native controller identities against the locked Nangate45 library."""
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'control_r7_v0_1'))
import synthesize

CORE = PROJECT / 'control_rtl_min_v0_1'
COMMON = dict(STALL_LIMIT=4096, DRAIN_LIMIT=128, LOCAL_S_BYTES=16384)
CASES = {
    f'{kind}{block}': (f'{kind}{block}', CORE / 'lc_min_controller.sv',
        dict(COMMON, BLOCK_ID=block, ENABLE_NATIVE=1, NATIVE_BLOCK_TYPE=number,
             NATIVE_TOPOLOGY=0x01930011 + number), 'clk_i', 1)
    for kind, number in (('u', 0), ('f', 1), ('c', 2), ('p', 3), ('j', 4))
    for block in (0, 1)
}
CASES.update({f'p16_{block}': (f'p16_{block}', CORE / 'lc_min_controller.sv',
    dict(COMMON, BLOCK_ID=block, ENABLE_NATIVE_P16=1), 'clk_i', 1) for block in (0, 1)})
CASES['mother'] = ('mother', CORE / 'mc_min_controller.sv',
    dict(STALL_LIMIT=4096, NATIVE_ABI_ID=0x01930001), 'clk_i', 1)
CASES['link'] = ('link', CORE / 'two_local_link.sv', {}, 'clk_i', 1)

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in CASES:
        raise SystemExit('first argument must be one of: ' + ', '.join(CASES))
    case = sys.argv.pop(1)
    synthesize.CASES = [CASES[case]]
    synthesize.main()
