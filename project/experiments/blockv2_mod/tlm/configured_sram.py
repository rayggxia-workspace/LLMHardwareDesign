"""Externally configured SRAM capacity/ports with finite ACK timing.

Each access() is the actual service's one 128-bit request. A wide configured
port does not coalesce separate requests or bypass service-internal waits.
"""
from collections import Counter,deque
from tlm_sram_profile import Sram,load_sram_profile

class ConfiguredSram:
    def __init__(self,clock,*,core_ps,profile):
        if type(core_ps) is not int or core_ps<=0:raise ValueError('positive SRAM clock required')
        self.clock,self.core_ps,self.profile=clock,core_ps,profile
        self.words={};self.next_port=0;self.responses=deque();self.stats=Counter()

    def access(self,word,done,payload=None):
        beats=self.profile.beats(word,1,write=payload is not None,service_bits=128)
        if beats!=[(word,1)] or payload is not None and len(payload)!=16:
            raise ValueError('invalid native SRAM word access')
        edge=((self.clock.now+self.core_ps-1)//self.core_ps)*self.core_ps
        while self.responses and self.responses[0]<=edge:self.responses.popleft()
        start=max(edge,self.next_port)
        if len(self.responses)==2:start=max(start,self.responses.popleft())
        self.stats['port_wait_ps']+=start-edge
        self.stats['write_transactions' if payload is not None else 'read_transactions']+=1
        self.stats[f'bank{word%4}_accesses']+=1
        self.next_port=start+self.core_ps;self.responses.append(start+2*self.core_ps)
        def complete():
            if payload is not None:self.words[word]=payload
            if word not in self.words:raise ValueError('SRAM read before write commit')
            done(self.words[word])
        self.clock.after(start-self.clock.now+2*self.core_ps,complete)

def profiles(hardware,hardware_sha,config):
    assemblies=set(hardware['leaf_inventory'])
    if config:
        result,digest=load_sram_profile(config,hardware_sha,assemblies)
        if set(result)!=assemblies or any(row.assembly!=name for name,row in result.items()):
            raise ValueError('SRAM config must bind each physical block instance exactly once')
        return result,digest
    result={}
    for name,row in hardware['leaf_inventory'].items():
        # Registered blockv2-mod uses 1024 16-byte words; reject a different
        # hardware manifest instead of quietly synthesizing an old four-S layout.
        site=hardware['sites'][name+'.S']
        capacity=site.get('capacity_words',site.get('words'))
        if capacity is None:
            raise ValueError('hardware SRAM capacity missing: '+name)
        result[name]=Sram(name,capacity*16,128,128)
    return result,None
