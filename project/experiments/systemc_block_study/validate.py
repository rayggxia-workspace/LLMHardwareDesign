"""Behavioral checks on finite buffers/ACKs; not full model numerics or RTL."""
import json,subprocess
from pathlib import Path
from sweep import SIM

def run(name,trace,profile='queued_pipe_w8',failure=None):
    p=Path('generated/validation-'+name+'.trace');p.write_bytes(trace.encode())
    r=subprocess.run(SIM+[str(p),profile],capture_output=True,text=True)
    Path('generated/validation-'+name+'.log').write_text(r.stdout+r.stderr)
    if failure:
        assert r.returncode and failure in r.stdout+r.stderr,(name,r.stdout,r.stderr)
        return {'case':name,'expected_failure':failure}
    assert not r.returncode,(name,r.stdout,r.stderr)
    d=json.loads(next(x[7:] for x in r.stdout.splitlines() if x.startswith('RESULT ')))
    assert d['P_scratch_peak_bytes']<=16384
    assert d['U_cache_peak_bytes']+4096<=16384
    assert d['max_outstanding_beats']<=32 and d['max_outstanding_descriptors']<=32
    assert d['read_bus_bytes']>=d['logical_read_bytes'] and d['write_bus_bytes']>=d['logical_write_bytes']
    assert abs(sum(d['spans_ticks'].values())-d['ticks'])<=len(d['spans_ticks'])
    return dict(d,case=name)

def main():
    rows=[]
    # Dynamic PV has 256 separate narrow-row reads. It must stall safely
    # at 32 descriptor credits and still deliver the tail output after ACK.
    d=run('queue-pressure','''3 1 1
0 1024 32 1
1 4096 32 1
2 16 32 0
2 Dot 16 2 8 512 1 24 2 2 0 1
''');assert d['max_outstanding_descriptors']==32;rows.append(d)
    d=run('resident-row-transition','''3 1 1
0 1152 32 1
1 2176 16 1
2 153 32 0
2 Dot 153 9 17 128 1 16 0 2 0 1
''');assert d['M_tiles']==6 and d['resident_A_saved_bytes']==4608;rows.append(d)
    # A consumer must not manufacture an absent producer's S/backing data.
    rows.append(run('missing-producer','''2 1 1
0 4 32 0
1 4 32 0
1 Convert 4 1 4 1 1 0 0 1 0
''',failure='read before producer write/ACK'))
    # K/V update commits 2 heads * 128 elements * 4 bytes, for both K/V.
    d=run('kv-ack','''5 1 1
0 256 32 1
1 256 32 1
2 131072 32 1
3 131072 32 1
4 512 32 0
4 KVWrite 512 1 512 512 1 0 0 4 0 1 2 3
''');assert d['KV_state_write_bytes']==2048 and d['logical_write_bytes']==2048;rows.append(d)
    Path('generated/validation.json').write_text(json.dumps({'scope':'SystemC resource/ACK/negative controls','cases':rows},indent=2)+'\n')
    print('VALIDATION_PASS',len(rows))

if __name__=='__main__':main()
