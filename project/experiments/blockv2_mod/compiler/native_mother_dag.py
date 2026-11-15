"""Encode dependency-correct CALL/WAIT actions, including live streamed scopes."""
from collections import defaultdict

def actions(calls,*,wait_policy='all'):
    if wait_policy not in ('all','predicted_first'):raise ValueError('unknown WAIT policy')
    count=len(calls);after=[set(c['after']) for c in calls]
    starts=[set(c.get('requires_started',[])) for c in calls]
    done_edges=[set(c.get('completion_after',[])) for c in calls]
    done_users=defaultdict(list);start_users=defaultdict(list)
    for i,c in enumerate(calls):
        if c['index']!=i or i in after[i]|starts[i]|done_edges[i]:raise ValueError('invalid call graph')
        for p in after[i]:
            if not 0<=p<count:raise ValueError('unknown completion predecessor')
            done_users[p].append(i)
        for p in starts[i]:
            if not 0<=p<count:raise ValueError('unknown start predecessor')
            start_users[p].append(i)
        if any(not 0<=p<count for p in done_edges[i]):raise ValueError('unknown stream completion')
    ready={i for i in range(count) if not after[i] and not starts[i]}
    issued=set();completed=set();live={};result=[];quiescent=[]
    while len(completed)<count:
        eligible=sorted(i for i in ready if calls[i]['target'] not in live)
        if eligible:
            for i in eligible:
                target=calls[i]['target']
                if target in live:continue
                ready.remove(i);issued.add(i);live[target]=i
                result.append({'op':'CALL','target':target,'call_index':i})
                for child in start_users[i]:
                    starts[child].remove(i)
                    if not starts[child] and not after[child] and child not in issued:ready.add(child)
            continue
        live_ids=set(live.values())
        def finishable(i,stack=frozenset()):
            if i in completed:return True
            if i not in live_ids or i in stack:return False
            return all(finishable(p,stack|{i}) for p in done_edges[i])
        retiring=[i for i in live.values() if finishable(i)]
        if not retiring:raise ValueError('native completion deadlock; unissued supply or cyclic start/wait')
        if wait_policy=='predicted_first':
            if any('finish_proxy' not in calls[i] for i in retiring):raise ValueError('missing completion estimate')
            retiring=[min(retiring,key=lambda i:(calls[i]['finish_proxy'],i))]
        mask=sum(1<<calls[i]['target'] for i in retiring)
        result.append({'op':'WAIT','mask':mask,'calls':sorted(retiring)})
        for i in retiring:
            completed.add(i);del live[calls[i]['target']]
            for child in done_users[i]:
                after[child].remove(i)
                if not after[child] and not starts[child] and child not in issued:ready.add(child)
        if not live:quiescent.append(len(result))
    return result,quiescent

def verify_actions(calls,program):
    """Independent execution of the explicit two-event contract."""
    issued=set();completed=set();live={}
    def settle(i,visiting):
        if i in completed:return
        if i not in live.values() or i in visiting:raise ValueError('WAIT would require an unissued/cyclic completion')
        for p in calls[i].get('completion_after',[]):settle(p,visiting|{i})
        completed.add(i)
    for action in program:
        if action['op']=='CALL':
            i=action['call_index'];c=calls[i];target=action['target']
            if i in issued or target in live or target!=c['target']:raise ValueError('native CALL identity/occupancy')
            if not set(c['after'])<=completed or not set(c.get('requires_started',[]))<=issued:
                raise ValueError('native CALL precedes its dependency')
            issued.add(i);live[target]=i
        elif action['op']=='WAIT':
            targets=[t for t in live if action['mask']&(1<<t)]
            if sum(1<<t for t in targets)!=action['mask']:raise ValueError('WAIT names idle target')
            if sorted(live[t] for t in targets)!=action['calls']:raise ValueError('WAIT call correspondence')
            for t in targets:settle(live[t],set())
            for t in targets:del live[t]
        else:raise ValueError('unknown native control action')
    if issued!=set(range(len(calls))) or completed!=issued or live:raise ValueError('incomplete native control program')
    return {'passed':True,'calls':len(calls),'actions':len(program),'scope':'independent start/completion ordering check, not RTL arithmetic execution'}
