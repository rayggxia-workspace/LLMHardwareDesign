"""Independent loop schedule check; does not import the DP/search code."""
from collections import defaultdict
from copy import deepcopy


def _resize_columns(child,interval):
    """Independent affine/native-traffic reconstruction, not planner import."""
    lo,hi=interval;old_width=child['columns'][1]-child['columns'][0];width=hi-lo
    b=deepcopy(child['binding']);c=b.get('read_cache')
    saved=(c['baseline_partial_external_reads']-c['cold_partial_external_reads']) if c else 0
    ticks=b['ticks']+(saved*c['load_ticks'] if c else 0);reads=b['external_read_words']+saved
    if any(x%old_width for x in (ticks,reads,b['external_write_words'])):
        raise ValueError('nonuniform compound native work')
    b['ticks']=ticks//old_width*width;b['external_read_words']=reads//old_width*width
    b['external_write_words']=b['external_write_words']//old_width*width
    if c:
        ca,cb=c['components'];r=c['rows'];k=c['K'];t=c['stripe']
        baseline=r*width*k*ca*cb*3
        cold=r*t*ca+r*width*(k-t)*ca*cb+r*width*k*cb+1
        b['ticks']-=(baseline-cold)*c['load_ticks'];b['external_read_words']-=baseline-cold
        b['warm_ticks']=b['ticks']-r*t*ca*c['load_ticks'];b['warm_read_words']=b['external_read_words']-r*t*ca
        c.update(columns=width,baseline_partial_external_reads=baseline,
                 cold_partial_external_reads=cold,warm_partial_external_reads=cold-r*t*ca)
    b['id']+=';frontier-width='+str(width)
    return {'columns':[lo,hi],'binding':b}


def _expand_compounds(tasks,plan):
    """Independent reconstruction; do not trust the planner's flattened view."""
    by_id={t['id']:t for t in tasks};owners={};expanded=[];rows=[]
    peak_so_far=0
    for row in plan['tasks']:
        if row['id'] not in by_id or row['id'] in owners:raise ValueError('compound task coverage differs')
        task=by_id[row['id']]
        matches=[b for b in task['bindings'] if b['id']==row['binding']]
        if len(matches)!=1:raise ValueError('unknown/ambiguous loop binding')
        b=matches[0];parents=task.get('after',[])
        if any(p not in owners for p in parents):raise ValueError('compound decision precedes dependency')
        deps=[s for p in parents for s in owners[p]]
        if 'parallel_shards' not in b:
            if row.get('evaluation',{}).get('cost_model')=='dot-column-shards-v1':
                raise ValueError('unexpected compound schedule')
            owners[row['id']]=[row['id']]
            expanded.append({**task,'after':deps,'bindings':[b]});rows.append(row)
        else:
            spec=b['parallel_shards'];e=row.get('evaluation',{});services=e.get('services',[])
            if spec.get('kind')!='dot-columns-v1' or len(spec['children'])<2 or len(services)!=len(spec['children']):
                raise ValueError('compound service coverage differs')
            fields={'cost_model','services','delta_makespan'}
            children=spec['children']
            if 'frontier_partition' in b:
                fields.add('resolved_columns');intervals=e.get('resolved_columns',[])
                if len(intervals)!=len(children):raise ValueError('frontier column coverage differs')
                edge=0
                for interval in intervals:
                    if (not isinstance(interval,list) or len(interval)!=2 or
                        any(type(x)!=int for x in interval) or not edge==interval[0]<interval[1]<=spec['columns']):
                        raise ValueError('frontier column gap/overlap/range')
                    edge=interval[1]
                if edge!=spec['columns']:raise ValueError('frontier column partition incomplete')
                children=[_resize_columns(c,r) for c,r in zip(children,intervals)]
            if set(e)!=fields or e['cost_model']!='dot-column-shards-v1':
                raise ValueError('compound evaluation differs')
            if (row['site']!=b['site'] or row['start']!=min(s['start'] for s in services) or
                row['end']!=max(s['end'] for s in services) or
                e['delta_makespan']!=max(peak_so_far,row['end'])-peak_so_far):
                raise ValueError('compound time/site differs')
            owners[row['id']]=[]
            for i,(child,s) in enumerate(zip(children,services)):
                leaf=child['binding'];name=spec['primitive']+'#columns-'+str(i)
                if s['id']!=name or s['binding']!=leaf['id'] or 'parallel_shards' in leaf:
                    raise ValueError('compound child identity differs')
                owners[row['id']].append(name)
                expanded.append({'id':name,'after':deps,'bindings':[leaf]});rows.append(s)
            leaves=[c['binding'] for c in spec['children']]
            for field in ('resources','nets'):
                if set(b[field])!=set().union(*(set(c[field]) for c in leaves)):
                    raise ValueError('compound '+field+' union differs')
        peak_so_far=max(peak_so_far,row['end'])
    if len(owners)!=len(tasks) or len({t['id'] for t in expanded})!=len(expanded):
        raise ValueError('compound task identity/coverage differs')
    return expanded,{**plan,'tasks':rows}


def verify(tasks,hardware,plan,wire_budget=None,*,_window_checked=False):
    def check(ok,message):
        if not ok:raise ValueError(message)
    check(plan.get('status')=='planned','loop plan is not successful')
    calendar=set(hardware.get('window_calendar',{}).get('resources',[]))
    window_audit=None
    if calendar and not _window_checked:
        from verify_window_schedule import audit
        window_audit=audit(tasks,hardware,plan)
    selected={(r['id'],r['binding']) for r in plan['tasks']}
    if (any(r.get('evaluation',{}).get('cost_model') == 'dot-phased-column-shards-v1' for r in plan['tasks']) or
        any('phase_execution' in b and (t['id'],b['id']) in selected for t in tasks for b in t['bindings'])):
        from verify_phased_compounds import project
        projected_tasks,projected_plan,audit = project(tasks,hardware,plan)
        result = verify(projected_tasks,hardware,projected_plan,wire_budget=wire_budget,_window_checked=True)
        return {**result,'cooperative_phase_audit':audit,'window_audit':window_audit}
    if any('parallel_shards' in b for t in tasks for b in t['bindings']):
        tasks,plan=_expand_compounds(tasks,plan)
    # Deliberately independent from search's conflict filter. A foreign or
    # corrupted plan must fail even if its conflicting users never overlap.
    incompatible=[]
    for pair in hardware.get('incompatible_nets',[]):
        check(isinstance(pair,(list,tuple)) and len(pair)==2,'invalid incompatible_nets pair')
        check(all(isinstance(n,str) and n in hardware['nets'] for n in pair) and pair[0]!=pair[1],
              'invalid incompatible_nets endpoints')
        incompatible.append(tuple(pair))
    rows={r['id']:r for r in plan['tasks']}
    check(len(rows)==len(plan['tasks'])==len(tasks),'loop task coverage differs')
    claims=defaultdict(list);storage=defaultdict(list);nets=set();traffic=0
    # Independently reconstruct persistent read-only S leases in the emitted
    # decision order. A site's serialized IO makes this its physical order.
    cache={};cache_flags={};residency=[];evaluated={};prefix_makespan=0
    task_by_id={t['id']:t for t in tasks}
    for row in plan['tasks']:
        check(row['id'] in task_by_id,'unknown loop task')
        matches=[b for b in task_by_id[row['id']]['bindings'] if b['id']==row['binding']]
        check(len(matches)==1,'unknown/ambiguous loop binding');b=matches[0];c=b.get('read_cache')
        if b.get('resident_region'):
            spec=b['resident_region'];scratch=b.get('scratch_by_site',{b['site']:b['scratch_words']})
            check(not c and not b.get('dot_tile') and spec.get('kind')=='serial-native-resident-loop-v1' and
                set(spec.get('invalidate_read_cache',()))==set(scratch),'invalid resident cache effects')
            discarded=[]
            for site in sorted(scratch):
                old=cache.pop(site,None)
                if old:
                    check(old['end']<=row['start'],'resident loop overwrites cache before old ACK')
                    if row['start']>old['end']:residency.append((site,old['end'],row['start'],old['words']+1))
                    discarded.append({'site':site,'tag':old['tag'],'prefix':old['stripe'],'words':old['words']})
            expected={'cost_model':'serial-native-resident-loop-v1','retention':'invalidate',
                'discarded_read_cache':discarded,'external_read_words':b['external_read_words'],
                'external_write_words':b['external_write_words'],'scratch_by_site':scratch,
                'duration':b['ticks'],'delta_makespan':max(prefix_makespan,row['end'])-prefix_makespan}
            if b.get('resident_overlap'):
                overlap=b['resident_overlap']
                check(overlap.get('kind')=='commuting-native-actors-v1' and
                    overlap.get('reservation')=='all-union-resources-through-final-ACK','invalid resident overlap reservation')
                expected.update(cost_model='commuting-native-resident-loop-v1',overlap_proof=overlap['proof'],
                                reservation=overlap['reservation'])
            check(row.get('evaluation')==expected,'resident loop state evaluation differs')
            evaluated[row['id']]=(b['ticks'],b['external_read_words'],scratch)
        if b.get('dot_tile'):
            spec=b['dot_tile']
            check(not c and spec.get('kind')=='prepared-s32-static-b-tile-v1' and
                  spec.get('invalidate_read_cache')==[b['site']], 'invalid tile cache effects')
            discarded=[]
            for site in spec['invalidate_read_cache']:
                old=cache.pop(site,None)
                if old:
                    check(old['end']<=row['start'],'tile overwrites cache before old ACK')
                    if row['start']>old['end']:residency.append((site,old['end'],row['start'],old['words']+1))
                    discarded.append({'site':site,'tag':old['tag'],'prefix':old['stripe'],'words':old['words']})
            scratch=b.get('scratch_by_site',{b['site']:b['scratch_words']})
            expected={'cost_model':'native-p-e-tile-stream-v1','retention':'invalidate',
                'discarded_read_cache':discarded,'external_read_words':b['external_read_words'],
                'external_write_words':b['external_write_words'],'scratch_by_site':scratch,
                'duration':b['ticks'],'delta_makespan':max(prefix_makespan,row['end'])-prefix_makespan}
            check(row.get('evaluation')==expected,'tile state evaluation differs')
            evaluated[row['id']]=(b['ticks'],b['external_read_words'],scratch)
        for site,n in b.get('scratch_by_site',{b['site']:b['scratch_words']}).items():
            if site in cache and (not c or site!=c['site']):
                check(n<=8,'active scratch overlaps retained S cache addresses')
        hit=False
        if c:
            old=cache.get(c['site'])
            if old:
                check(old['end']<=row['start'],'cache use/overwrite before prior owner finished')
                if row['start']>old['end']:residency.append((c['site'],old['end'],row['start'],old['words']+1))
            hit=bool(c['stripe'] and old and old['tag']==c['tag'] and old['stripe']>=c['stripe'])
            check(row.get('cache_hit') is hit,'cache hit claim differs')
            if c.get('cost_model')=='dot-prefix-state-v2':
                e=row.get('evaluation',{});policy=e.get('retention')
                check(policy in ('preserve','shrink','discard'),'invalid retention policy')
                q=old['stripe'] if old and old['tag']==c['tag'] else 0
                reused=min(q,c['stripe']);saved=reused*c['rows']*c['components'][0]
                duration=b['ticks']-saved*c['load_ticks'];reads=b['external_read_words']-saved
                if policy=='discard':cache.pop(c['site'],None)
                elif c['stripe']:
                    retained=max(q,c['stripe']) if policy=='preserve' else c['stripe']
                    cache[c['site']]={'tag':c['tag'],'stripe':retained,
                        'words':retained*c['rows']*c['components'][0],'end':row['end']}
                elif old:cache[c['site']]={**old,'end':row['end']}
                current=cache.get(c['site']);words=current['words'] if current else 0
                scratch=dict(b.get('scratch_by_site',{b['site']:b['scratch_words']}))
                scratch[c['site']]=max(scratch[c['site']],9+words)
                expected={'cost_model':c['cost_model'],'retention':policy,'reused_prefix':reused,
                    'loaded_prefix':c['stripe']-reused,'retained_prefix':current['stripe'] if current else 0,
                    'external_read_words':reads,'external_write_words':b['external_write_words'],
                    'scratch_by_site':scratch,'duration':duration,
                    'delta_makespan':max(prefix_makespan,row['end'])-prefix_makespan}
                check(e==expected,'state evaluation differs')
                evaluated[row['id']]=(duration,reads,scratch)
            else:
                if c['stripe']:cache[c['site']]={'tag':c['tag'],'stripe':c['stripe'],'words':c['cache_words'],'end':row['end']}
                else:cache.pop(c['site'],None)
        prefix_makespan=max(prefix_makespan,row['end'])
        cache_flags[row['id']]=hit
    for site,old in cache.items():
        if plan['makespan']>old['end']:residency.append((site,old['end'],plan['makespan'],old['words']+1))
    for site,start,end,words in residency:storage[site].append((start,end,words))
    for t in tasks:
        check(t['id'] in rows,'missing loop task')
        row=rows[t['id']];matches=[b for b in t['bindings'] if b['id']==row['binding']]
        check(len(matches)==1,'unknown/ambiguous loop binding');b=matches[0]
        hit=cache_flags[t['id']]
        duration,reads,scratch=evaluated.get(t['id'],((b['warm_ticks'] if hit else b['ticks']),(b['warm_read_words'] if hit else b['external_read_words']),b.get('scratch_by_site',{b['site']:b['scratch_words']})))
        check(row['site']==b['site'] and row['start']>=0 and row['end']-row['start']==duration,'loop time/site mismatch')
        check(all(rows[p]['end']<=row['start'] for p in t.get('after',[])),'loop read before producer commit')
        for r in b['resources']:
            if r not in calendar:claims[r].append((row['start'],row['end'],1))
        for site,n in scratch.items():
            offset=None
            if 'materialized_tile' in b:
                meta=next(m for m in hardware['leaf_inventory'].values() if m['site']==site)
                offset=b['materialized_tile']['resource_offsets'].get(meta['io_resource'])
            start,end=(row['start']+offset[0],row['start']+offset[1]) if offset else (row['start'],row['end'])
            storage[site].append((start,end,n))
        check(all(n in hardware['nets'] for n in b['nets']),'unknown static connection demand')
        nets.update(b['nets']);traffic+=reads+b['external_write_words']
    def peak(intervals):
        events=[(a,n) for a,b,n in intervals]+[(b,-n) for a,b,n in intervals]
        live=high=0
        for _,delta in sorted(events):live+=delta;check(live>=0,'negative resource occupancy');high=max(high,live)
        check(live==0,'resource not released');return high
    for r,intervals in claims.items():check(peak(intervals)<=hardware['resources'][r],'loop resource contention '+r)
    peaks={site:peak(intervals) for site,intervals in storage.items()}
    for site,n in peaks.items():check(n<=hardware['sites'][site]['words'],'private S overflow '+site)
    physical=nets|{n for n,meta in hardware['nets'].items() if meta.get('fixed')}
    for left,right in incompatible:
        check(not (left in physical and right in physical),
              'incompatible static connection demands: '+left+' / '+right)
    cost=sum(hardware['nets'][n]['cost'] for n in nets if not hardware['nets'][n].get('fixed'))
    check(sorted(nets)==plan['nets'] and cost==plan['wire_cost'],'static union differs')
    check(wire_budget is None or cost<=wire_budget,'static connection budget exceeded')
    check(traffic==plan['external_words'],'external transfer count differs')
    if 'read_cache_hits' in plan:check(sum(cache_flags.values())==plan['read_cache_hits'],'read cache hit total differs')
    check(max((r['end'] for r in rows.values()),default=0)==plan['makespan'],'loop makespan differs')
    return {'passed':True,'peak_words':peaks,'external_words':traffic,'static_nets':len(nets),
            'window_audit':window_audit,
            'checked_static_conflict_pairs':len(incompatible),
            'scope':'independent streaming-loop schedule/resource check; kernel program proof is separate'}
