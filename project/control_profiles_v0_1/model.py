"""Finite candidate control interpreter. Ticks are not hardware cycles.

No numerical native implementation: service data is an opaque version token.
No RTL state injection: immutable images are installed by write/readback.
"""
import copy,hashlib
import images
codec=images.codec; need=images.need


class CPU:
    def __init__(self,name,parsed):
        self.name=name; self.image=parsed; self.role='mother' if name=='mother' else 'local'; self.block=None if name=='mother' else int(name[5:])
        self.active=name=='mother'; self.pc=0; self.regs=[0]*8; self.args=[0]*8; self.task=None; self.sequence=0; self.global_token=None
        self.ireg=None; self.read=None; self.pm=None; self.hold=False; self.steps=0; self.token=None; self.obj=None; self.valid=False
        self.error=0; self.error_pc=0xffffffff; self.cancelled=False; self.drain_age=0; self.read_bytes=self.write_bytes=0; self.effects=set()


class Model:
    def __init__(self,files,kinds,parameters,environment=None,initial=None):
        self.files=files; self.kinds=kinds; self.parsed={}; self.load=[]
        for target,data in files.items():
            ram=bytearray([0xcd]*len(data)); written=bytearray(len(data))
            for a in range(0,len(data),16): ram[a:a+16]=data[a:a+16]; written[a:a+16]=b'\1'*16
            need(all(written) and bytes(ram)==data,'actual configuration write/readback')
            self.parsed[target]=images.parse(bytes(ram),kinds.get(int(target[5:])) if target!='mother' else None)
            self.load.append(dict(target=target,bytes=len(data),sha256=images.sha(bytes(ram)),full_readback=True))
        need(len(parameters)==8 and all(type(v) is int and 0<=v<=0xffffffff for v in parameters),'immutable scalar area')
        self.parameters=list(parameters); self.parameter_bytes=b''.join(v.to_bytes(4,'little') for v in parameters)
        self.env=dict(environment or {}); self.initial=copy.deepcopy(initial or dict(root=5,generation=7,store={5:0x12345678},journal={}))
        need(self.initial['root']>0 and self.initial['root'] in self.initial['store'],'nonzero committed state')
        self.sequence={b:0 for b in kinds}; self.generation=1; self.epoch=self.env.get('epoch',1); self.job=self.env.get('job',7)

    def install_job(self,parameters,job,epoch=None):
        need(self.finished and not self.poison and not self.channels and not self.services and not self.credits,'job replacement before actual closure')
        need(not self.publication_attempted or self.publication_ack,'publication outcome requires explicit query before another job')
        need(job>self.job and len(parameters)==8 and all(type(v) is int and 0<=v<2**32 for v in parameters),'new job metadata')
        self.initial=copy.deepcopy(self.state); self.parameters=list(parameters); self.parameter_bytes=b''.join(v.to_bytes(4,'little') for v in parameters)
        self.job=job; self.epoch=self.epoch if epoch is None else epoch

    def event(self,kind,**kw): self.trace.append(dict(tick=self.t,kind=kind,job=self.job,epoch=self.epoch,**kw))
    def retire(self,c,next_pc=None):
        need(c.ireg is not None and c.steps<min(c.image['header']['max_steps'],c.task['max_steps'] if c.task else 256),'step budget')
        pc=c.pc; word=c.ireg; c.pc=pc+1 if next_pc is None else next_pc; c.steps+=1
        self.event('RETIRE',cpu=c.name,pc=pc,word=hex(word),next_pc=c.pc,registers=list(c.regs)); c.ireg=None; c.hold=False
    def trap(self,c,status,pc=None):
        if not c.error or c.error==11 and status==9: c.error=status; c.error_pc=c.pc if pc is None else pc
        c.ireg=None
        if c.role=='mother': self.abort=True; self.first_error=self.first_error or dict(status=status,source=255,pc=c.error_pc)
        else: c.cancelled=True
        self.event('TRAP',cpu=c.name,status=status,pc=c.error_pc)
    def offer(self,name,payload,action,c=None,**kw):
        need(name not in self.channels and len(self.channels)<8,'bounded holding channels')
        self.channels[name]=dict(payload=copy.deepcopy(payload),action=action,cpu=c.name if c else None,offered=self.t,**kw)
        self.event('OFFER',channel=name,payload=copy.deepcopy(payload),action=action)
    def begin_read(self,c,kind,offset,size,index=0):
        need(c.read is None and c.pm is None and size%16==0 and offset%16==0 and 0<=offset and offset+size<=len(c.image['bytes']),'PM record extent')
        c.read=dict(kind=kind,offset=offset,size=size,buffer=bytearray(),index=index)
    def descriptor(self,c,name,index):
        h=c.image['header']; need(0<=index<h[name+'_count'],'descriptor index')
        self.begin_read(c,name,h[name+'_offset']+dict(task=64,object=64,execution=128)[name]*index,dict(task=64,object=64,execution=128)[name],index)
    def pm_step(self,c):
        if (c.cancelled or self.abort and c.role=='mother') and c.pm is None: c.read=None
        if c.pm is not None and self.t>=c.pm['due']:
            p=c.pm; raw=c.image['bytes'][p['address']:p['address']+16]
            self.event('PM_RSP',cpu=c.name,address=p['address'],data=raw.hex()); c.pm=None
            if c.cancelled or self.abort and c.role=='mother': c.read=None
            else:
                r=c.read; r['buffer'].extend(raw)
                if len(r['buffer'])==r['size']:
                    c.read=None; kind=r['kind']; raw=bytes(r['buffer'])
                    if kind=='instruction': c.ireg=int.from_bytes(raw,'little'); self.event('FETCH',cpu=c.name,pc=c.pc,word=hex(c.ireg))
                    elif kind=='task': c.task=codec.unpack_record('task',raw); c.pc=c.task['entry_pc']
                    elif kind=='object':
                        obj=codec.unpack_record('object',raw); need(c.obj is None and obj['base_bytes']+obj['capacity_bytes']<=16384,'scratch ownership/range')
                        c.obj=obj; c.valid=False; self.event('OPEN',cpu=c.name,object=0); self.retire(c)
                    else: self.issue_service(c,codec.unpack_record('execution',raw))
        if c.read is not None and c.pm is None and not c.cancelled and not(self.abort and c.role=='mother'):
            address=c.read['offset']+len(c.read['buffer']); c.pm=dict(address=address,due=self.t+1+self.env.get('latency',2))
            self.event('PM_REQ',cpu=c.name,address=address,owner=c.read['kind'])
    def issue_service(self,c,e):
        ins=codec.decode_instruction(c.ireg,'local'); need(c.obj is not None and c.token is None and e['resource']==ins['a'],'service/object/token ownership')
        need(e['src0']==255 or c.valid,'compute read before prior ACK/WAIT')
        if self.abort or c.cancelled: return
        number=self.next_operation; self.next_operation+=1
        c.token=dict(number=number,token=ins['b'],done=None,error=0,pc=c.pc,descriptor=e); c.hold=True
        self.offer('cmd.'+c.name,dict(job=self.job,epoch=self.epoch,task_sequence=c.sequence,token=ins['b'],operation=number,descriptor=codec.pack_record('execution',e).hex(),
            args=list(c.args)), 'command',c)
    def service_effect(self,s):
        c=self.cpus[s['cpu']]; e=s['descriptor']; action=e['native0']; p=list(self.parameters)
        need(s['args'][:5]==p[:5],'candidate adapter immutable state tuple differs from CALL')
        if action==3 and p[4] in self.state['journal']:
            row=self.state['journal'][p[4]]
            need((row['old'],row['new'],row['generation'])==(p[0],p[1],p[2]+1),'transaction ID collision')
            self.event('PUBLISH_REPLAY',operation=s['number'],transaction=p[4],old=p[0],new=p[1],generation=row['generation'])
            s.update(read_bytes=0,write_bytes=0,effect_tick=self.t,phase='response',due=self.t+2,committed=True); return
        if action:
            need(p[0]!=0 and p[1]!=0 and p[0]!=p[1] and p[0]==self.state['root'] and p[2]==self.state['generation'] and
                p[3] in (1,3) and p[4]>0,'old/next namespace or generation')
        source=self.sram[c.block] if e['src0']==0 else self.input_data
        if action==1:
            need(len(self.state['store'])+int(p[1] not in self.state['store'])<=16,'finite external state handle store')
            source=self.state['store'][p[0]].to_bytes(4,'little')*4
            self.event('OLD_READ',operation=s['number'],handle=p[0],generation=p[2],data=source.hex())
        if action==4:
            need(self.shadow is not None and self.source_done and self.shadow['handle']==p[1],'next read before actual producer completion')
            source=self.shadow['payload'].to_bytes(4,'little')*4
            self.event('NEXT_READ',operation=s['number'],cpu=c.name,handle=p[1],data=source.hex())
        data=hashlib.sha256(source+bytes([e['resource']])+s['number'].to_bytes(4,'little')+self.job.to_bytes(4,'little')).digest()[:16]
        if action==1:
            need(p[4] not in self.state['journal'],'transaction replay update')
            self.shadow=dict(handle=p[1],old=p[0],generation=p[2],transaction=p[4],payload=int.from_bytes(data[:4],'little'))
            self.event('NEXT_WRITE',operation=s['number'],handle=p[1],old=p[0],generation=p[2],transaction=p[4],payload=self.shadow['payload'])
        if action==2:
            need(self.shadow is not None and self.source_done and self.shadow['handle']==p[1],'consumer before completed next producer')
        if action==3:
            need(self.shadow is not None and self.source_done and self.consumer_ack&p[3]==p[3] and self.consumer_done&p[3]==p[3] and
                not any(x['number']!=s['number'] for x in self.services.values()),'publish before all actual consumers/ACKs/terminals')
            self.state['store'][p[1]]=self.shadow['payload']; self.state['root']=p[1]; self.state['generation']+=1
            self.state['journal'][p[4]]=dict(old=p[0],new=p[1],generation=self.state['generation'],committed=True,consumer_mask=p[3])
            self.event('PUBLISH',operation=s['number'],old=p[0],new=p[1],generation=self.state['generation'],transaction=p[4],mask=p[3]); s['committed']=True
        else:
            self.sram[c.block]=data; self.event('S_WRITE',cpu=c.name,operation=s['number'],data=data.hex(),input_sha256=images.sha(source))
        s['read_bytes']=0 if action==3 else 16; s['write_bytes']=0 if action==3 else 16
        s['effect_tick']=self.t; s['phase']='response'; s['due']=self.t+2+self.env.get('latency',2)
    def channels_step(self):
        for name,q in list(self.channels.items()):
            c=self.cpus[q['cpu']] if q['cpu'] else None; action=q['action']
            ready=self.t>q['offered'] and (not self.env.get('stall') or self.t%5==0)
            if action=='call': ready=ready and not self.cpus['local'+str(q['block'])].active
            if action=='command': ready=ready and c.name not in self.services
            if action=='terminal': ready=ready and self.credits[c.global_token]['terminal'] is None
            if action=='response' and q.get('blocked'): ready=False
            if action=='host' and self.env.get('hold_result'): ready=ready and self.t-q['offered']>=40
            self.event('SAMPLE',channel=name,ready=bool(ready),payload=copy.deepcopy(q['payload']))
            if not ready: continue
            del self.channels[name]; self.event('ACCEPT',channel=name,action=action,payload=copy.deepcopy(q['payload']))
            if action=='call':
                m=codec.unpack_record('task_message',bytes.fromhex(q['payload']['hex'])); child=self.cpus['local'+str(q['block'])]
                need(not child.active and child.obj is None and child.token is None,'CALL target not drained')
                child.active=True; child.sequence=m['task_sequence']; self.sequence[child.block]=child.sequence; child.global_token=m['completion_token']
                child.regs=[0]*8; child.args=[m['arg'+str(i)] for i in range(8)]; child.steps=0; child.error=0; child.error_pc=0xffffffff
                child.cancelled=False; child.drain_age=0; child.effects=set(); child.read_bytes=child.write_bytes=0; child.task=None; child.ireg=None; child.hold=False
                self.credits[child.global_token]['accepted']=self.t; self.descriptor(child,'task',m['task_descriptor']); self.retire(c)
            elif action=='cancel':
                child=self.cpus['local'+str(q['block'])]; child.cancelled=True
                if not child.error: child.error=11; child.error_pc=child.pc
                self.event('CANCEL',cpu=child.name,pc=child.pc)
            elif action=='command':
                tok=c.token; e=tok['descriptor']; self.services[c.name]=dict(cpu=c.name,number=tok['number'],descriptor=e,args=list(c.args),phase='effect',due=self.t+3+self.env.get('latency',2),committed=False)
                if e['native0']:
                    self.event('PARAM_REQ',cpu=c.name,reference=e['parameter_ref'],bytes=32)
                    self.services[c.name].update(phase='parameter',due=self.t+2)
                if e['native0']==3: self.publication_attempted=True
                self.retire(c)
            elif action=='response':
                token=c.token; s=self.services.pop(c.name); token.update(done=self.t,error=q['payload']['status'])
                c.read_bytes+=q['payload']['read_bytes']; c.write_bytes+=q['payload']['write_bytes']
                if s['descriptor']['native0']==2 and not q['payload']['status']: self.consumer_ack|=s['descriptor']['native1']; c.effects.add(('consumer',s['descriptor']['native1']))
                if s['descriptor']['native0']==1 and not q['payload']['status']: c.effects.add(('source',0))
                if s['descriptor']['native0']==3 and not q['payload']['status']: self.publication_ack=True
                if q['payload']['status']: self.trap(c,9,token['pc'])
            elif action=='terminal':
                p=codec.unpack_record('event_message',bytes.fromhex(q['payload']['hex'])); self.credits[c.global_token]['terminal']=p
                self.confirmed_read_bytes+=p['confirmed_read_bytes']; self.confirmed_write_bytes+=p['confirmed_write_bytes']
                c.active=False; c.hold=False; c.ireg=None
                if not p['status']:
                    for effect,bit in c.effects:
                        if effect=='source': self.source_done=True
                        else: self.consumer_done|=bit
                elif self.first_error is None: self.first_error=dict(status=p['status'],source=c.block,pc=p['error_pc']); self.abort=True
            elif action=='param':
                need(q['index']<8,'G_PARAM bounds'); c.regs[q['register']]=int.from_bytes(bytes.fromhex(q['payload']['data']),'little'); self.retire(c)
            else: self.outcome=q['payload']; self.finished=True
    def terminal(self,c):
        need(c.token is None and c.obj is None and c.pm is None and c.read is None,'terminal before owned drain')
        packet=codec.pack_record('event_message',dict(kind=3 if c.error else 2,source_block=c.block,job_id=self.job,epoch=self.epoch,task_sequence=c.sequence,
            completion_token=c.global_token,event_id=255,status=c.error,error_pc=c.error_pc,confirmed_read_bytes=c.read_bytes,confirmed_write_bytes=c.write_bytes))
        c.hold=True; self.offer('return.'+c.name,dict(hex=packet.hex()),'terminal',c)
    def local_step(self,c,ins):
        op=ins['op']; next_pc=None
        if op=='L_OPEN': self.descriptor(c,'object',ins['a']); return
        if op=='L_EXEC': self.descriptor(c,'execution',ins['c']); return
        if op=='L_WAIT':
            need(c.token is not None and ins['x']==1<<c.token['token'],'WAIT unallocated token')
            if c.token['done'] is None or c.token['done']>=self.t: return
            need(not c.token['error'],'error token reached ordinary WAIT'); c.token=None; c.valid=True
        elif op=='L_MOVI': c.regs[ins['a']]=ins['x']
        elif op=='L_ARG': need(c.task['argument_mask']&(1<<ins['b']),'ARG undeclared'); c.regs[ins['a']]=c.args[ins['b']]
        elif op=='L_ADDI':
            delta=ins['x'] if ins['x']<2**31 else ins['x']-2**32; value=c.regs[ins['a']]+delta
            need(0<=value<2**32,'ADDI overflow'); c.regs[ins['a']]=value
        elif op=='L_LOOP':
            need(0<=ins['x']<c.pc and c.regs[ins['a']]>0,'LOOP counter/back edge'); c.regs[ins['a']]-=1
            next_pc=ins['x'] if c.regs[ins['a']] else c.pc+1
        elif op=='L_BRANCH':
            need(all(c.pc<v<c.image['header']['instruction_count'] for v in [ins['x'],ins['y']]),'BRANCH forward extent')
            next_pc=ins['x'] if c.regs[ins['a']] else ins['y']
        elif op=='L_DROP': need(c.obj is not None and c.token is None,'DROP obligations'); c.obj=None; c.valid=False; self.event('DROP',cpu=c.name)
        elif op=='L_END': self.retire(c); self.terminal(c); return
        elif op=='L_FAIL': self.trap(c,ins['x']); return
        elif op!='NOP': raise ValueError('local unsupported instruction')
        self.retire(c,next_pc)
    def mother_step(self,c,ins):
        op=ins['op']; next_pc=None
        if op=='G_PARAM':
            need(ins['x']<8,'G_PARAM bounds'); c.hold=True
            self.offer('parameter',dict(index=ins['x'],data=self.parameter_bytes[4*ins['x']:4*ins['x']+4].hex()),'param',c,index=ins['x'],register=ins['a']); return
        if op=='G_MOVI': c.regs[ins['a']]=ins['x']
        elif op=='G_BRANCH':
            need(all(c.pc<v<c.image['header']['instruction_count'] for v in [ins['x'],ins['y']]),'mother forward branch')
            next_pc=ins['x'] if c.regs[ins['a']] else ins['y']
        elif op=='G_LOOP':
            need(0<=ins['x']<c.pc and c.regs[ins['a']]>0,'mother loop counter/back edge'); c.regs[ins['a']]-=1
            next_pc=ins['x'] if c.regs[ins['a']] else c.pc+1
        elif op=='G_CALL':
            block=ins['a']; token=ins['b']; need(block in self.sequence and token not in self.credits and len(self.credits)<2,'global finite credit/target')
            child=self.cpus['local'+str(block)]; need(not child.active and not any(v['block']==block for v in self.credits.values()),'target reservation')
            packet=dict(kind=0,target_block=block,job_id=self.job,epoch=self.epoch,task_sequence=self.sequence[block]+1,task_descriptor=ins['c'],completion_token=token,
                program_image_id=child.image['header']['program_image_id'],topology_id=images.TOPOLOGY)
            packet.update({'arg'+str(i):c.regs[i] for i in range(8)})
            self.credits[token]=dict(block=block,terminal=None,accepted=None,cancel=False); c.hold=True
            self.offer('call',dict(hex=codec.pack_record('task_message',packet).hex()),'call',c,block=block); return
        elif op=='G_WAIT':
            selected=[k for k in range(32) if ins['x']&(1<<k)]; need(selected and all(k in self.credits for k in selected),'global WAIT allocation')
            if any(self.credits[k]['terminal'] is None for k in selected): return
            for k in selected: self.credits.pop(k)
        elif op=='G_END':
            need(not self.credits and not self.services and not self.channels,'global END obligations')
            self.retire(c); self.host_result(0); c.active=False; return
        elif op=='G_FAIL': self.trap(c,ins['x']); return
        elif op!='NOP': raise ValueError('mother unsupported instruction')
        self.retire(c,next_pc)
    def host_result(self,status):
        need(not self.credits and not self.services and not any(c.active or c.token or c.obj for n,c in self.cpus.items() if n!='mother'),'host result before obligations')
        self.offer('host',dict(status=status,job=self.job,epoch=self.epoch,read_bytes=self.confirmed_read_bytes,
            write_bytes=self.confirmed_write_bytes,
            state_disposition='COMMITTED' if self.publication_ack else 'UNKNOWN' if self.publication_attempted else 'OLD_ACTIVE'), 'host')
    def run(self):
        self.cpus={n:CPU(n,p) for n,p in self.parsed.items()}; self.sram=getattr(self,'sram',{b:b'\xcd'*16 for b in self.kinds}); self.state=copy.deepcopy(self.initial)
        self.input_data=hashlib.sha256(('job:'+str(self.job)).encode()).digest()[:16]; self.shadow=None; self.consumer_ack=self.consumer_done=0; self.source_done=False
        self.publication_ack=False; self.publication_attempted=False; self.confirmed_read_bytes=self.confirmed_write_bytes=0
        self.channels={}; self.services={}; self.credits={}; self.trace=[]; self.next_operation=0
        self.abort=False; self.first_error=None; self.poison=False; self.finished=False; self.outcome=None; self.cancel_sent=False
        self.t=0; self.event('BEGIN',parameters=list(self.parameters),initial=copy.deepcopy(self.state),initial_task_sequences=dict(self.sequence),input_data=self.input_data.hex(),images=[x.copy() for x in self.load])
        for self.t in range(8192):
            self.channels_step()
            if self.finished: break
            for name,s in list(self.services.items()):
                if self.t<s['due']: continue
                c=self.cpus[name]
                if s['phase']=='parameter':
                    self.event('PARAM_RSP',cpu=name,data=self.parameter_bytes.hex()); s.update(phase='effect',due=self.t+1)
                elif s['phase']=='effect':
                    if self.env.get('missing_service')==s['number']: continue
                    try:
                        if self.env.get('error_service')==s['number'] and not self.env.get('error_after_effect'):
                            s.update(read_bytes=0,write_bytes=0,effect_tick=self.t,phase='response',due=self.t+2)
                        else: self.service_effect(s)
                    except ValueError as error:
                        self.event('SERVICE_REJECT',cpu=name,message=str(error)); s.update(read_bytes=0,write_bytes=0,effect_tick=self.t,phase='response',due=self.t+2,rejected=True)
                elif 'response.'+name not in self.channels:
                    status=9 if s.get('rejected') or self.env.get('error_service')==s['number'] else 0
                    self.offer('response.'+name,dict(operation=s['number'],status=status,read_bytes=s['read_bytes'],write_bytes=s['write_bytes']), 'response',c,
                        blocked=bool(s['committed'] and self.env.get('lost_publish_ACK')))
                    s['phase']='held'
            for name,c in self.cpus.items():
                self.pm_step(c)
                if not c.active or c.hold or c.read is not None or c.pm is not None: continue
                if c.role=='local' and c.cancelled:
                    if c.token is not None:
                        if c.token['done'] is None:
                            c.drain_age+=1
                            if c.drain_age>=128: self.poison=True
                            continue
                        self.event('CANCEL_TOKEN',cpu=name,operation=c.token['number']); c.token=None
                    if c.obj is not None: self.event('DROP',cpu=name); c.obj=None; c.valid=False
                    c.ireg=None; self.terminal(c); continue
                if self.abort and c.role=='mother': continue
                if c.role=='local' and c.task is None: continue
                if c.ireg is None:
                    if c.pc>=c.image['header']['instruction_count']: self.trap(c,6); continue
                    self.begin_read(c,'instruction',128+16*c.pc,16); continue
                try:
                    need(c.steps<min(c.image['header']['max_steps'],c.task['max_steps'] if c.task else 256),'instruction step budget')
                    ins=codec.decode_instruction(c.ireg,c.role)
                    if c.role=='mother': self.mother_step(c,ins)
                    else: self.local_step(c,ins)
                except ValueError as error: self.event('CONTROL_REJECT',cpu=name,message=str(error)); self.trap(c,12 if 'budget' in str(error) else 7)
            if self.abort:
                for token,ctx in list(self.credits.items()):
                    child=self.cpus['local'+str(ctx['block'])]
                    if ctx['terminal'] is None and ctx['accepted'] is not None and not ctx['cancel'] and 'call' not in self.channels:
                        packet=dict(kind=1,target_block=child.block,job_id=self.job,epoch=self.epoch,task_sequence=child.sequence,task_descriptor=0,completion_token=token,
                            program_image_id=child.image['header']['program_image_id'],topology_id=images.TOPOLOGY)
                        self.offer('cancel.'+child.name,dict(hex=codec.pack_record('task_message',packet).hex()),'cancel',self.cpus['mother'],block=child.block); ctx['cancel']=True
                if self.credits and all(v['terminal'] is not None for v in self.credits.values()) and not self.channels and not self.services and self.cpus['mother'].pm is None:
                    self.credits.clear(); self.cpus['mother'].active=False; self.cpus['mother'].read=None; self.cpus['mother'].pm=None; self.host_result(self.first_error['status'])
                elif not self.credits and not self.channels and not self.services and self.cpus['mother'].pm is None:
                    self.cpus['mother'].active=False; self.host_result(self.first_error['status'])
            cancel_when=self.env.get('cancel_when')
            cancel_trigger=self.env.get('cancel_tick')==self.t or cancel_when=='next_write' and self.shadow is not None or \
                cancel_when=='two_consumers' and len(self.credits)==2 or cancel_when=='command_offer' and any(n.startswith('cmd.') for n in self.channels) or \
                cancel_when=='publish_offer' and any(n.startswith('cmd.') and codec.unpack_record('execution',bytes.fromhex(q['payload']['descriptor']))['native0']==3 for n,q in self.channels.items())
            if cancel_trigger and not self.cancel_sent:
                self.cancel_sent=True
                self.abort=True; self.first_error=dict(status=11,source=255,pc=self.cpus['mother'].pc); self.event('HOST_CANCEL')
            if any(s['committed'] and self.env.get('lost_publish_ACK') and self.t-s['effect_tick']>128 for s in self.services.values()): self.poison=True
            if any(self.t-s['due']>128 for s in self.services.values() if self.env.get('missing_service')==s['number']): self.poison=True
            if self.poison: self.event('POISON',credits=len(self.credits),services=len(self.services),publication_unknown=bool(self.state['journal'] and not self.publication_ack)); break
        else: raise RuntimeError('research execution bound, no architectural completion')
        need(self.finished or self.poison,'missing terminal disposition')
        return dict(trace=self.trace,state=self.state,pending_shadow=self.shadow,outcome=self.outcome,poison=self.poison,ticks=self.t+1,loads=self.load,
            final_credits=len(self.credits),final_services=len(self.services),publication_ack=self.publication_ack,
            rtl_tested=False,ticks_are_hardware_cycles=False,deployable=False)
