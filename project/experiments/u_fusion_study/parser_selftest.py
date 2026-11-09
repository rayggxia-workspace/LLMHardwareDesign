"""Synthetic receipt parser checks only; does not claim RTL simulation results."""
from run_native import check_log


def main():
    lines=[]
    for direct in (0,1):
        for tiles in (1,16):
            for delay in (0,4):
                lines.append(f'NATIVE_FUSION_MEASURE direct={direct} tiles={tiles} delay={delay} '
                    f'cycles={100*tiles+delay*tiles} S_reads={(3 if direct else 4)*tiles} '
                    f'S_writes={(1 if direct else 2)*tiles} N_commands={tiles} E_commands={tiles} '
                    f'direct_beats={tiles if direct else 0} result=1049')
    lines += ['NATIVE_FUSION_CANCEL_PASS N_error_status=9 disabled_status=5 output_unchanged=1',
              'NATIVE_FUSION_RESET_PASS held_producer_cancelled=1 no_stale_output=1',
              'NATIVE_FUSION_PASS routes=2 tile_counts=1,16 handoff_delays=0,4 no_engine_replication=1']
    text='\n'.join(lines)+'\n'
    report=check_log(text)
    if len(report['cases'])!=8 or len(report['comparisons'])!=4:raise ValueError('parser positive fixture')
    bad={
        'missing_case':text.replace(lines[0]+'\n',''),
        'duplicate_case':text+lines[0]+'\n',
        'wrong_S_reads':text.replace('S_reads=4 ','S_reads=5 ',1),
        'wrong_E_instances':text.replace('E_commands=1 ','E_commands=2 ',1),
        'zero_cycles':text.replace('cycles=100 ','cycles=0 ',1),
        'missing_cancel':text.replace(lines[-3],''),
        'missing_reset':text.replace(lines[-2],''),
    }
    for name,broken in bad.items():
        try:check_log(broken)
        except ValueError:continue
        raise ValueError('corrupt synthetic receipt accepted '+name)
    print('PARSER_SELFTEST_PASS synthetic_positive=1 rejected=7 no_RTL_execution=1')


if __name__=='__main__':main()
