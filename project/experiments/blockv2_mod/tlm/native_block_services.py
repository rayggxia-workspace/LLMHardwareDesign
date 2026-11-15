"""Descriptor adapters for blockv2-mod services absent in the PR260 registry."""
import struct
from native_tlm_timing import Transfer

def counted(dma,sram,*,store):
    def bind(record):
        count=struct.unpack_from('<H',record,18)[0]
        if not 0<count<=(128 if store else 64):
            raise ValueError('counted DMA request count')
        # PR260's DMA engine accepts a byte count at binding time. Preserve all
        # address/tag fields; consume the counted ABI field before that check.
        raw=bytearray(record);raw[18:20]=b'\0\0'
        return dma.provider(sram,size=count*(64 if store else 128),store=store)(raw)
    return bind

def gather(dma,sram):
    def bind(record):
        table,rows,offset,destination,index_address,flags=struct.unpack_from('<QIHHQI',record,16)
        if (table%128 or not 0<rows<2**31 or destination not in (0,512)
            or offset%4 or offset>16380 or flags not in (0,1)
            or (flags and index_address%4) or any(record[44:124])):
            raise ValueError('invalid GTH1 descriptor')
        def execute(done):
            def indexed(data,lane):
                index=struct.unpack_from('<i',data,lane)[0]
                if index<0:index+=rows
                if not 0<=index<rows:raise ValueError('Gather index outside table')
                raw=bytearray(128)
                struct.pack_into('<H6xQ',raw,16,destination,table+8192*index)
                dma.provider(sram,size=8192)(raw)(done)
            if flags:
                beat=index_address//64*64
                dma.dram.submit(Transfer(beat),lambda:indexed(dma.memory(beat),index_address%64))
            else:
                sram.access(offset//16,lambda data:indexed(data,offset%16))
        return execute
    return bind

def gated(arithmetic,packet):
    def bind(record):
        gate,up,out,words=struct.unpack_from('<4H',record,16)
        spans=sorted((gate,up,out))
        if (not 0<words<=32 or spans[-1]+words>1024
            or any(a+words>b for a,b in zip(spans,spans[1:])) or any(record[24:124])):
            raise ValueError('invalid GSM1 descriptor')
        def begin(done):
            def step(i):
                if i==words:done();return
                def rhs(a,b):
                    values=[]
                    for lane in (0,2):
                        pair,error=packet(a[lane:lane+2],b[lane:lane+2],True,3)
                        if error:raise ValueError('GSM1 arithmetic overflow')
                        values.extend(pair)
                    arithmetic.leaf('g_s32_packets',10,lambda:arithmetic.write(
                        out+i,values,lambda:step(i+1)))
                arithmetic.read(gate+i,lambda a:arithmetic.read(up+i,lambda b:rhs(a,b)))
            step(0)
        return arithmetic.service(begin)
    return bind
