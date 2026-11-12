"""Independent coverage/dependency projection, followed by schedule audit.

Does not import the cover planner. Native recipe/loop validity is checked by
its own registrar; this checker verifies no original task is lost or repeated.
"""
from verify_loop_dp import verify as verify_schedule
from event_execution import phase_edges


def project(tasks,covers,plan):
    covers=tuple(covers)
    by={t['id']:t for t in tasks};actions={t['id']:{'id':t['id'],'covers':[t['id']],
        'bindings':t['bindings']} for t in tasks}
    if len(by)!=len(tasks):raise ValueError('duplicate original task')
    for a in covers:
        if a['id'] in actions:raise ValueError('duplicate registered cover')
        actions[a['id']]=a
    phase_dependencies={name:phase_edges(task) for name,task in by.items()}
    endpoints={name for name,edges in phase_dependencies.items() if edges}
    endpoints.update(edge.task for edges in phase_dependencies.values() for edge in edges)
    if any(len(a['covers'])>1 and endpoints.intersection(a['covers']) for a in covers):
        raise ValueError('multi-task cover has no mapping for its phase edge endpoints')
    owners={};output=[];rows=[]
    for row in plan['tasks']:
        a=actions.get(row['id'])
        if a is None:raise ValueError('unregistered cover decision')
        group=a['covers'];members=set(group)
        if (row.get('covers')!=group or not group or len(group)!=len(members) or
            not members<=by.keys() or members&owners.keys()):raise ValueError('cover membership/overlap differs')
        # Outside producers must have been committed by earlier decisions.
        # This also rejects covers with a hidden outside path back inside.
        dependencies=set().union(*(set(by[n].get('after',())) for n in group))-members
        phase_waits=phase_dependencies[group[0]] if len(group)==1 else ()
        if not (dependencies|{edge.task for edge in phase_waits})<=owners.keys():
            raise ValueError('cover before external dependency')
        bindings=[b for b in a['bindings'] if b['id']==row['binding']]
        if len(bindings)!=1:raise ValueError('unknown/ambiguous cover service')
        after=sorted({owners[n] for n in dependencies})
        projected={'id':a['id'],'after':after,'bindings':bindings}
        if phase_waits:
            projected['event_after']=[{'task':owners[edge.task],'from':edge.source,'to':edge.target}
                                      for edge in phase_waits]
        output.append(projected);rows.append(row)
        owners.update(dict.fromkeys(group,a['id']))
    if owners.keys()!=by.keys():raise ValueError('incomplete original task coverage')
    if len({t['id'] for t in output})!=len(output):raise ValueError('repeated cover action')
    return output,{**plan,'tasks':rows}


def verify(tasks,hardware,covers,plan,wire_budget=None):
    expected='event-cover-frontier-v1' if 'event_model' in hardware else 'convex-cover-frontier-v1'
    if plan.get('kind')!=expected:raise ValueError('unknown cover frontier plan')
    projected,ordinary=project(tasks,covers,plan)
    if expected!='event-cover-frontier-v1' and any(t.get('event_after') for t in projected):
        raise ValueError('phase edges require event replay')
    if expected=='event-cover-frontier-v1':
        from verify_event_execution import verify as verify_events
        result=verify_events(projected,hardware,ordinary,wire_budget=wire_budget)
    else:
        result=verify_schedule(projected,hardware,ordinary,wire_budget=wire_budget)
    if plan.get('covered_original_tasks')!=len(tasks):raise ValueError('original task count differs')
    return {**result,'covered_original_tasks':len(tasks),'decisions':len(projected),
            'scope':'independent original task coverage, committed dependencies and schedule; native recipe proof separate'}
