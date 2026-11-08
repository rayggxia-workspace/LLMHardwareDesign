"""Proposed 64B management frames and finite reset/provider/journal model.

Separate from ISA instructions and existing RTL pins. The applied-reset and
future-queue proof is a model provider contract, not hardware introspection.
"""
import copy,struct
import images
need=images.need
NAMES=['version','kind','participant','sequence','epoch','generation','bitmap','transaction','status','flags','value0','value1','value2','value3']
KINDS=dict(RESET_REQ=128,RESET_ACK=129,RELEASE=130,QUERY=131,QUERY_REPLY=132)
FORMAT=struct.Struct('<HBBIIIQIHHIIII16s')
def pack(fields):
    need(not(set(fields)-set(NAMES)),'management unknown fields')
    row=dict(version=1,participant=255,sequence=0,epoch=0,generation=0,bitmap=0,transaction=0,status=0,flags=0,value0=0,value1=0,value2=0,value3=0,**{})
    row.update(fields); need(row['kind'] in KINDS.values() and row['version']==1 and row['flags']&~1==0,'management version/kind/flags')
    try: return FORMAT.pack(*[row[n] for n in NAMES],b'\0'*16)
    except struct.error as e: raise ValueError(str(e))
def unpack(raw):
    need(len(raw)==64,'management size'); values=FORMAT.unpack(raw); row=dict(zip(NAMES,values[:-1])); need(values[-1]==b'\0'*16,'management reserved bytes')
    need(pack(row)==raw,'management canonical encoding'); return row
def inventory(kinds):
    names=['controller.mother','external.MEM_and_journal','transport','ingress']
    for b,k in sorted(kinds.items()):
        names+=['controller.local'+str(b),'adapter.'+str(b),'feeder.'+str(b)]
        names+=['provider.'+str(b)+'.'+r for r in images.SPEC['profiles'][k]['macros']]
    need(len(names)<=64 and len(set(names))==len(names),'complete bounded cohort names'); return dict(enumerate(names))


class Coordinator:
    def __init__(self,kinds,files,persistent_state,unknown_transaction=None):
        self.kinds=kinds; self.files=files; self.inventory=inventory(kinds); self.bitmap=(1<<len(self.inventory))-1
        self.providers={i:dict(future=[bytes([i])*16],applied=False) for i in self.inventory}
        self.persistent=copy.deepcopy(persistent_state); self.phase='POISONED'; self.sequence=0; self.epoch=self.generation=1
        self.acks=set(); self.loaded={}; self.tick=0; self.last_ack=None; self.gate=False; self.unknown=unknown_transaction; self.queries={}; self.events=[]
    def record(self,kind,**kw): self.events.append(dict(tick=self.tick,kind=kind,**kw))
    def request(self,sequence,epoch,generation):
        need(self.phase=='POISONED' and sequence>self.sequence and epoch>self.epoch and generation>self.generation,'fresh reset cohort tuple')
        self.sequence=sequence; self.epoch=epoch; self.generation=generation; self.phase='RESETTING'; self.gate=False
        raw=pack(dict(kind=KINDS['RESET_REQ'],sequence=sequence,epoch=epoch,generation=generation,bitmap=self.bitmap))
        self.record('RESET_REQ',hex=raw.hex()); return raw
    def apply(self,participant):
        need(self.phase=='RESETTING' and participant in self.providers,'reset apply participant')
        self.providers[participant]['future'].clear(); self.providers[participant]['applied']=True
        self.record('PROVIDER_APPLIED',participant=participant)
    def ack_frame(self,participant): return pack(dict(kind=KINDS['RESET_ACK'],participant=participant,sequence=self.sequence,epoch=self.epoch,generation=self.generation,bitmap=self.bitmap,flags=1))
    def accept_ack(self,raw):
        m=unpack(raw); p=m['participant']
        need(self.phase=='RESETTING' and m['kind']==KINDS['RESET_ACK'] and p in self.providers and p not in self.acks,'reset ACK member/duplicate/state')
        need((m['sequence'],m['epoch'],m['generation'],m['bitmap'],m['flags'])==(self.sequence,self.epoch,self.generation,self.bitmap,1) and
            m['transaction']==m['status']==m['value0']==m['value1']==m['value2']==m['value3']==0,'reset ACK tuple/reserved semantics')
        # Ground-truth check for this software provider contract. Real hardware
        # must supply a trustworthy applied/quiescent acknowledgment instead.
        need(self.providers[p]['applied'] and not self.providers[p]['future'],'ACK before actual provider future-response flush')
        self.acks.add(p); self.record('RESET_ACK',hex=raw.hex())
        if len(self.acks)==len(self.providers): self.phase='QUIET'; self.last_ack=self.tick
    def quiet(self):
        need(self.phase=='QUIET' and self.tick>self.last_ack and all(not p['future'] for p in self.providers.values()),'additional quiet step / future responses')
        self.phase='RESET_COMPLETE'; self.record('QUIET')
    def reload(self,target,data,complete=True):
        need(self.phase=='RESET_COMPLETE' and target in self.files,'reload admission')
        parsed=images.parse(data,self.kinds.get(int(target[5:])) if target!='mother' else None)
        ram=bytearray([0xcd]*len(data)); limit=len(data) if complete else 16
        for a in range(0,limit,16): ram[a:a+16]=data[a:a+16]
        need(bytes(ram)==data and complete and images.sha(bytes(ram))==images.sha(self.files[target]),'full reload / actual readback / expected image SHA')
        self.loaded[target]=images.sha(bytes(ram)); self.record('RELOAD',target=target,sha256=self.loaded[target])
    def query(self,transaction):
        need(self.phase=='RESET_COMPLETE' and transaction>0,'query before quiescent reset')
        request=pack(dict(kind=KINDS['QUERY'],participant=1,sequence=self.sequence,epoch=self.epoch,generation=self.generation,bitmap=self.bitmap,transaction=transaction))
        row=self.persistent['journal'].get(transaction)
        reply=pack(dict(kind=KINDS['QUERY_REPLY'],participant=1,sequence=self.sequence,epoch=self.epoch,generation=self.generation,bitmap=self.bitmap,transaction=transaction,
            status=2 if row else 3,value0=self.persistent['root'],value1=self.persistent['generation'],value2=row['old'] if row else 0,value3=row['new'] if row else 0))
        self.record('QUERY',request=request.hex(),reply=reply.hex()); return reply
    def accept_query(self,raw,transaction):
        m=unpack(raw)
        need(self.phase=='RESET_COMPLETE' and m['kind']==KINDS['QUERY_REPLY'] and m['participant']==1 and m['transaction']==transaction and
            (m['sequence'],m['epoch'],m['generation'],m['bitmap'])==(self.sequence,self.epoch,self.generation,self.bitmap),'query reply identity')
        row=self.persistent['journal'].get(transaction)
        expected=(2,self.persistent['root'],self.persistent['generation'],row['old'],row['new']) if row else (3,self.persistent['root'],self.persistent['generation'],0,0)
        need((m['status'],m['value0'],m['value1'],m['value2'],m['value3'])==expected and m['flags']==0,'query reply actual journal')
        self.queries[transaction]=m
        if self.unknown==transaction: self.unknown=None
        self.record('QUERY_ACCEPT',hex=raw.hex())
    def release_old(self,transaction):
        need(transaction in self.queries and self.queries[transaction]['status']==2,'old release without definitive publication query')
        row=self.persistent['journal'][transaction]
        need(row['consumer_mask']==3 and row['old']!=self.persistent['root'] and not any(p['future'] for p in self.providers.values()),'old still referenced/current')
        self.persistent['store'].pop(row['old'],None); self.record('OLD_RELEASE',handle=row['old'],transaction=transaction)
    def release(self):
        need(self.phase=='RESET_COMPLETE' and len(self.acks)==len(self.providers) and len(self.loaded)==len(self.files) and self.unknown is None and
            not any(p['future'] for p in self.providers.values()),'release before all ACK/quiet/full reload/outcome query')
        raw=pack(dict(kind=KINDS['RELEASE'],sequence=self.sequence,epoch=self.epoch,generation=self.generation,bitmap=self.bitmap))
        self.gate=True; self.phase='READY'; self.record('RELEASE',hex=raw.hex()); return raw


def campaign(files,kinds,state,transaction):
    results=[]
    def reject(name,fn):
        try: fn()
        except ValueError: results.append(dict(name=name,rejected=True)); return
        raise ValueError('accepted invalid reset/query action '+name)
    c=Coordinator(kinds,files,state,transaction); before=copy.deepcopy(c.persistent)
    reject('release_before_reset',c.release); reject('query_before_reset',lambda:c.query(transaction)); c.request(1,2,2)
    p=next(iter(c.inventory)); reject('unapplied_ACK',lambda:c.accept_ack(c.ack_frame(p)))
    c.apply(p); raw=c.ack_frame(p); m=unpack(raw)
    reject('stale_reset_sequence',lambda:c.accept_ack(pack(dict(m,sequence=0))))
    reject('wrong_reset_epoch',lambda:c.accept_ack(pack(dict(m,epoch=1))))
    reject('wrong_reset_generation',lambda:c.accept_ack(pack(dict(m,generation=1))))
    reject('wrong_cohort_bitmap',lambda:c.accept_ack(pack(dict(m,bitmap=m['bitmap']^1))))
    reject('unknown_participant',lambda:c.accept_ack(pack(dict(m,participant=63))))
    c.accept_ack(raw); reject('duplicate_ACK',lambda:c.accept_ack(raw)); reject('missing_provider_ACK',c.release)
    for p in list(c.inventory)[1:]: c.apply(p); c.accept_ack(c.ack_frame(p))
    reject('quiet_same_tick',c.quiet); c.tick+=1; c.quiet()
    need(c.persistent==before,'reset cleared persistent committed state/journal')
    reject('old_release_before_query',lambda:c.release_old(transaction))
    target=next(iter(files)); reject('partial_reload',lambda:c.reload(target,files[target],False)); reject('missing_reload',c.release)
    for target,data in files.items(): c.reload(target,data)
    reject('unknown_publication_outcome',c.release)
    reply=c.query(transaction); r=unpack(reply)
    reject('query_wrong_transaction',lambda:c.accept_query(pack(dict(r,transaction=transaction+1)),transaction))
    reject('query_wrong_epoch',lambda:c.accept_query(pack(dict(r,epoch=1)),transaction))
    bad=bytearray(reply); bad[-1]=1; reject('reserved_management_bits',lambda:unpack(bytes(bad)))
    c.accept_query(reply,transaction)
    if r['status']==2: c.release_old(transaction)
    release=unpack(c.release()); need(release['epoch']==2 and c.gate and c.phase=='READY','new epoch release')
    results.append(dict(name='all_applied_flush_reload_query_release',passed=True,participants=len(c.inventory),new_epoch=2,root=c.persistent['root']))
    need(FORMAT.size==64 and unpack(pack(dict(kind=128,sequence=0x12345678,epoch=2,generation=3,bitmap=0x0102030405060708)))['bitmap']==0x0102030405060708,'management endian roundtrip')
    raw=pack(dict(kind=128,sequence=0x12345678,epoch=2,generation=3,bitmap=0x0102030405060708)); need(raw[4:8].hex()=='78563412' and raw[16:24].hex()=='0807060504030201','independent little-endian bytes')
    return dict(results=results,events=c.events,inventory=c.inventory,state=c.persistent,release_certificate=release,rtl_tested=False,
        real_provider_reset_tested=False,CDC_tested=False,provider_contract_conditional=True)
