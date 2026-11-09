"""Independent addressed execution of finite row programs.

Does not call the allocator, its event cost function, its grouping heuristic,
or an unbounded operand dictionary. Observed results are verification only.
"""
from resident_batch_graph import digest,verify as verify_tile


def replay(tile,program,inputs):
    verify_tile(tile)
    if (program.get('status')!='planned' or program.get('kind')!='native-resident-row-program-v1' or
        program.get('tile_sha256')!=digest(tile)):raise ValueError('row program/source binding differs')
    graph=tile['graph'];objects=graph['objects'];actors=program['actors'];names=tuple(sorted(actors))
    if ({a['kind'] for a in actors.values()}!={'M','E'} or len({a['site'] for a in actors.values()})!=len(actors)):
        raise ValueError('row program needs independent M/E stores')
    memory={};tags={}
    for name,a in actors.items():
        if (type(a['words'])!=int or a['words']<a['stride'] or a['stride']!=(8 if a['kind']=='M' else 1) or
            a['words']%a['stride'] or any(type(a[t])!=int or a[t]<1 for t in ('load_ticks','store_ticks'))):
            raise ValueError('invalid row actor geometry')
        memory[name]=[None]*a['words'];tags[name]={}
    row_timing=program['row_timing'];scalar=program['scalar_timing']
    contract=program.get('operand_contract');masked=contract is not None
    if masked:
        mask=contract.get('operand_mask',{});proof=contract.get('proof',{});shas=[proof.get('manifest_sha256',''),*proof.get('logs_sha256',[])]
        if (contract.get('kind')!='native-resident-services-active-prefix-v1' or mask.get('kind')!='native-M-active-prefix-v1' or
            mask.get('padding_writes') is not False or mask.get('initializations')!=['zero','ones','mixed','unknown'] or
            mask.get('rows')!=[1,8] or mask.get('k')!=[1,2] or mask.get('columns')!=1 or
            contract.get('rtl_sha256')!=row_timing['rtl_sha256'] or contract.get('profile')!=row_timing['profile'] or
            len(shas)!=5 or len(set(shas[1:]))!=4 or
            any(not isinstance(s,str) or len(s)!=64 or any(c not in '0123456789abcdef' for c in s) for s in shas) or
            len(proof.get('cases_per_initialization',[]))!=4 or any(type(n)!=int or n<1 for n in proof['cases_per_initialization'])):
            raise ValueError('independent active-prefix proof differs')
    from resident_timing import validate
    validate(scalar)
    if (row_timing.get('kind')!='native-resident-row-services-v1' or
        len(row_timing.get('proof',{}).get('logs_sha256',[]))!=3 or
        len(row_timing['proof'].get('cases_per_initialization',[]))!=3 or
        any(n<1 for n in row_timing['proof']['cases_per_initialization']) or
        any(scalar['rtl_sha256'].get(k)!=v for k,v in row_timing.get('rtl_sha256',{}).items())):
        raise ValueError('row service qualification differs')
    external={program['zero_address']:0};external_tags={};observed={};bank={};pending={};executed=set()
    if not 0<=program['zero_address']<tile['scratch_start']:raise ValueError('invalid row zero address')
    for name,o in objects.items():
        if o['kind']=='produced':continue
        value=o['literal'] if 'literal' in o else inputs[(o['tensor'],o['index'])]
        if type(value)!=int or not -(1<<31)<=value<1<<31:raise ValueError('row source outside S32')
        word=value&0xffffffff;addr=o['external_address']
        if addr in external and external[addr]!=word:raise ValueError('row external source aliases')
        external[addr]=word;external_tags.setdefault(addr,set()).add(name)
    nodes={n['id']:n for n in graph['operations'] if 'reuse_of' not in n}
    copy_ticks=service_ticks=loads=stores=0;groups=0;peak={name:0 for name in names};row_executes=0
    def read(name,address,record=None):
        if type(address)!=int or not 0<=address<len(memory[name]) or memory[name][address] is None:
            raise ValueError('row read outside explicitly written finite SRAM')
        if record is not None and tags[name].get(address)!=record:raise ValueError('row operand identity differs')
        peak[name]=max(peak[name],address+1);return memory[name][address]
    def write(name,address,value,record=None):
        if type(address)!=int or not 0<=address<len(memory[name]) or not 0<=value<1<<128:
            raise ValueError('row write outside finite SRAM')
        memory[name][address]=value;peak[name]=max(peak[name],address+1)
        if record is not None:tags[name][address]=record
        else:tags[name].pop(address,None)
    def s16(word,lane):
        x=(word>>(16*lane))&65535;return x-65536 if x>=32768 else x
    def service(e):
        op=e['op']
        try:
            if op=='ROW_M_TERM':
                p=row_timing['profile'];r=str(e['rows'])
                return p['P'][r]['0']+p['P'][r][str(e['k'])]+p['feeder'][r][str(int(e['reuse_b']))]
            if op=='ROW_M_FINAL':
                return row_timing['profile']['P'][str(e['rows'])][str(64+(1 if e['width']==16 else 2)*64+e['shift'])]
            if op=='E':return scalar['profile']['E'][str(e['opcode']+16*len(e['inputs'])+64*e['shift'])]
            return 0
        except KeyError as exc:raise ValueError('row command lacks measured profile') from exc
    for e in program['events']:
        actor=e['actor'];a=actors[actor];kind=e['op']
        service_ticks+=service(e)
        if kind in ('LOAD','LOAD_ZERO'):
            if e.get('wait_ack') is not True:raise ValueError('row LOAD lacks ACK')
            at=e['external_address']
            if type(at)!=int or not 0<=at<tile['external_capacity_words'] or at not in external:
                raise ValueError('row LOAD lacks actual external backing')
            if kind=='LOAD_ZERO':
                if at!=program['zero_address'] or external[at]!=0:raise ValueError('row guard is not explicit zero')
                write(actor,e['address'],0)
            else:
                if e['record'] not in external_tags.get(at,set()):raise ValueError('row LOAD has stale external identity')
                if at!=objects[e['record']]['external_address']:raise ValueError('row LOAD address differs')
                write(actor,e['address'],external[at],e['record'])
            loads+=1;copy_ticks+=a['load_ticks']
        elif kind in ('STORE','STORE_COMMIT'):
            if e.get('wait_ack') is not True:raise ValueError('row STORE lacks ACK')
            value=e['record'];word=read(actor,e['address'],value);at=e['external_address']
            if value not in observed or observed[value]!=word:raise ValueError('row STORE is not a computed native result')
            if kind=='STORE_COMMIT':
                if not any((c['record'],c['original_record'],c['external_address'])==(value,e['commit_for'],at)
                           for c in graph['external_commits']):raise ValueError('row output commit differs')
            elif at!=objects[value]['external_address']:raise ValueError('row spill address differs')
            if type(at)!=int or not 0<=at<tile['external_capacity_words']:raise ValueError('row STORE outside capacity')
            external[at]=word;external_tags[at]={value};stores+=1;copy_ticks+=a['store_ticks']
        elif kind=='ROW_M_TERM':
            members=e['native'];r=e['rows']
            if (a['kind']!='M' or type(r)!=int or not 1<=r<=8 or len(members)!=r or len(set(members))!=r or
                any(name not in nodes or nodes[name]['kind']!='M' or name in executed for name in members)):
                raise ValueError('invalid row M members')
            ns=[nodes[name] for name in members];first=ns[0];old=pending.get(actor)
            ti=e['term']
            if old is None:
                if ti!=0 or e['clear'] is not True:raise ValueError('row M context starts without clear')
                old={'members':members,'term':0,'acc':[0]*r,'final':set()};groups+=1
            elif old['members']!=members or old['term']!=ti or old['final']:
                raise ValueError('row M context overwritten or term reordered')
            if ti>=len(first['terms']):raise ValueError('extra row M term')
            t=first['terms'][ti]
            if ((e['k'],e['coefficient'],e['scale_shift'],e['clear'])!=(first['k'],t['coefficient'],t['scale_shift'],ti==0) or
                e['a_records']!=[n['terms'][ti]['a'] for n in ns] or e['b_record']!=t['b'] or
                any((n['k'],n['width'],n['shift'],len(n['terms']))!=(first['k'],first['width'],first['shift'],len(first['terms'])) or
                    n['terms'][ti]['b']!=t['b'] or n['terms'][ti]['coefficient']!=t['coefficient'] or
                    n['terms'][ti]['scale_shift']!=t['scale_shift'] for n in ns)):
                raise ValueError('row M changed scalar native semantics')
            if e['a']%4 or e['k'] not in (1,2):raise ValueError('row feeder alignment/segment differs')
            if e['a']+4*((r+3)//4)>a['words']:raise ValueError('row A wide read crosses SRAM boundary')
            if not masked:
                for j in range(4*((r+3)//4)):
                    word=read(actor,e['a']+j)
                    if j>=r and word!=0:raise ValueError('row A guard changed')
            av=[read(actor,e['a']+j,record) for j,record in enumerate(e['a_records'])]
            if e['reuse_b']:
                if actor not in bank or bank[actor][0]!=t['b'] or e['b'] is not None:raise ValueError('row B reuse lacks real matching bank')
                bv=bank[actor][1]
            else:
                if e['b']%4:raise ValueError('row B feeder address is unaligned')
                if e['b']+8>a['words']:raise ValueError('row B wide read crosses SRAM boundary')
                bv=read(actor,e['b'],t['b'])
                if not masked and any(read(actor,e['b']+j)!=0 for j in range(1,8)):raise ValueError('row B guard changed')
                bank[actor]=(t['b'],bv)
            for j,word in enumerate(av):
                old['acc'][j]+=sum(s16(word,k)*s16(bv,k) for k in range(e['k']))*t['coefficient']*(1<<t['scale_shift'])
                if not -(1<<63)<=old['acc'][j]<1<<63:raise ValueError('row S64 accumulator overflow')
            old['term']=ti+1;pending[actor]=old;row_executes+=1
        elif kind=='ROW_M_FINAL':
            old=pending.get(actor);rr=e['row']
            if (a['kind']!='M' or old is None or old['members']!=e['native'] or e['rows']!=len(old['members']) or
                type(rr)!=int or not 0<=rr<e['rows'] or rr in old['final'] or e.get('wait_s_ack') is not True):
                raise ValueError('row final lacks context/unique ACK')
            node=nodes[old['members'][rr]]
            if (old['term']!=len(node['terms']) or (e['record'],e['width'],e['shift'])!=(node['output'],node['width'],node['shift'])):
                raise ValueError('row final differs from native scalar output')
            acc=old['acc'][rr];shift=node['shift'];q,rem=divmod(acc,1<<shift)
            value=q+int(shift>0 and (2*rem>1<<shift or 2*rem==1<<shift and q%2))
            value=max(-(1<<(node['width']-1)),min((1<<(node['width']-1))-1,value));word=value&0xffffffff
            write(actor,e['address'],word,node['output']);observed[node['output']]=word
            old['final'].add(rr);executed.add(node['id'])
            if len(old['final'])==e['rows']:pending.pop(actor)
        elif kind=='E':
            n=nodes.get(e['native'])
            if (a['kind']!='E' or n is None or n['kind']!='E' or n['id'] in executed or
                (e['input_records'],e['record'],e['opcode'],e['shift'])!=(n['inputs'],n['output'],n['opcode'],n['shift']) or
                len(e['inputs'])!=len(n['inputs']) or e.get('wait_s_ack') is not True):raise ValueError('row E command differs')
            args=[read(actor,addr,record) for addr,record in zip(e['inputs'],n['inputs'])];word=0
            for lane in range(8):
                values=[s16(value,lane) for value in args]
                if n['opcode']==5:value=min(values)
                elif n['opcode']==6:value=values[0] if values[2] else values[1]
                else:raise ValueError('unregistered row E opcode')
                word|=(value&65535)<<(16*lane)
            write(actor,e['address'],word,n['output']);observed[n['output']]=word;executed.add(n['id'])
        else:raise ValueError('unknown row program event')
    if pending or executed!=nodes.keys():raise ValueError('row native coverage incomplete')
    for c in graph['external_commits']:
        value=c['record'];at=c['external_address']
        if value not in external_tags.get(at,set()) or external[at]!=observed[value]:raise ValueError('row live-out not committed')
    if (loads,stores,loads+stores,copy_ticks,service_ticks,copy_ticks+service_ticks)!=(program['external_load_words'],
        program['external_store_words'],program['external_words'],program['copy_ticks'],program['native_service_ticks'],program['total_ticks']):
        raise ValueError('row program cost or transfer accounting differs')
    return {'passed':True,'observed_native_outputs':observed,'unique_native_operations':len(executed),
        'row_contexts':groups,'M_executes':row_executes,'external_words':loads+stores,'peak_address_words':peak,
        'scope':'independent finite SRAM, actual operand identity, per-row S64, bank/alignment/guard/ACK and cost replay; no RTL or system qualification'}
