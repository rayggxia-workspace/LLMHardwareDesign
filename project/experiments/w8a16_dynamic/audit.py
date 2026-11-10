"""Read recovered artifacts only; no numerical generation or simulation."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
from recover import receipts


def product_audit(log,vector,final_ack):
    """Compare recorded values/identities and traffic; no numerical rerun."""
    assert '%Error' not in log
    lines=iter(vector.splitlines());expected=[];cases=0
    for header in lines:
        full,n,shift,major=map(int,header.split());cases+=1
        for _ in range(full+full*n+1):next(lines)
        expected.extend(int(next(lines),16) for _ in range(((full+127)//128)*15))
    observed=[(int(cycle),int(record),int(value,16)) for cycle,record,value in
              re.findall(r'JOINT_RAW cycle=(\d+) record=(\d+) value=([0-9a-f]+)',log)]
    assert cases==4 and len(expected)==len(observed)==120
    assert [row[2] for row in observed]==expected
    req=re.findall(r'JOINT_S_REQ cycle=(\d+) owner=(\d+) address=(\d+)',log)
    ack=re.findall(r'JOINT_S_ACK cycle=(\d+)',log)
    assert len(req)==len(ack)==21225
    assert all(int(address)<1024 for _,_,address in req)
    assert all(int(b)>=int(a)+2 for (a,_,_),b in zip(req,ack))
    mc_req=re.findall(r'JOINT_LOCAL_MC_REQ cycle=(\d+) channel=(\d+) tag=(\d+)',log)
    mc_rsp=re.findall(r'JOINT_LOCAL_MC_RETURN cycle=(\d+) tag=(\d+)',log)
    assert len(mc_req)==len(mc_rsp)==120*17
    assert [int(row[2]) for row in mc_req]==[int(row[1]) for row in mc_rsp]
    a=re.findall(r'JOINT_A cycle=(\d+) record=(\d+) beat=(\d+)',log)
    assert len(a)==120*8 and [int(row[2]) for row in a]==list(range(8))*120
    assert [int(row[1]) for row in a[::8]]==[row[1] for row in observed]
    commands=re.findall(r'JOINT_LC cycle=(\d+) data=([0-9a-f]+)',log)
    assert len(commands)==1560
    index=0;frames=[]
    while index<len(commands):
        cycle,value=commands[index];value=int(value,16)
        assert value&65535==0x4d02
        opcode=(value>>16)&15;length=(value>>20)&15
        frames.append(dict(cycle=int(cycle),opcode=opcode,length=length))
        index+=length
    assert [row['opcode'] for row in frames]==[1,4,2,3]*120
    assert [row['length'] for row in frames]==[8,1,2,2]*120
    responses=[(int(c),int(v,16)) for c,v in re.findall(r'JOINT_LR_FRAME cycle=(\d+) value=([0-9a-f]+)',log)]
    assert len(responses)==120*6
    assert all(v&0xffffffff==0x02504d02 and (v>>40)&255==0 for _,v in responses)
    writes=re.findall(r'JOINT_WRITE_ACK cycle=(\d+) final=(\d+) address=(\d+)',log)
    staging=[row for row in writes if int(row[1])==0]
    if final_ack:
        assert len(staging)==2304 and [int(row[2]) for row in staging]==list(range(288))*8
    else:
        assert not writes  # legacy fixture counted staging but did not trace it
    finals=[row for row in writes if int(row[1])==1]
    assert len(finals)==(8 if final_ack else 0)
    if final_ack:assert [int(row[2]) for row in finals]==[300,301]*4
    summary=re.search(r'PASS dynamic_product cases=4 partials=120 LOCAL64returns=2040 S128reads=21225 ACKs=21225 Abeats=960 LC128flits=1560 LR128flits=1680 stagedS128writes=2304 (?:finalS128writeACKs=8 validationReadbacks=8 )?DDRbytes=0 cycles=(\d+)',log)
    assert summary
    # Per-record boundary is first BEGIN header through raw capture. This
    # includes true LOCAL_S_PACK64 filling, A packing and serial API frames,
    # but not prior staging writes, next merge/final store, or deployed PM.
    record_costs=[dict(record=row[1],begin_cycle=frames[i*4]['cycle'],raw_cycle=row[0],
                       begin_to_raw=row[0]-frames[i*4]['cycle']) for i,row in enumerate(observed)]
    return dict(cases=cases,partials=len(observed),local64_returns=len(mc_rsp),
                local_source_bus_bytes=len(mc_rsp)*64,ddr_bytes=0,
                source_S128_reads=len(req),source_S128_read_bytes=len(req)*16,
                staged_S128_writes=2304,staged_write_bytes=2304*16,staging_ACKs_individually_traced=final_ack,
                final_S128_write_ACKs=len(finals),total_fixture_cycles=int(summary.group(1)),
                record_costs=record_costs)


def audit(run):
    recovery,files=receipts(run)
    assert 'FAILED' not in recovery['sacct'] and 'COMPLETED' in recovery['sacct']
    raw=(run/'source.tar.gz').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==recovery['source_archive_sha256']
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        sources={m.name:archive.extractfile(m).read() for m in archive if m.isfile()}
    assert sources['source-commit.txt'].decode().strip()==recovery['source_commit']
    time_divisor=1000 if b'PACK_CMD cycle=%0t' in sources['source/project/experiments/w8a16_dynamic/tb_packer.sv'] else 1
    for line in sources['source.sha256'].decode().splitlines():
        sha,path=line.split('  ',1);assert hashlib.sha256(sources[path]).hexdigest()==sha
    checkpoint=json.loads(files['checkpoint/checkpoint-report.json'])
    assert checkpoint['passed'] and checkpoint['vectors']==12
    assert checkpoint['shapes']==[['AV',2,8],['QK',128,2]]
    assert hashlib.sha256(files['checkpoint/checkpoint-vectors.json']).hexdigest()==checkpoint['vector_sha256']
    if 'm-provider-source.json' in sources:
        override=json.loads(sources['m-provider-source.json'])
        assert override['commit']==recovery['m_provider_commit']
        assert all(hashlib.sha256(sources['source/'+p]).hexdigest()==v for p,v in override['files'].items())
    results=[];timings=[];products=[]
    for seed in range(25001,25007):
        math=json.loads(files[f'seed-{seed}/oracle.json']);assert math['passed'] and math['cases']==187
        prefix=f'rtl-{seed}/';result=json.loads(files[prefix+'result.json'])
        assert result['passed'] and result['merge_commands']==536 and result['raw_groups']==345 and result['packer_commands']==55
        assert result['checkpoint_roles']==['AV','QK']
        for path,sha in result['vectors_sha256'].items():
            assert hashlib.sha256(files[prefix+path]).hexdigest()==sha
        for unit,count in [('merge','commands=536'),('raw','groups=345'),('packer','commands=55')]:
            assert b'%Warning' not in files[prefix+unit+'-build.log']
            for initial in range(3):
                log=files[prefix+unit+f'-{initial}.log'].decode()
                assert 'PASS ' in log and count in log and '%Error' not in log
        real=prefix+'real-packer-build.log' in files
        if real:
            assert b'%Warning' not in files[prefix+'real-packer-build.log']
            expected=[int(line.split()[-1],16) for line in files[prefix+'real-packer.txt'].decode().splitlines()]
            for initial in range(3):
                for ideal in (0,1):
                    log=files[prefix+f'real-packer-{initial}-{ideal}.log'].decode()
                    assert 'PASS packer commands=54' in log and '%Error' not in log
                    done=re.findall(r'PACK_DONE cycle=(\d+) tag=(\d+) reads=(\d+) error=(\d+)',log)
                    assert len(done)==54 and [int(row[2]) for row in done]==expected
                    req=re.findall(r'PACK_REQ cycle=(\d+) tag=(\d+) addr=(\d+)',log)
                    rsp=re.findall(r'PACK_RSP cycle=(\d+) tag=(\d+)',log)
                    assert len(req)==len(rsp)==sum(expected)
                    assert all(int(row[2])<1024 for row in req)
                    assert all(int(b[0])>=int(a[0])+2*time_divisor for a,b in zip(req,rsp))
                    if seed==25001 and initial==0 and ideal==1:
                        commands={int(tag):int(cycle) for cycle,tag in re.findall(r'PACK_CMD cycle=(\d+) tag=(\d+)',log)}
                        timings=[dict(tag=int(tag),command_cycle=commands[int(tag)]//time_divisor,done_cycle=int(cycle)//time_divisor,
                                      cycles=(int(cycle)-commands[int(tag)])//time_divisor,reads=int(reads),error=int(error))
                                 for cycle,tag,reads,error in done]
        if prefix+'weight-source-build.log' in files:
            assert result['local_source_records']==30
            assert b'%Warning' not in files[prefix+'weight-source-build.log']
            for initial in range(3):
                log=files[prefix+f'weight-source-{initial}.log'].decode()
                assert 'PASS local_source records=30' in log and 'DDRbytes=0' in log and '%Error' not in log
                # If the newer held-offer/quarantine tests are in the source,
                # they must have reached their final successful assertions.
                if b'held_cancel=1' in sources['source/project/experiments/w8a16_dynamic/tb_weight_source.sv']:
                    assert 'held_cancel=1 quarantine=1' in log
                mc_returns=re.findall(r'LOCAL_MC_RETURN cycle=(\d+) tag=(\d+)',log)
                if mc_returns:
                    assert len(mc_returns)==512  # 30*17 + two canceled true returns
                    assert [int(v[1]) for v in mc_returns[:510]]==[0x8000+r*32+b for r in range(30) for b in range(17)]
        if prefix+'product-build.log' in files:
            assert result['product']['cases']==4 and result['product']['partials']==120
            assert b'%Warning' not in files[prefix+'product-build.log']
            for initial in range(3):
                report=product_audit(files[prefix+f'product-{initial}.log'].decode(),
                                     files[prefix+'product.txt'].decode(),
                                     b'finalS128writeACKs=' in sources['source/project/experiments/w8a16_dynamic/tb_product.sv'])
                products.append(dict(seed=seed,initial=initial,**report))
                if prefix+f'product-{initial}-ideal.log' in files:
                    ideal=product_audit(files[prefix+f'product-{initial}-ideal.log'].decode(),
                                        files[prefix+'product.txt'].decode(),True)
                    products.append(dict(seed=seed,initial=initial,ideal=True,**ideal))
        results.append(dict(seed=seed,merge_runs=3,raw_runs=3,host_packer_runs=3,
                            real_S_packer_runs=6 if real else 0,math_cases=187))
    return dict(passed=True,job=int(recovery['job']),source_commit=recovery['source_commit'],
                archive_sha256=recovery['archive_sha256'],results=results,
                m_provider_commit=recovery.get('m_provider_commit',recovery['source_commit']),
                real_S_ideal_first_seed_timings=timings,
                real_product_runs=products,
                qualification='component arithmetic/real-S packing and, when present, actual M-product fixture. Not deployed LC/MC program, 300MHz physical or wholemodel quality.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);args=parser.parse_args()
    result=audit(args.run);(args.run/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=result['passed'],job=result['job'],seeds=len(result['results']))))
