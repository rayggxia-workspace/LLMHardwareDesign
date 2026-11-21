"""Export trace-backed exact K128/K512 S32 service fees for SystemC."""
import argparse
import hashlib
import json
from pathlib import Path
from audit_s128 import audit


def export(directory):
    report=audit(directory);assert report['real_S'] and report['job'] in ('102419','102444')
    profiles=[]
    for measured in report['timing']:
        rows=measured['rows_capacity'];mode=measured['mode']
        for layout in ('N-major','K-major'):
            frames=[]
            for full_k,offset in ((128,0),)+tuple((512,k) for k in range(0,512,128)):
                selection=[f for f in measured['frames'] if (f['rows'],f['n'],f['layout'],f['full_k'],f['k_offset'],f['chunk_k'])==
                           (rows,8,layout,full_k,offset,128)]
                assert selection
                expected_final=offset+128==full_k
                for frame in selection:
                    assert frame['reads']==32*(rows+8) and frame['writes']==(2*rows if expected_final else 0)
                    assert frame['final']==expected_final and frame['max_s_owner']==2
                fees=sorted({f['cmd_to_terminal_cycles'] for f in selection})
                if mode==0:assert len(fees)==1 and measured['begin_cycles']==[6]
                frames.append(dict(full_k=full_k,k_offset=offset,cycles=max(fees),observed_cycles=fees,
                                   read_words=32*(rows+8),result_write_words=2*rows if expected_final else 0))
            profiles.append(dict(rows=rows,lanes=rows*4,layout=layout,pressure=bool(mode),
                                 begin_cycles=max(measured['begin_cycles']),frames=frames))
    assert len(profiles)==12
    return dict(schema='native-s32-dot-fees/1',source_job=report['job'],source_commit=report['source_commit'],
        source_archive_sha256=report['source_archive_sha256'],receipts_archive_sha256=report['receipts_archive_sha256'],
        offline_audit_sha256=hashlib.sha256((directory/'audit.json').read_bytes()).hexdigest(),profiles=profiles,
        measurement='First-seed actual four-bank SRAM, 10ns functional clock. Timing fees count cycles, not 300MHz qualification.',
        pressure='Observed per-shape envelope from seed25201/init0, not arbitrary-backpressure bound.',
        excluded='DDR staging/readback, production LC framing, overlap with other S clients, clock/energy qualification.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();args.out.write_text(json.dumps(export(args.run),indent=2)+'\n')
