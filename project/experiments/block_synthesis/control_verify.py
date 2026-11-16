"""Independent MC/LC replay audit: integer graph, actual write/ACK/release trace."""
import re


def verify_replay(compiled,seeds,directory):
    model=compiled['model'];values={k:list(v) for k,v in seeds.items()}
    for node in model['tasks']:
        a,b=[values[n] for n in node['inputs']]
        if node['op']=='Add':raw=[x+y for x,y in zip(a,b)]
        elif node['op']=='Mul':raw=[x*y for x,y in zip(a,b)]
        else:raise ValueError('unregistered independent control reference')
        values[node['outputs'][0]]=[min(32767,max(-32768,x)) for x in raw]
    word=lambda xs:sum((int(x)&65535)<<(16*i) for i,x in enumerate(xs))
    def transfers(text,kind):
        return [dict(src=int(a),dst=int(b),addr=int(c),data=int(d,16),cycle=int(e)) for a,b,c,d,e in
            re.findall(kind+r' src=(\d+) dst=(\d+) addr=(\d+) data=([0-9a-f]+) cycle=(\d+)',text)]
    cases=[]
    for scenario in ('normal','stalled','reset'):
        for initial in ('1-143','2-143','2-144'):
            name=scenario+'-'+initial;text=(directory/(name+'.log')).read_text()
            if text.count('GENERATED_CONTROL_PASS')!=1:raise ValueError('control replay did not pass '+name)
            epochs=text.split('EPOCH_BEGIN')
            if scenario=='reset':
                if len(epochs)!=3 or not transfers(epochs[1],'WRITE') or transfers(epochs[1],'COMMIT') or 'RELEASE block=' in epochs[1]:
                    raise ValueError('reset case did not hold an actual unacknowledged write')
            text=epochs[-1];writes=transfers(text,'WRITE');commits=transfers(text,'COMMIT')
            releases=[(int(a),int(b)) for a,b in re.findall(r'RELEASE block=(\d+) cycle=(\d+)',text)]
            if not len(writes)==len(commits)==len(releases)==len(compiled['moves']):
                raise ValueError('write/ACK/release coverage differs '+name)
            for move,request,ack,release in zip(compiled['moves'],writes,commits,releases):
                src=compiled['hardware']['control_groups'][move['src']]['block_id']
                dst=compiled['hardware']['control_groups'][move['dst']]['block_id']
                expected={'src':src,'dst':dst,'addr':move['destination_address'],'data':word(values[move['value']])}
                if any(ack[k]!=v or request[k]!=v for k,v in expected.items()):
                    raise ValueError('generated graph numeric/address trace differs '+name)
                if request['cycle']>=ack['cycle'] or release!=(src,ack['cycle']):
                    raise ValueError('source released before real storage acknowledgment '+name)
            for kind in ('MC','LC block=0','LC block=1'):
                fetches=re.findall(r'FETCH kind='+kind+r' addr=(\d+)',text)
                if not any(int(a)>=128 for a in fetches):raise ValueError('no real program fetch for '+kind)
            result=re.search(r'GENERATED_CONTROL_PASS cycles=(\d+) commits=(\d+) confirmed_bytes=(\d+) pm_requests=(\d+)',text)
            if not result:raise ValueError('missing retirement summary '+name)
            start=re.search(r'START cycle=(\d+)',text)
            if not start:raise ValueError('missing actual mother start acceptance')
            total,stores,confirmed,fetches=map(int,result.groups())
            if confirmed!=16*(len(model['tasks'])+len(compiled['moves'])):
                raise ValueError('confirmed write accounting differs')
            cases.append({'name':name,'run_cycles':total-int(start.group(1)),'commits':stores,
                'confirmed_write_bytes':confirmed,'mother_reads_during_run':fetches,
                'source_hold_cycles':text.count('HOLD block='),'passed':True})
    expected={m['net'] for m in compiled['moves']}
    if expected!={n['id'] for n in compiled['connections']} or not expected<=set(compiled['plan']['nets']):
        raise ValueError('program and connection demands differ')
    fixed={n for n in compiled['plan']['nets'] if compiled['hardware']['nets'][n].get('fixed')}
    if fixed!=set(compiled['preconnected_demands']):raise ValueError('preconnected demand coverage differs')
    return {'status':'generated_mc_lc_replay_passed','cases':cases,
        'scope':'two constrained U_64 targets, Add/Mul native S16 graph, real SRAM and MC/LC PM fetch',
        'system_physical_qualified':False,'whole_llm_control_image_qualified':False}
