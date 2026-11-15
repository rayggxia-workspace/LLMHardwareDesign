"""Emit explicit boot/page handshakes for existing native MC and LC RTL.

This is a boot-port transaction recipe, not additional execution-ISA opcodes.
It requires a deployment agent implementing ready/valid and response checks.
"""
import struct,zlib
from collections import Counter
from hashlib import sha256

def recipe(local,pages,targets,call_rows,topology):
    image_id=struct.unpack_from('<I',local,60)[0]
    operations=[]
    def emit(op,**fields):operations.append({'op':op,**fields})
    for target in targets:
        emit('lc_cfg',target=target,code=0,generation=1,abi=0x02500002,
             capacity=0x02510001,bytes=len(local),require_status=0)
        for address in range(0,len(local),16):
            emit('lc_cfg',target=target,code=1,generation=1,address=address,
                 data_hex=local[address:address+16].hex(),require_status=0)
        emit('lc_cfg',target=target,code=2,generation=1,crc32=zlib.crc32(local),
             require_status=0,require_certified=True)
    emit('mc_release',epoch=1,sequence=1)
    sequence=Counter()
    page_contract=[]
    for index,page in enumerate(pages):
        generation=index+1;raw=page['data'];name=page['file']
        emit('await_quiescent',require_mc_result_consumed=index>0,require_lc_idle=targets,
             require_transport_drained=True)
        emit('mc_deploy',valid=False)
        emit('mc_cfg',code=0,generation=generation,total_bytes=len(raw),
             image_id=struct.unpack_from('<I',raw,60)[0],topology_id=topology,
             abi_id=0x02500002,capacity_id=0x02590003,require_status=0)
        for code in (1,2):
            for address in range(0,len(raw),16):
                emit('mc_cfg',code=code,generation=generation,address=address,
                     **({'data_hex':raw[address:address+16].hex()} if code==1 else
                        {'require_data_hex':raw[address:address+16].hex()}),
                     require_status=0)
        emit('mc_cfg',code=3,generation=generation,proof_after_all_readbacks_match=True,require_status=0)
        emit('mc_cfg',code=4,generation=generation,require_status=0,require_prepared=True)
        for target in targets:
            emit('lc_session',target=target,generation=generation,topology=topology,
                 require_idle=True,require_transport_drained=True)
        emit('mc_deploy',valid=True,generation=generation,
             local_enabled=sum(1<<t for t in targets),
             local_image_ids={str(t):image_id for t in targets})
        emit('mc_start',generation=generation,job=1,epoch=1,sequence=generation,args=0)
        extent=call_rows[page['first_call']:page['first_call']+page['call_count']]
        before=dict(sequence)
        for c in extent:sequence[c['target']]+=1
        if any(n>=2**32 for n in sequence.values()):raise ValueError('MC call sequence overflow')
        emit('mc_result',require_status=0,require_job=1,require_epoch=1,require_sequence=generation)
        page_contract.append({'file':name,'generation':generation,
                              'call_sequence_before':before,'call_sequence_after':dict(sequence),
                              'sha256':sha256(raw).hexdigest()})
    return {'schema':'native-mc-lc-deployment-operations/1','topology':topology,
            'local_program_installations':len(targets),'local_program_image_id':image_id,
            'operations':operations,'pages':page_contract,
            'scope':'generated ready/valid boot-port recipe; RTL replay acceptance remains separate'}
