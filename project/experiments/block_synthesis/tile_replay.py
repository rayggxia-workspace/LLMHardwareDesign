"""Literal finite-S numerical replay of the qualified tile/scatter recipe.

SRAM words are actual 128-bit records. Only one r-by-n S64 accumulator is
live. External tensors/packed temporaries are explicitly simulator external
memory, never extra private SRAM. This interpreter has no cycle/energy model.
"""
from collections import Counter
import numpy as np


def signed16(word,lane=0):
    value=(int(word)>>(16*lane))&65535
    return value-65536 if value&32768 else value


def final32(raw,shift):
    # Independent scalar RNE, then native S32 saturation. Python integers avoid
    # relying on simulator int64 wraparound at negative/tie boundaries.
    value=int(raw)
    if shift:
        sign=-1 if value<0 else 1
        base,rem=divmod(abs(value),1<<shift)
        value=sign*(base+int(rem>(1<<(shift-1)) or (rem==(1<<(shift-1)) and base&1)))
    return min((1<<31)-1,max(-(1<<31),value))


class SRAM:
    def __init__(self,words):
        self.data=[None]*words;self.high=0

    def write_ack(self,address,word):
        if not 0<=address<len(self.data):raise ValueError('tile SRAM address overflow')
        if not 0<=int(word)<1<<128:raise ValueError('tile word outside 128-bit ABI')
        self.data[address]=int(word);self.high=max(self.high,address+1)

    def read(self,address):
        if not 0<=address<len(self.data) or self.data[address] is None:
            raise ValueError('tile reads unwritten SRAM word')
        return self.data[address]


class TileReplay:
    def __init__(self,ir):
        self.hardware=ir['hardware'];self.constants=ir.get('tile_constants',{});self.events=[]

    def dot(self,node,records,b,binding):
        spec=binding['dot_tile'];rows,columns,k=spec['rows'],spec['columns'],spec['K']
        rt,ct=spec['tile'];pm=self.hardware['leaf_inventory'][binding['macro_binding']['M']]
        ps=SRAM(self.hardware['sites'][pm['site']]['words'])
        em=self.hardware['leaf_inventory'][binding['macro_binding']['E']] if ct>1 else None
        es=SRAM(self.hardware['sites'][em['site']]['words']) if em else None
        if records.shape!=(rows,k,3):raise ValueError('tile prepared external region differs')
        weights=np.asarray(b,dtype=np.int64).reshape(-1,k,columns)
        if weights.shape[0]!=1 or weights.min()<-32768 or weights.max()>32767:
            raise ValueError('tile requires one row-shared S16 B')
        weights=weights[0];counts=Counter();max_tmp=0
        def load(s,address,word):
            s.write_ack(address,word);counts['external_read_words']+=1
        def store(s,address):
            word=s.read(address);counts['external_write_words']+=1;return word
        def basis(lane):
            lanes=self.constants['records'][lane+1]
            return sum((int(x)&65535)<<(16*i) for i,x in enumerate(lanes))
        # Actual sixteen scalar zero LOADs. Result storage is not initialized.
        zero=sum(int(x)<<(16*i) for i,x in enumerate(self.constants['records'][0]))
        for address in list(range(8))+list(range(16,24)):load(ps,address,zero)
        counts['initial_zero_loads']=16
        raw=np.empty((rows,columns),dtype=np.int64)
        canonical=np.empty_like(raw)
        for rr in range(0,rows,rt):
            r=min(rt,rows-rr)
            for cc in range(0,columns,ct):
                n=min(ct,columns-cc);acc=np.zeros((r,n),dtype=np.int64)
                counts['grid_tiles']+=1
                for kk in range(k):
                    for j in range(n):load(ps,16+j,int(weights[kk,cc+j])&65535)
                    counts['dot_B_loads']+=n
                    bv=None
                    for component in range(3):
                        for i in range(r):load(ps,i,int(records[rr+i,kk,component])&65535)
                        counts['dot_A_loads']+=r
                        av=np.array([signed16(ps.read(i)) for i in range(r)],dtype=np.int64)
                        if component==0:
                            bv=np.array([signed16(ps.read(16+j)) for j in range(n)],dtype=np.int64)
                        # Registered feeder cold/reuse-B and native Scale /
                        # Execute semantics, retaining just this tile's S64.
                        acc+=np.outer(av,bv)*(1 if component==0 else 65536)
                        counts.update(dot_scales=1,dot_feeds=1,dot_executes=1)
                raw[rr:rr+r,cc:cc+n]=acc
                if n==1:
                    for i in range(r):
                        result=final32(acc[i,0],spec['final_shift']);address=512+i*8
                        ps.write_ack(address,result&0xffffffff)
                        word=store(ps,address);canonical[rr+i,cc]=self.signed32(word)
                    counts.update(final_reads=r,canonical_outputs=r)
                    continue
                # Save every packed final before the first scatter clears M.
                packed=[];flags=[];stride=(n+3)//4
                for i in range(r):
                    for first in range(0,n,4):
                        word=sum((final32(acc[i,j],spec['final_shift'])&0xffffffff)<<(32*(j-first))
                                 for j in range(first,min(n,first+4)))
                        address=96+len(packed);ps.write_ack(address,word)
                        packed.append(store(ps,address));counts['final_reads']+=1
                for word in packed:
                    load(es,0,word)
                    # Real compact E ASR(15) separately on each S16 lane.
                    flag=sum(((signed16(es.read(0),j)>>15)&65535)<<(16*j) for j in range(8))
                    es.write_ack(1,flag);flags.append(store(es,1));counts['e_sign_services']+=1
                max_tmp=max(max_tmp,len(packed)+len(flags))
                counts.update(packed_outputs=len(packed),flag_outputs=len(flags))
                for i in range(r):
                    for j in range(n):
                        index=i*stride+j//4;lane=2*(j%4);scatter=0
                        for word,selected,scale,shift in (
                            (packed[index],lane,1,0),(packed[index],lane+1,1,16),
                            (flags[index],lane,-1,16)):
                            load(ps,0,word);load(ps,16,basis(selected))
                            # The one-hot B vector is one full 128-bit record
                            # in a native N1/K8 feed, not a CPU bit extraction.
                            partial=sum(signed16(ps.read(0),v)*signed16(ps.read(16),v) for v in range(8))
                            scatter+=partial*scale*(1<<shift)
                            counts.update(scatter_input_loads=1,scatter_basis_loads=1,
                                scatter_executes=1,scatter_feeds=1,scatter_scales=1)
                        result=final32(scatter,0);address=512+i*8+j
                        ps.write_ack(address,result&0xffffffff);word=store(ps,address)
                        canonical[rr+i,cc+j]=self.signed32(word)
                        counts.update(final_reads=1,canonical_outputs=1)
        expected=binding['tile_work']
        for key,value in counts.items():
            if expected.get(key)!=value:raise ValueError('tile replay command/transfer count differs '+key)
        if ps.high>expected['P_words'] or (es and es.high>expected['E_words']) or max_tmp>expected['temporary_external_words']:
            raise ValueError('tile replay allocation exceeds plan')
        self.events.append({'primitive':node['id'],'tile':[rt,ct],'counts':dict(counts),
            'peak_P_extent':ps.high,'peak_E_extent':es.high if es else 0,'peak_external_tmp':max_tmp})
        return raw.reshape(node['shape']),canonical.reshape(node['shape'])

    @staticmethod
    def signed32(word):
        value=int(word)&0xffffffff
        return value-(1<<32) if value&(1<<31) else value
