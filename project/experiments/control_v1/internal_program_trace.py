"""Observe real C/queue/adapter completion handshakes in the fixed final-cell model."""
from pathlib import Path
import collections,json,re
from program_event_trace import sha,audit as external_audit


def instrument(bench,header,graph,out):
    header=Path(header);graph=Path(graph);out=Path(out)
    text=header.read_text();g=json.loads(graph.read_text());assert len(g['instances'])==345
    members={m.group(2):int(m.group(1))+1 for m in re.finditer(r'(?:CData|SData|IData|QData|VlWide<\d+>)/\*(\d+):0\*/\s+(control_system__DOT__\w+)\s*;',text)}
    pins={};bindings=[]
    for bit,c in g['connections'].items():
        for p in [c['driver'],*c['sinks']]:pins[(p['instance'],p['pin'])]=(bit,c)
    def expression(instance,port,width):
        words=[]
        for first in range(0,width,32):
            terms=[]
            for k in range(first,min(first+32,width)):
                pin=port if width==1 else port+'['+str(k)+']'
                bit,c=pins[(instance,pin)];chosen=None
                raw='control_system__DOT__net_'+bit
                if raw in members:chosen=(raw,0)
                for p in [c['driver'],*c['sinks']]:
                    name=p['pin'].split('[')[0];index=int(p['pin'].split('[')[1][:-1])if '['in p['pin']else 0
                    m='control_system__DOT____Vcell'+('out'if p['direction']=='output'else'inp')+'__'+p['instance']+'__'+name
                    if m in members:chosen=(m,index);break
                assert chosen is not None,(instance,pin,bit)
                m,index=chosen;assert index<members[m]
                value='v.rootp->'+m
                if members[m]>64:value+='['+str(index//32)+']';shift=index%32
                else:shift=index
                terms.append('((uint64_t('+value+')>>'+str(shift)+'&1ULL)<<'+str(k-first)+')')
                bindings.append(dict(instance=instance,pin=pin,graph_bit=bit,member=m,member_bit=index))
            words.append('uint32_t('+'|'.join(terms)+')')
        return words
    lines=[]
    def capture(event,instance,valid,ready,data,width,endpoint=None,last=None):
        valid=expression(instance,valid,1)[0];ready=expression(instance,ready,1)[0]
        words=expression(instance,data,width);fields='",\\\"endpoint\\\":"+std::to_string('+str(endpoint or 0)+')'
        if endpoint=='dynamic':fields='",\\\"endpoint\\\":"+std::to_string('+expression(instance,'task_endpoint',4)[0]+')'
        if last:fields+='+",\\\"last\\\":"+std::to_string('+expression(instance,last,1)[0]+')'
        fields+='+",\\\"words\\\":["'
        for i,w in enumerate(words):fields+=(' +","'if i else '')+'+std::to_string('+w+')'
        fields+=' +"]"'
        lines.append('if('+valid+'&&'+ready+')event_trace("'+event+'",'+fields+');')
    capture('C_WORD','controller','task_valid','task_ready','task_data',32,'dynamic','task_last')
    for n in range(8):
        q='queue_'+str(n)
        capture('Q_CMD',q,'cmd_valid','cmd_ready','cmd_data',32,n,'cmd_last')
        capture('Q_TASK',q,'task_valid','task_ready','task_data',256,n)
        capture('Q_COMPLETE',q,'complete_valid','complete_ready','complete_data',64,n)
        capture('Q_DONE',q,'done_valid','done_ready','done_data',32,n,'done_last')
    capture('C_DONE','controller','done_valid','done_ready','done_data',32,0,'done_last')
    changes=[('#include "Vcontrol_system.h"','\n#include "Vcontrol_system___024root.h"'),('  if(v.rvalid && v.rready){','\n'.join(lines)+'\n')]
    changed=bench
    # Capture at the settled low clock immediately before any rising edge.
    for anchor,extra in changes:
        assert changed.count(anchor)==1
        changed=changed.replace(anchor,extra+anchor if anchor.startswith('  if')else anchor+extra)
    recovered=changed
    for anchor,extra in reversed(changes):recovered=recovered.replace(extra+anchor if anchor.startswith('  if')else anchor+extra,anchor,1)
    assert recovered==bench
    binding=out/'internal-signal-bindings.json';binding.write_text(json.dumps(dict(graph=str(graph),graph_sha256=sha(graph),root_header=str(header),root_header_sha256=sha(header),bindings=bindings,observation='Actual root member on exactly the graph net, possibly another pin of that same physical net. No cross-net alias inference, RTL change, or host-plan substitution.'),indent=2))
    return changed,recovered,{str(header):sha(header),str(graph):sha(graph),str(binding):sha(binding),str(Path(__file__)):sha(__file__)}


def audit(path,cycles):
    path=Path(path);filtered=path.with_name(path.stem+'-external-only.jsonl')
    events={'C_WORD','Q_CMD','Q_TASK','Q_COMPLETE','Q_DONE','C_DONE'}
    command_words=[collections.deque()for _ in range(8)];packets=[collections.deque()for _ in range(8)]
    assembly=[[]for _ in range(8)];inflight=[collections.deque()for _ in range(8)];completions=[collections.deque()for _ in range(8)]
    returned=collections.deque();cassembly=[];descriptors={};order=[];submitted=0;counts=collections.Counter();programs=[];active=None
    with filtered.open('w')as ext:
        for line in path.open():
            r=json.loads(line);e=r['event']
            if e not in events:
                ext.write(line)
                if e=='program_begin':
                    assert active is None
                    active=(r['case'],r['run']);descriptors={};order=[];submitted=0;counts=collections.Counter()
                elif e=='descriptor':descriptors[r['index']]=r['words']
                elif e=='planned_order':order.append(r['descriptor'])
                elif e=='program_end':
                    assert active==(r['case'],r['run']) and not cassembly and not returned
                    assert all(not q for group in [command_words,packets,assembly,inflight,completions]for q in group)
                    if not r['fault']:assert submitted==len(order)
                    programs.append(dict(case=r['case'],run=r['run'],submitted_packets=submitted,counts=dict(counts),fault=r['fault']));active=None
                continue
            assert active==(r['case'],r['run']) and 0<=r['cycle']<=cycles
            n=r['endpoint'];w=r['words'];assert 0<=n<8 and all(0<=x<2**32 for x in w);counts[e]+=1
            if e=='C_WORD':
                assert len(w)==1 and r['last']==(len(cassembly)==7)
                if cassembly:assert n==cassembly[0][0]
                cassembly.append((n,w[0]));command_words[n].append((w[0],r['last']))
                if r['last']:
                    actual=[x[1]for x in cassembly];expected=descriptors[order[submitted]]
                    assert n==((expected[0]>>8)&15) and actual[0]&65535==expected[0]&65535 and actual[1:]==expected[1:]
                    submitted+=1;cassembly=[]
            elif e=='Q_CMD':
                assert len(w)==1 and command_words[n].popleft()==(w[0],r['last'])
                assert r['last']==(len(assembly[n])==7);assembly[n].append(w[0])
                if r['last']:packets[n].append(assembly[n]);assembly[n]=[]
            elif e=='Q_TASK':
                assert len(w)==8 and packets[n].popleft()==w
                inflight[n].append(w[0]>>16)
            elif e=='Q_COMPLETE':
                assert len(w)==2 and inflight[n].popleft()==w[0]&65535 and (w[0]>>16)&15==n
                completions[n].append(w)
            elif e=='Q_DONE':
                assert len(w)==1 and completions[n]
                expected=completions[n][0];half=counts['Q_DONE_'+str(n)]%2
                assert w[0]==expected[half] and r['last']==half
                counts['Q_DONE_'+str(n)]+=1;returned.append((w[0],r['last']))
                if half:completions[n].popleft()
            elif e=='C_DONE':assert len(w)==1 and returned.popleft()==(w[0],r['last'])
    assert active is None and len(programs)==18 and {p['case']for p in programs}==set(range(1,15))
    base=external_audit(filtered,cycles)
    base.update(internal_dispatch_captured=True,host_plan_compared_to_actual_dispatch=True,queue_packets_and_adapter_completions_independently_replayed=True,internal_programs=programs,filtered_external_trace_sha256=sha(filtered),scope='Actual C accepted words, eight queue command/assembled-task/completion/return handshakes and C accepted returns, sampled at settled pre-rising clock. No per-cycle waveform or upper physical qualification.')
    return base
