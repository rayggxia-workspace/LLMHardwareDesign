"""Read real resident-service measurements, then account generated events.

These are serial P/E/S service slots plus an explicit virtual-memory model.
They are not LC/DMA/system calibration or measured DRAM latency/energy.
"""
import json
from pathlib import Path


def read_qualification(directory,logs):
    from resident_probe import analyse
    directory=Path(directory)
    if len(logs)!=3 or len({Path(p).resolve() for p in logs})!=3:
        raise ValueError('three distinct initialization logs required')
    reports=[analyse(directory,Path(log),write_summary=False) for log in logs]
    profiles=[]
    for report in reports:
        rows=report.get('passive_profiles',[])
        if not rows:raise ValueError('resident protocol-only evidence has no timing profiles')
        if any(p['min']!=p['max'] for p in rows):raise ValueError('nonconstant resident service profile')
        profile={b:{} for b in ('P','E','feeder')}
        for row in rows:
            if str(row['key']) in profile[row['boundary']]:raise ValueError('duplicate resident service profile')
            # Inclusive service slots follow the existing native tile profile
            # convention. Response holding and observer accesses are outside.
            profile[row['boundary']][str(row['key'])]=row['max']+1
        profiles.append(profile)
    if any(p!=profiles[0] for p in profiles[1:]):raise ValueError('resident profiles differ across SRAM states')
    manifest=json.loads((directory/'manifest.json').read_text())
    return {'kind':'native-resident-services-v1','profile':profiles[0],
        'rtl_sha256':{k:v for k,v in manifest['sha256'].items() if k.startswith('rtl/')},
        'proof':{'manifest_sha256':reports[0]['manifest_sha256'],
                 'log_sha256':[r['log_sha256'] for r in reports],
                 'cases_per_initialization':[r['cases'] for r in reports]},
        'scope':'serial native P/M/feeder/E/S acceptance-to-first-completion slots; no LC/DMA/system/physical/energy qualification'}


def validate(timing):
    if timing.get('kind')!='native-resident-services-v1' or not timing.get('proof') or not timing.get('rtl_sha256'):
        raise ValueError('qualified native resident timing required')
    if set(timing.get('profile',{}))!={'P','E','feeder'}:raise ValueError('resident timing boundaries differ')
    for table in timing['profile'].values():
        if not table or any(type(v)!=int or v<1 for v in table.values()):raise ValueError('positive measured resident slots required')


def event_ticks(event,timing):
    if timing is None:return 0
    p=timing['profile'];op=event['op']
    try:
        if op=='M_TERM':return p['P']['0']+p['P'][str(1+event['k'])]+p['feeder'][str(int(event['reuse_b']))]
        if op=='M_FINAL':return p['P'][str(16+64*(1 if event['width']==16 else 2)+event['shift'])]
        if op=='E':return p['E'][str(event['opcode']+16*len(event['inputs'])+64*event['shift'])]
        if op in ('LOAD','LOAD_ZERO','STORE','TRANSFER'):return 0
        raise ValueError('unknown resident timing event')
    except KeyError as exc:raise ValueError('unmeasured native resident command') from exc


def audit(plan,timing):
    """Recount all emitted service/copy events, independent of planner state."""
    validate(timing)
    if plan.get('service_timing')!=timing:raise ValueError('resident plan timing provenance differs')
    from resident_transports import catalog,event_contract
    paths=catalog(plan.get('transports',()),plan['actors'])
    copies=services=0;loads=stores=0;transfers=transfer_ticks=0
    nets=set((plan.get('initial_continuation') or {}).get('transport_nets',()))
    for event in plan['events']:
        actor=plan['actors'][event['actor']];kind=event['op']
        if kind in ('LOAD','LOAD_ZERO'):copies+=actor['load_ticks'];loads+=1
        elif kind=='STORE':copies+=actor['store_ticks'];stores+=1
        elif kind=='TRANSFER':
            p=event_contract(event,paths,plan['actors']);copies+=p['ticks'];transfers+=1;transfer_ticks+=p['ticks'];nets.update(p['nets'])
        else:services+=event_ticks(event,timing)
    if (copies,services,copies+services,loads,stores)!=(plan['copy_ticks'],plan['native_service_ticks'],
            plan['total_ticks'],plan['external_load_words'],plan['external_store_words']):
        raise ValueError('resident service/copy accounting differs')
    if paths and ((transfers,transfer_ticks,sorted(nets))!=(plan['transport_words'],plan['transport_ticks'],plan['transport_nets']) or
                  not nets<={n for p in paths.values() for n in p['nets']} or
                  plan.get('transport_net_budget') is not None and len(nets)>plan['transport_net_budget']):
        raise ValueError('resident transport/static net accounting differs')
    return {'passed':True,'copy_ticks':copies,'native_service_ticks':services,'total_ticks':copies+services,
            'scope':'serialized event/profile accounting; finite-S numeric and full graph proof are separate'}
