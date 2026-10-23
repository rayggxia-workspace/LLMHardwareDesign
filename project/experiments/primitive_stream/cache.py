"""Software state/epoch oracle. No claim about cycle/RTL command queues."""
import hashlib
import numpy as np

class ImmutableKV:
    def __init__(self,capacity,dimension,profile_id):
        if capacity<=0 or dimension<=0:raise ValueError("positive capacity/dimension")
        self.k=np.empty((capacity,dimension),dtype=np.int8)
        self.v=np.empty_like(self.k);self.capacity=capacity;self.length=0;self.epoch=0
        self.profile_id=profile_id;self.events=[]

    def append(self,positions,k,v,expected_epoch,profile_id):
        # Validate everything before modifying storage or publishing length/epoch.
        if expected_epoch!=self.epoch:raise ValueError("stale cache epoch")
        if profile_id!=self.profile_id:raise ValueError("scale/profile change requires explicit conversion")
        if k.dtype!=np.int8 or v.dtype!=np.int8 or k.shape!=v.shape or k.ndim!=2 or k.shape[1]!=self.k.shape[1]:
            raise ValueError("strict i8 token-major K/V")
        count=len(k)
        if not count or list(positions)!=list(range(self.length,self.length+count)):
            raise ValueError("missing/duplicate/out-of-order token")
        if self.length+count>self.capacity:raise OverflowError("cache capacity exceeded")
        before=self.k[:self.length].tobytes()+self.v[:self.length].tobytes()
        old_length=self.length
        self.k[old_length:old_length+count]=k;self.v[old_length:old_length+count]=v
        after=self.k[:old_length].tobytes()+self.v[:old_length].tobytes()
        if before!=after:raise AssertionError("published KV was rewritten")
        self.length+=count;self.epoch=self.length
        self.events.append({"begin":old_length,"count":count,"published_epoch":self.epoch,
            "new_payload_bytes":k.nbytes+v.nbytes,"old_payload_rewrite_bytes":0,
            "old_prefix_sha256":hashlib.sha256(before).hexdigest()})

    def read(self,expected_epoch):
        if expected_epoch!=self.epoch:raise ValueError("read of stale/unpublished epoch")
        return self.k[:self.length].copy(),self.v[:self.length].copy()
