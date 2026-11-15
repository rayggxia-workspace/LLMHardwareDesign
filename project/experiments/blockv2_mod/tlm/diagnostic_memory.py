"""Explicit zero-input/zero-weight diagnostic scene; never model accuracy evidence."""
from bisect import bisect_right
from struct import pack
from native_tlm_dma import CommittedMemory

class DiagnosticMemory:
    def __init__(self,manifest,payloads,storage):
        self.descriptor_base=manifest['descriptor_base'];self.descriptors=payloads['descriptors.bin']
        self.inputs={r['region']['base']:(r['region']['bytes']+63)//64*64
                     for r in storage['runtime_asset_requirements'] if r['kind']=='input_tensor'}
        self.weights={r['base']:r for r in storage['weights'].values()}
        self.bases=sorted([*self.inputs,*self.weights])
        self.record=bytes(1024)+pack('<8H',*([0x3c00]*8))+bytes(48)
        writes=[(r['base'],(r['bytes']+63)//64*64,r.get('tag_base',r['base']//64))
                for r in storage['regions'].values() if r['base'] not in self.inputs]
        self.committed=CommittedMemory(self.readonly,writes)
    def readonly(self,address):
        if self.descriptor_base<=address<self.descriptor_base+len(self.descriptors):
            return self.descriptors[address-self.descriptor_base:address-self.descriptor_base+64]
        i=bisect_right(self.bases,address)-1
        if i<0:raise ValueError('unmapped diagnostic input')
        base=self.bases[i]
        if base in self.inputs:
            if address+64>base+self.inputs[base]:raise ValueError('input read outside bound allocation')
            return bytes(64)
        w=self.weights[base]
        if w['format']!='W8A16_n8_k128_ordinary_1088_v1' or address+64>base+w['bytes']:
            raise ValueError('unsupported/out-of-range diagnostic weight image')
        offset=(address-base)%1088
        return self.record[offset:offset+64]
    def __call__(self,address):return self.committed(address)
    def begin_write(self,*args):return self.committed.begin_write(*args)
