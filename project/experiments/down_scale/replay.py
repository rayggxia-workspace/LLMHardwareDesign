"""Compact encoded-only replay plus actual metadata/partial/output packet roundtrip.

No float capture is required here. This cannot revalidate float calibration.
Reference Fraction units and rounding do not import the producer arithmetic.
"""
import argparse
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import struct
import numpy as np
from common import save

MAGIC=b'DS59PKT1'
HEADER=struct.Struct('<8s8I24s')


def packets(payload,kind,stream):
    result=[]
    for seq,off in enumerate(range(0,len(payload),1984)):
        piece=payload[off:off+1984]
        h=HEADER.pack(MAGIC,1,kind,stream,seq,len(payload),off,len(piece),0,hashlib.sha256(piece).digest()[:24])
        result.append(h+piece+b'\0'*((-len(piece))%64))
    return result


def receive(items,kind,stream,size):
    out=bytearray()
    for seq,packet in enumerate(items):
        if len(packet)<64 or len(packet)>2048 or len(packet)%64:raise ValueError('packet geometry')
        magic,version,pk,st,sn,total,offset,n,reserved,digest=HEADER.unpack(packet[:64])
        if (magic,version,pk,st,sn,total,offset,reserved)!=(MAGIC,1,kind,stream,seq,size,len(out),0):raise ValueError('packet identity/sequence')
        if not 0<n<=1984 or len(packet)!=64+64*((n+63)//64):raise ValueError('packet payload size')
        piece=packet[64:64+n]
        if hashlib.sha256(piece).digest()[:24]!=digest or any(packet[64+n:]):raise ValueError('packet digest/padding')
        out.extend(piece)
    if len(out)!=size:raise ValueError('packet truncation')
    return bytes(out)


def run(directory):
    directory=Path(directory);index=json.loads((directory/'arrays.json').read_text())
    def array(name):
        record=index[name];p=directory/'objects'/record['file'];raw=p.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=record['sha256']:raise ValueError('array SHA '+name)
        return np.load(io.BytesIO(raw),allow_pickle=False)
    reports=json.loads((directory/'numeric/numeric.json').read_text());profiles={p['name']:p for p in json.loads((directory/'numeric/profiles.json').read_text())}
    ey=array('Y_e');outputs=partials=packet_count=wire_bytes=0;proof=[]
    for record in reports:
        key=record['key'];pr=profiles[record['profile']];ag,wg=pr['ag'],pr['wg'];group=min(ag,wg)
        qa=array(key+'.A_i8');ea=array(key+'.A_e');qw=array(pr['name']+'.W_i8');ew=array(pr['name']+'.W_e')
        expected=array(key+'.out');saved_acc=array(key+'.acc');saved_e0=array(key+'.e0');saved_parts=array(key+'.parts')
        # Decode uses immediate row1, prefill row4; both paths have identical grouping/scales.
        tile=1 if record['phase']=='decode' else 4
        for row in range(0,len(qa),tile):
            rows=min(tile,len(qa)-row);shape=(rows,16);terms=[[] for _ in range(rows*16)]
            metadata=ea[row:row+rows].astype('i1').tobytes()+ew.astype('i1').tobytes()+ey.astype('i1').tobytes()
            stream=packet_count+1;meta_packets=packets(metadata,3,stream)
            got=receive(meta_packets,3,stream,len(metadata));packet_count+=len(meta_packets);wire_bytes+=sum(map(len,meta_packets))
            ae_count=rows*(8192//ag);we_count=16*(8192//wg)
            ae=np.frombuffer(got[:ae_count],dtype='i1').reshape(rows,-1)
            we=np.frombuffer(got[ae_count:ae_count+we_count],dtype='i1').reshape(16,-1)
            ye=np.frombuffer(got[ae_count+we_count:],dtype='i1')
            allparts=[]
            for g,start in enumerate(range(0,8192,group)):
                part=qa[row:row+rows,start:start+group].astype(np.int64)@qw[:,start:start+group].astype(np.int64).T
                if not np.array_equal(part,saved_parts[g,row:row+rows]):raise AssertionError('partial dot')
                allparts.append(part.astype('<i4'));partials+=part.size
            received=[]
            for begin in range(0,len(allparts),4):
                chunk=np.stack(allparts[begin:begin+4]);raw=chunk.tobytes();stream=packet_count+1
                pp=packets(raw,1,stream);raw2=receive(pp,1,stream,len(raw))
                received.extend(np.frombuffer(raw2,dtype='<i4').reshape(chunk.shape));packet_count+=len(pp);wire_bytes+=sum(map(len,pp))
            shared=np.empty(shape,dtype=np.int8)
            for idx in np.ndindex(shape):
                units=[int(ae[idx[0],(g*group)//ag])+int(we[idx[1],(g*group)//wg]) for g in range(len(received))]
                value=sum((Fraction(int(part[idx]))*Fraction(2)**unit for part,unit in zip(received,units)),Fraction(0))
                minimum=min(units);acc=value/(Fraction(2)**minimum)
                if acc.denominator!=1 or acc.numerator!=int(saved_acc[row+idx[0],idx[1]]) or minimum!=saved_e0[row+idx[0],idx[1]]:raise AssertionError('wide accumulation')
                shared[idx]=max(-128,min(127,round(value/(Fraction(2)**int(ye[idx[1]])))))
                outputs+=1
            stream=packet_count+1;near_packets=packets(expected[row:row+rows].tobytes(),2,stream)
            near=np.frombuffer(receive(near_packets,2,stream,rows*16),dtype='i1').reshape(shape)
            if not np.array_equal(near,shared):raise AssertionError('near/shared RQ changed outputs')
            packet_count+=len(near_packets);wire_bytes+=sum(map(len,near_packets))
        proof.append(key)
    return {'status':'PASS','cases':len(proof),'Fraction_output_values':outputs,'INT64_partial_values':partials,
            'packets_decoded':packet_count,'packet_wire_bytes':wire_bytes,
            'scope':'encoded integer/metadata roundtrip, no raw float calibration or hardware claim'}


def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    if a.output.exists():raise ValueError('refuse overwrite')
    result=run(a.directory);save(a.output,result);print(json.dumps(result))


if __name__=='__main__':main()
