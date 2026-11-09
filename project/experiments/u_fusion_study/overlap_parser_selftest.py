"""Synthetic log-parser tests only; these are not RTL execution evidence."""
import copy
from run_overlap import check_log


def fixture(depth):
    lines=[]
    for overlap in (0,1):
        for tiles in (1,16,32):
            for delay in (0,4):
                fifo=tiles if overlap else 0
                lines.append(f'OVERLAP_MEASURE depth={depth} overlap={overlap} tiles={tiles} delay={delay} cycles={tiles*100+delay} '
                             f'S_reads={tiles*3} S_writes={tiles} N_commands={tiles} E_commands={tiles} E_beats={tiles} '
                             f'FIFO_pushes={fifo} FIFO_pops={fifo} max_inflight={min(tiles,2) if overlap else 1} verified_slots={tiles}')
    lines.extend((f'OVERLAP_FULL_PASS depth={depth} held_cycles=8 recovered_tiles={depth+3} max_inflight={depth+1}',
                  f'OVERLAP_RESET_PASS depth={depth} held_producer_cancelled=1 empty_after_reset=1 fresh_tile_verified=1',
                  f'OVERLAP_PASS depth={depth} routes=2 tile_counts=1,16,32 delays=0,4 one_N_one_E=1'))
    return '\n'.join(lines)


def main():
    rejected=0
    for depth in (1,2,4):
        good=fixture(depth);assert check_log(good,depth)['passed']
        bad=(good.replace('S_reads=3 ','S_reads=4 ',1),
             good.replace('FIFO_pops=1 ','FIFO_pops=0 ',1),
             good.replace('verified_slots=32','verified_slots=31',1),
             good.replace('max_inflight=1 ','max_inflight=99 ',1),
             '\n'.join(good.splitlines()[1:]),
             good+'\n'+good.splitlines()[0],
             good.replace('empty_after_reset=1','empty_after_reset=0'),
             good.replace('held_cycles=8','held_cycles=7'),
             good.replace('one_N_one_E=1','one_N_one_E=2'),
             good.replace('cycles=100 ','cycles=0 ',1))
        for text in bad:
            try:check_log(text,depth)
            except ValueError:rejected+=1
            else:raise AssertionError('parser accepted malformed receipt')
    print(f'OVERLAP_PARSER_SELFTEST_PASS synthetic_positive=3 synthetic_negative={rejected} RTL_executed=0')


if __name__=='__main__':main()
