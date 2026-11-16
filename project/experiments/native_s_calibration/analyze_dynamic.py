"""Audit the explicit failed full-scope15-pass timing diagnostic."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile

TRACE='6ed2129e2f13842dc53b4ba2135ea41886d1c126d842661dc7d5ac38ffb26f1d'


def analyze(directory):
    receipt=json.loads((directory/'recovery.json').read_text())
    raw=base64.b64decode(b''.join((directory/'receipts.tar.gz.b64').read_bytes().split()),validate=True)
    assert hashlib.sha256(raw).hexdigest()==receipt['receipts_archive_sha256']
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        files={m.name:archive.extractfile(m).read() for m in archive if m.isfile()}
    assert {k:hashlib.sha256(v).hexdigest() for k,v in files.items()}==receipt['members']
    source=(directory/'source.tar.gz').read_bytes()
    assert hashlib.sha256(source).hexdigest()==receipt['source_archive_sha256']
    with tarfile.open(fileobj=io.BytesIO(source),mode='r:gz') as archive:
        sources={m.name:archive.extractfile(m).read() for m in archive if m.isfile()}
    for line in sources['source.sha256'].decode().splitlines():
        digest,path=line.split('  ',1);assert hashlib.sha256(sources[path]).hexdigest()==digest
    rows=[]
    for name,data in sorted(files.items()):
        if not name.endswith('/report.json'):continue
        report=json.loads(data);assert report['passed'] and report['input_trace_SHA256']==TRACE
        assert len(report['affinity'])==12
        result=report['results'][-1]['result'];ns=result['native_service'];env=report['source_env']
        assert report['results'][-1]['label']=='decode512' and result['tokens']==1
        assert result['logical_write_bytes']==8191232 and result['KV_state_write_bytes']==73728
        assert result['max_outstanding_beats']<=32 and result['max_outstanding_descriptors']<=32
        assert ns['shared_S_owner_peak']<=2 and result['closure']['S_peak']<=16384
        assert ns['max_W_banks']<=4 and ns['max_A_tiles']<=2 and ns['max_command_result_slots']<=2
        assert not ns['whole_system_calibrated'] and not ns['numerically_replayed'] and not ns['physical_system_qualified']
        if env['NS_DYNAMIC']=='1':
            assert ns['dynamic_partials']==1105920 and ns['dynamic_S_read_B']==5096079360
            assert ns['dynamic_staged_write_B']==339738624 and ns['dynamic_local_return_B']==1203240960
            assert ns['dynamic_service_cycles_sum']==1105920*(int(env['NS_DYNAMIC_RECORD_CYCLES'])+6)
            assert result['M_commands']==4119296
            assert result['read_bus_bytes']==3799178240 and result['logical_read_bytes']==3648183296
        else:
            assert ns['dynamic_partials']==0 and result['M_commands']==3028352
            assert abs(result['tokens_per_second']-8.13617916866)<1e-9
        assert sum(c['flows']['weight']['bus_read'] for c in result['detail']['channels'])==3298000896
        rows.append(dict(plan=report['plan'],cycles=result['ticks'],tokens_per_second=result['tokens_per_second'],
                         dynamic_P_count=int(env['NS_DYNAMIC_PCOUNT']),dynamic_record_cycles=int(env['NS_DYNAMIC_RECORD_CYCLES']),
                         dynamic_partials=ns['dynamic_partials'],dynamic_service_sum_cycles=ns['dynamic_service_cycles_sum'],
                         dynamic_local_S_read_B=ns['dynamic_S_read_B'],dynamic_staging_S_write_B=ns['dynamic_staged_write_B'],
                         local_source_return_B=ns['dynamic_local_return_B'],DDR_read_bus_B=result['read_bus_bytes'],
                         DDR_logical_read_B=result['logical_read_bytes'],DDR_write_bus_B=result['write_bus_bytes'],
                         spans=result['spans_ticks'],qualification='Full scope SystemC timing diagnostic. Real15pass M/S fees; E/N/deployed program/source loader/whole physical and energy remain unqualified.'))
    assert len(rows)==8
    repeat=next(r for r in rows if r['plan']=='measured15-ideal-3P-repeat')
    first=next(r for r in rows if r['plan']=='measured15-ideal-3P')
    assert repeat['cycles']==first['cycles']
    return dict(passed=True,job=receipt['job'],source_commit=receipt['source_commit'],
                archive_sha256=receipt['receipts_archive_sha256'],trace_sha256=TRACE,rows=rows,
                meets_9_215647_target=False,whole_system_calibrated=False,energy_qualified=False,
                private_S_B=16384,dynamic_source_window_B=4608,dynamic_final_result_B=32,added_SRAM_B=0,
                pressure_scope='1483 is the largest observed seed25001 record in fixture102338, not arbitrary-stall worst-case bound')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);args=p.parse_args()
    result=analyze(args.run);(args.run/'dynamic-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,job=result['job'],rows=[(r['plan'],r['tokens_per_second']) for r in result['rows']])))
