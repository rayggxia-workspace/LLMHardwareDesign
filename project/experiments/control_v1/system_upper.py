"""Route every extracted control_system boundary net on research M11/M12.

Route candidates are separate from actual GDS/ODB readback and full RC/STA.
No candidate alone grants physical-composition acceptance.
"""
import argparse,hashlib,json,math,os,time,random
from pathlib import Path
from tree_router import route
ROOT=Path(__file__).resolve().parents[3]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def priority_outputs(graph):
    from r256_scene import is_r256,SCHEMA
    sources={'macro_1','macro_2','macro_3','macro_4','macro_s','macro_t'}
    internal=bool(graph.get('S_internal_drive'))
    if internal:sources.remove('macro_s')
    r256=is_r256(graph['instances'])
    if r256:
        assert graph.get('scene')==SCHEMA and internal
        sources.add('macro_r')
    names=['net_'+bit for bit,c in graph['connections'].items()if c['driver']['instance']in sources]
    assert len(names)==(1229 if r256 else 583 if internal else 1370)
    return names


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--graph',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--seed',type=int,default=0)
    p.add_argument('--plan-only',action='store_true')
    p.add_argument('--cap-lower-bound-only',action='store_true',
                   help='Failure-only actual-output-driver/shortest-wire capacitance diagnostic; no route or acceptance')
    p.add_argument('--pair-wire-feasibility-report',type=Path,
                   help='Failure-only joint all-rotation pair constraints, from an actual-driver report')
    p.add_argument('--router',choices=['python','cpp','openroad'],default='cpp')
    p.add_argument('--pg-wrappers',type=Path)
    p.add_argument('--pg-candidate-access',action='store_true')
    p.add_argument('--route-trials',type=int,choices=[1,4,8,16],default=1)
    p.add_argument('--route-heuristic-weight',type=int,choices=[1,4,8,16,32,64,128,256],default=1,
                   help='Search ordering only; complete independent edge/flood/short/geometry/RC acceptance is unchanged')
    p.add_argument('--route-congestion-scale',type=int,choices=[0,1,4,8,16,32],default=0,
                   help='Search cost only; zero preserves prior coupling to heuristic weight, all physical gates unchanged')
    p.add_argument('--route-ordinary-congestion-scale',type=int,choices=[0,16,64,256],default=0,help='Search only: separate ordinary-net congestion cost from unchanged scale1 finite weak-output search')
    p.add_argument('--route-ordinary-search-margin',type=int,choices=[0,4,16,64,256],default=0,help='Search only: ordinary-net tree/target window widens every4 rounds and restores full grid at64; zero preserves full search')
    p.add_argument('--route-ordinary-zero-pattern',action='store_true',help='Optional bounded zero-occupancy ordinary prepass; otherwise original bidirectional/ordinary search, never a physical gate')
    p.add_argument('--route-nonpreferred-cost',type=int,choices=[2,8,32],default=2,help='Search cost only: penalize vertical M11 and horizontal M12 edges; no geometry, RC or acceptance rule changes')
    p.add_argument('--directional-regression-only',action='store_true')
    p.add_argument('--pattern-weight-regression-only',action='store_true')
    p.add_argument('--pattern-scale-regression-only',action='store_true')
    p.add_argument('--program-event-trace-config',type=Path,help='Observe actual current final-cell programs using immutable compiled model assets; zero-delay event evidence only')
    p.add_argument('--search-phase-profile-config',type=Path,help='Bounded software phase diagnosis only; no route or physical qualification')
    p.add_argument('--route-critical-first',action='store_true',help='Search only: preserve constrained native-output priority partition in every negotiated round, not only initialization')
    p.add_argument('--route-resource-labels',type=int,choices=[4000000,8000000],default=4000000,help='Search memory only: optional8million labels; final physical/electrical/timing gates unchanged')
    p.add_argument('--route-trial-attempts',type=int,default=0,help='Search only: finite attempt budget with failed-attempt refill within unchanged active trial width; zero preserves legacy pool')
    p.add_argument('--route-adaptive-heuristic',action='store_true',help='Search speed only: high weight above conflict threshold, original full-cost probes and late annealing; all actual acceptance gates unchanged')
    p.add_argument('--route-regression-only',action='store_true')
    p.add_argument('--route-initial-order',type=int,choices=[0,1,2,3],default=0,
                   help='Search only: seeded ties with shortest-span, longest-span or highest-fanout first; physical gates unchanged')
    p.add_argument('--bidirectional-two-terminal',action='store_true',
                   help='Search only: balanced-potential bidirectional search for unconstrained two-terminal nets; all finite budgets retain original search')
    p.add_argument('--route-regression-baseline',type=Path,
                   help='Immutable previous C++ source for exact default route/output/log replay; regression only')
    p.add_argument('--openroad-router-probe-only',action='store_true',
                   help='Execute small exact-technology OpenROAD search preflight only; no physical/system qualification')
    p.add_argument('--openroad-congestion-iterations',type=int,choices=[5,20,50],default=5,
                   help='CUGR search effort only; independent geometry, PG and RC acceptance remain unchanged')
    p.add_argument('--openroad-global-router',choices=['cugr','fastroute'],default='cugr',
                   help='Search only: compare global routers on the selected guide grid and original physical technology')
    p.add_argument('--openroad-guide-pitch-um',type=float,choices=[1.6,4],default=4,
                   help='Search only: unused lower track grids set24/60um guide tiles; actual M11/M12 tracks remain4um')
    p.add_argument('--openroad-snapshot-config',type=Path,
                   help='Bounded replay of SHA-bound search ODB/guides for DRC diagnosis only; never qualification')
    p.add_argument('--router-conflict-snapshot-config',type=Path,
                   help='Replay complete search paths for conflict diagnosis only; never routing qualification')
    p.add_argument('--multiply-congestion-history',action='store_true',
                   help='Search comparison only: multiply present and historical congestion penalties; all physical gates unchanged')
    p.add_argument('--native-cap-residual-config',type=Path,
                   help='Failure-only actual joined native ground capacitance plus optimistic upper-wire budget audit')
    p.add_argument('--native-pin-load-residual',type=Path,
                   help='Failure-only actual final-ODB minimum Liberty pin load added to an exact native/wire residual')
    p.add_argument('--lock-native-output-routes',action='store_true',
                   help='Independent search candidate: route original six macro outputs first within optimistic physical wire budgets, then protect these exact upper paths')
    p.add_argument('--negotiate-priority-routes',action='store_true',
                   help='Search only: retain clean trees, scale congestion costs with initial heuristic weight, allow priority output paths to be negotiated')
    p.add_argument('--defer-access-vias',action='store_true',
                   help='Search only: reserve every actual M11 landing, choose M11/M12 access vias during routing instead of fixing all stubs first')
    p.add_argument('--pin-aware-placement',action='store_true')
    p.add_argument('--electrical-placement-report',type=Path,
                   help='Source-bound actual-driver diagnostic for placement optimization only')
    p.add_argument('--placement-residual-budget',type=Path,
                   help='Search only: subtract measured native ground and minimum input pin capacitance from driver wire budgets')
    p.add_argument('--route-residual-budget',type=Path,
                   help='Search only: use source-bound measured native ground and minimum input pin capacitance in finite weak-output routing budgets; all final RC gates unchanged')
    p.add_argument('--placement-local-density-weight',type=float,choices=[0,1e6,1e7,1e8,1e9,1e10],default=0,
                   help='Search only: local16x16 uniform-bbox wire-density penalty; never a physical gate')
    p.add_argument('--placement-local-density-model',choices=['quantized','exact'],default='quantized',
                   help='Search only: optional exact rectangle-overlap demand; old quantized mode unchanged')
    p.add_argument('--reuse-placement',type=Path,
                   help='Reuse and independently reconstruct one exact source-bound diagnostic placement for routing')
    p.add_argument('--s-translation-proposal',type=Path,help='Diagnostic only: verify a prior S-only translation and freshly reconstruct all actual pins before original cap diagnostic')
    p.add_argument('--expand-routing-halo-um',type=int,choices=[0,512,1024,2048],default=0,
                   help='Diagnostic only: translate the exact reused scene and add equal routing whitespace on four sides; charge new area and recheck actual terminal bounds')
    p.add_argument('--rotate-electrical-placement',action='store_true',
                   help='Four rigid orientations, diagnostic only until actual geometry supports them')
    p.add_argument('--channel-gap-um',type=int,choices=[64,256,512,1024],default=64)
    p.add_argument('--placement-capacity-target',type=float,default=0,
                   help='Optional placement congestion proxy target; never a routing or electrical acceptance criterion')
    a=p.parse_args()
    assert not a.route_regression_baseline or a.route_regression_only or a.directional_regression_only
    assert a.route_nonpreferred_cost==2 or a.router=='cpp'
    assert not a.route_initial_order or a.router=='cpp'
    assert not a.route_adaptive_heuristic or(a.router=='cpp'and a.negotiate_priority_routes and not a.bidirectional_two_terminal)
    assert not a.bidirectional_two_terminal or (a.router=='cpp'and a.defer_access_vias)
    assert a.placement_capacity_target==0 or .35<=a.placement_capacity_target<=.8
    assert not a.placement_capacity_target or a.electrical_placement_report
    assert not a.placement_residual_budget or a.electrical_placement_report
    assert not a.placement_local_density_weight or a.electrical_placement_report
    assert a.placement_local_density_model=='quantized'or a.placement_local_density_weight>0
    assert not a.lock_native_output_routes or a.reuse_placement
    assert not a.route_critical_first or(a.negotiate_priority_routes and a.route_residual_budget)
    assert not a.route_ordinary_congestion_scale or(a.route_critical_first and a.route_congestion_scale==1 and not a.bidirectional_two_terminal)
    assert not a.route_ordinary_search_margin or a.route_ordinary_congestion_scale
    assert not a.route_ordinary_zero_pattern or(a.router=='cpp'and a.bidirectional_two_terminal and a.route_critical_first and a.route_residual_budget and a.negotiate_priority_routes and a.defer_access_vias and not a.route_ordinary_congestion_scale and not a.route_ordinary_search_margin)
    assert a.route_resource_labels==4000000 or(a.router=='cpp'and a.route_residual_budget)
    assert a.route_trial_attempts==0 or(a.router=='cpp'and 1<a.route_trials<=a.route_trial_attempts<=256)
    assert not a.route_residual_budget or (a.lock_native_output_routes and a.router=='cpp'and a.defer_access_vias)
    assert a.seed>=24 or (not a.pin_aware_placement and a.channel_gap_um==64)
    assert not a.electrical_placement_report or (a.seed>=24 and a.pin_aware_placement)
    assert not a.rotate_electrical_placement or (a.electrical_placement_report and(a.cap_lower_bound_only or a.plan_only))
    assert not a.expand_routing_halo_um or (a.reuse_placement and a.cap_lower_bound_only and not a.lock_native_output_routes)
    assert not a.s_translation_proposal or(a.reuse_placement and a.cap_lower_bound_only and not a.expand_routing_halo_um and not a.lock_native_output_routes)
    assert not a.reuse_placement or not(a.electrical_placement_report or a.rotate_electrical_placement or (a.cap_lower_bound_only and not(a.expand_routing_halo_um or a.s_translation_proposal)) or a.plan_only or a.pair_wire_feasibility_report)
    assert os.environ.get('SLURM_JOB_ID') and len(os.sched_getaffinity(0))<=16
    a.out.mkdir(parents=True,exist_ok=False)
    receipt=dict(passed=False,job=os.environ['SLURM_JOB_ID'],inputs={},whole_system_qualified=False)
    try:
        if a.search_phase_profile_config:
            import subprocess,sys
            helper=Path(__file__).with_name('search_phase_profile.py')
            for path in (a.manifest,a.graph,a.search_phase_profile_config,Path(__file__),helper):receipt['inputs'][str(path)]=sha(path)
            target=a.out/'profile'
            subprocess.run([sys.executable,str(helper),'--config',str(a.search_phase_profile_config),'--out',str(target)],check=True)
            child=target/'receipt.json';result=json.loads(child.read_text())
            assert result['passed']and result['stage']=='bounded-search-phase-diagnostic-only'and not result['whole_system_qualified']and not result['route_qualified']
            receipt['inputs'].update(result['inputs']);receipt['inputs'][str(child)]=sha(child)
            receipt.update(passed=True,stage='bounded-search-phase-diagnostic-only',route_qualified=False,whole_system_qualified=False,scope=result['scope'])
            return
        if a.program_event_trace_config:
            from program_event_trace import run
            run(a.program_event_trace_config,a.out,receipt)
            return
        if a.pattern_weight_regression_only or a.pattern_scale_regression_only:
            import subprocess,sys
            assert not(a.pattern_weight_regression_only and a.pattern_scale_regression_only)
            kind='scale'if a.pattern_scale_regression_only else'weight'
            helper=Path(__file__).with_name('pattern_'+kind+'_regression.py')
            for path in (a.manifest,a.graph,Path(__file__),helper):receipt['inputs'][str(path)]=sha(path)
            child=a.out/(kind+'-cases')
            subprocess.run([sys.executable,str(helper),'--out',str(child)],check=True)
            result=json.loads((child/'receipt.json').read_text())
            stage='ordinary-pattern-'+kind+'-regression-only'
            assert result['passed'] and result['stage']==stage and not result['whole_system_qualified']
            receipt['inputs'].update(result['inputs']);receipt['inputs'][str(child/'receipt.json')]=sha(child/'receipt.json')
            receipt.update(passed=True,stage=stage,whole_system_qualified=False)
            return
        if a.directional_regression_only:
            from directional_router_regression import run
            assert a.route_regression_baseline
            for name in ('ordinary_zero_pattern.h','ordinary_pattern_regression.py','directional_bidir_regression.py'):
                path=Path(__file__).with_name(name);receipt['inputs'][str(path)]=sha(path)
            for path in (Path(__file__),Path(__file__).with_name('directional_router_regression.py'),Path(__file__).with_name('tree_router_cpp.py'),Path(__file__).with_name('tree_router.cpp'),Path(__file__).with_name('resource_search.h'),Path(__file__).with_name('router_trial_pool.py'),Path(__file__).with_name('test_router_trial_pool.py'),a.route_regression_baseline):
                receipt['inputs'][str(path)]=sha(path)
            result=run(a.out,a.route_regression_baseline)
            (a.out/'directional-regression.json').write_text(json.dumps(result,indent=2)+'\n')
            receipt.update(passed=result['passed'],stage='directional-search-regression-only',whole_system_qualified=False)
            return
        if a.router_conflict_snapshot_config:
            import subprocess,sys
            helper=Path(__file__).with_name('router_conflict_snapshot.py')
            config=json.loads(a.router_conflict_snapshot_config.read_text())
            assert config['graph']==str(a.graph)
            for path in (a.manifest,a.graph,a.router_conflict_snapshot_config,Path(__file__),helper):receipt['inputs'][str(path)]=sha(path)
            target=a.out/'complete-paths'
            subprocess.run([sys.executable,str(helper),'--config',str(a.router_conflict_snapshot_config),'--out',str(target)],check=True)
            child=target/'receipt.json';result=json.loads(child.read_text())
            assert result['passed']and result['stage']=='complete-search-path-diagnostic-only'and not result['whole_system_qualified']
            receipt['inputs'].update(result['inputs'])
            report=target/'complete-path-diagnostics.json'
            assert result['outputs'][report.name]==sha(report)
            (a.out/'complete-path-summary.json').write_text(json.dumps(dict(child_receipt=str(child),child_receipt_sha256=sha(child),report=str(report),report_sha256=sha(report),whole_system_qualified=False),indent=2)+'\n')
            receipt.update(passed=True,stage='complete-search-path-diagnostic-only',whole_system_qualified=False,
                           scope='Complete original search paths and exact count replay only. No routing, geometry, PG, RC or timing qualification.')
            return
        if a.openroad_snapshot_config:
            from openroad_snapshot import inspect
            def bind_snapshot(path,digest=None):
                actual=sha(path)
                if digest is not None:assert actual==digest
                receipt['inputs'][str(path)]=actual
            for path in (a.openroad_snapshot_config,Path(__file__),Path(__file__).with_name('openroad_snapshot.py'),Path(__file__).with_name('openroad_grid.py')):
                bind_snapshot(path)
            result=inspect(a.openroad_snapshot_config,a.out,bind_snapshot)
            receipt.update(passed=result['execution_passed'],stage='bounded-routing-diagnostic-only',scope=result['scope'])
            return
        if a.openroad_router_probe_only:
            from openroad_router_probe import run
            for path in (Path(__file__), Path(__file__).with_name('openroad_router_probe.py'),
                         Path(__file__).with_name('openroad_grid.py'),
                         ROOT/'project/experiments/block_v1/overlay.py',
                         ROOT/'project/experiments/block_v1/technology-2um-v1.json',
                         ROOT/'project/experiments/block_v1/odb_geometry.tcl'):
                receipt['inputs'][str(path)]=sha(path)
            result=run(a.out,congestion_iterations=a.openroad_congestion_iterations,global_router=a.openroad_global_router,guide_pitch=a.openroad_guide_pitch_um)
            receipt.update(passed=result['execution_passed'],stage='openroad-small-search-preflight-only',scope=result['scope'])
            return
        if a.native_pin_load_residual:
            from native_pin_load import inspect
            def bind(path,digest=None):
                actual=sha(path)
                if digest is not None:assert actual==digest
                receipt['inputs'][str(path)]=actual
            bind(Path(__file__).with_name('native_pin_load.py'))
            result=inspect(a.manifest,a.graph,a.native_pin_load_residual,a.out,bind)
            (a.out/'native-pin-load.json').write_text(json.dumps(result,indent=2)+'\n')
            receipt.update(passed=True,stage='minimum-native-pin-capacitance-failure-only',scope=result['scope'])
            return
        if a.native_cap_residual_config:
            from native_cap_residual import inspect
            helper=Path(__file__).with_name('native_cap_residual.py');receipt['inputs'][str(helper)]=sha(helper)
            result=inspect(a.native_cap_residual_config,a.manifest,a.graph,a.out,receipt['inputs'],sha)
            receipt.update(passed=result['passed'],stage='native-ground-plus-upper-lower-bound-only',scope=result['scope'])
            return
        if a.route_regression_only:
            from router_regression import run
            for name in ('router_regression.py','tree_router_cpp.py','tree_router.cpp','resource_search.h','ordinary_zero_pattern.h'):
                path=Path(__file__).with_name(name);receipt['inputs'][str(path)]=sha(path)
            if a.route_regression_baseline:receipt['inputs'][str(a.route_regression_baseline)]=sha(a.route_regression_baseline)
            result=run(a.out,baseline_source=a.route_regression_baseline)
            receipt.update(passed=result['passed'],stage='route-search-regression-only',scope=result['scope'])
            return
        m=json.loads(a.manifest.read_text());g=json.loads(a.graph.read_text())
        assert g['passed'] and g['no_unassigned_active_logic']
        from boundary_links import validate
        validate(m,g)
        receipt['inputs']={str(a.manifest):sha(a.manifest),str(a.graph):sha(a.graph),str(Path(__file__)):sha(Path(__file__)),
                           str(Path(__file__).with_name('tree_router.py')):sha(Path(__file__).with_name('tree_router.py'))}
        receipt['inputs'][str(Path(__file__).with_name('boundary_links.py'))]=sha(Path(__file__).with_name('boundary_links.py'))
        receipt['inputs'][str(Path(__file__).with_name('r256_scene.py'))]=sha(Path(__file__).with_name('r256_scene.py'))
        plans={}
        for name,row in m['leaves'].items():
            path=Path(row['pins']);assert sha(path)==row['pins_sha256']
            assert g['inputs'][str(path)]==row['pins_sha256']
            receipt['inputs'][str(path)]=sha(path)
            plans[name]={pin['pin']:pin for pin in json.loads(path.read_text())['pins']}
        if a.pg_wrappers:
            from pg_interface import inventory,augment
            access=inventory(m,a.pg_wrappers,a.out,candidate=a.pg_candidate_access)
            for top in plans:plans[top].update(access['contacts'][top])
            receipt['inputs'].update(access['inputs'])
            g=augment(g,access,a.out/'pg-access.json')
            (a.out/'physical-graph.json').write_text(json.dumps(g,indent=2)+'\n')
            receipt['inputs'][str(a.out/'physical-graph.json')]=sha(a.out/'physical-graph.json')
            receipt['inputs'][str(a.out/'pg-access.json')]=sha(a.out/'pg-access.json')
        if a.pair_wire_feasibility_report:
            assert not(a.cap_lower_bound_only or a.plan_only or a.electrical_placement_report)
            from pair_wire_feasibility import inspect
            helper=Path(__file__).with_name('pair_wire_feasibility.py');receipt['inputs'][str(helper)]=sha(helper)
            result=inspect(m,g,plans,a.pair_wire_feasibility_report,a.out,sha)
            receipt['inputs'].update(result['inputs'])
            receipt.update(passed=True,stage='pair-wire-feasibility-diagnostic-only',
                           impossible_pair_counts=result['impossible_pair_counts'],
                           scope='Executed necessary-condition diagnostic only. No route or system acceptance.')
            return
        from r256_scene import is_r256,placement_pin_maps,phase_placement
        placement_plans=placement_pin_maps(m,plans)
        gap=[32,64,96][a.seed%3]
        rows=[1,2,3,4,5,6,0]+([7]if is_r256(g['instances'])else[])
        if a.seed>=3:rows=list(reversed(rows))
        if a.seed>=6:random.Random(a.seed).shuffle(rows)
        placement={};orientations={name:0 for name in g['instances']};y=128;padding=128
        def align(v):return 4*math.ceil(v/4)
        def put(name,x,y):
            assert name in g['instances'] and name not in placement
            placement[name]=[align(x),align(y)]
            return m['leaves'][g['instances'][name]]['die_um']
        # Each queue, adapter and native compute/storage leaf has one explicit
        # physical instance. No block is resized or geometrically modified.
        for role in rows:
            x=128;height=0
            names=['queue_'+str(role),'endpoint_'+str(role)]
            if role in (1,2,3,4):names+=['macro_'+str(role)]
            elif role==5:names+=['macro_s','s_port']
            elif role==6:names+=['macro_t']
            elif role==7:names+=['macro_r']
            for name in names:
                w,h=put(name,x,y);x=align(x+w+gap);height=max(height,h)
            y=align(y+height+gap)
        x=128
        for name in ('host','controller','routes','system_status','reset_distribution'):
            w,h=put(name,x,y);x=align(x+w+gap)
        reused=None
        if a.reuse_placement:
            parent=a.reuse_placement/'receipt.json';proof=json.loads(parent.read_text())
            assert proof['passed']and proof['stage']in('wire-cap-lower-bound-only','placement-preflight-only')
            assert proof['inputs'][str(a.manifest)]==sha(a.manifest)and proof['inputs'][str(a.graph)]==sha(a.graph)
            path=a.reuse_placement/'placement.json';assert proof['outputs'][path.name]==sha(path)
            receipt['inputs'][str(parent)]=sha(parent);receipt['inputs'][str(path)]=sha(path)
            reused=json.loads(path.read_text());placement=reused['placements_um'];orientations=reused['orientations']
            assert set(orientations)==set(g['instances'])and all(v==0 for v in orientations.values()),'Actual mask assembly currently supports N only'
        elif g.get('boundary_links'):
            assert not a.rotate_electrical_placement
            from linked_floorplan import place
            for name in ('linked_floorplan.py','floorplan.py','electrical_floorplan.py'):
                helper=Path(__file__).with_name(name);receipt['inputs'][str(helper)]=sha(helper)
            if a.electrical_placement_report:
                driver_receipt=a.electrical_placement_report.parent/'receipt.json'
                assert json.loads(driver_receipt.read_text())['inputs'][str(a.graph)]==sha(a.graph)
            if a.placement_residual_budget:
                rr=json.loads((a.placement_residual_budget.parent/'receipt.json').read_text())
                for path in (a.manifest,a.graph):assert rr['inputs'][str(path)]==sha(path)
            placement,placement_proof=place(m,g,placement_plans,a.seed,a.channel_gap_um,a.electrical_placement_report,a.out,capacity_target=a.placement_capacity_target,residual_report=a.placement_residual_budget,local_weight=a.placement_local_density_weight,local_model=a.placement_local_density_model)
            receipt['inputs'].update(placement_proof.get('inputs',{}))
            (a.out/'placement-search.json').write_text(json.dumps(placement_proof,indent=2)+'\n')
        elif a.electrical_placement_report:
            from electrical_floorplan import place
            helper=Path(__file__).with_name('electrical_floorplan.py');receipt['inputs'][str(helper)]=sha(helper)
            if a.placement_residual_budget:
                rr=json.loads((a.placement_residual_budget.parent/'receipt.json').read_text())
                for path in (a.manifest,a.graph):assert rr['inputs'][str(path)]==sha(path)
            placement,placement_proof=place(m,g,placement_plans,a.seed,a.channel_gap_um,a.electrical_placement_report,a.out,a.rotate_electrical_placement,capacity_target=a.placement_capacity_target,residual_report=a.placement_residual_budget,local_weight=a.placement_local_density_weight,local_model=a.placement_local_density_model)
            orientations=placement_proof['rotations']
            receipt['inputs'].update(placement_proof['inputs'])
            padding=128
            (a.out/'placement-search.json').write_text(json.dumps(placement_proof,indent=2)+'\n')
        elif a.seed>=24:
            from floorplan import place
            helper=Path(__file__).with_name('floorplan.py');receipt['inputs'][str(helper)]=sha(helper)
            placement,placement_proof=place(g['instances'],m['leaves'],g['connections'],a.seed,
                pin_maps=placement_plans if a.pin_aware_placement else None,gap_um=a.channel_gap_um)
            padding=[128,512,1024,2048][(a.seed-24)%4]
            placement={name:[x+padding-128,y+padding-128] for name,(x,y) in placement.items()}
            placement_proof['routing_halo_um']=padding
            (a.out/'placement-search.json').write_text(json.dumps(placement_proof,indent=2)+'\n')
        placement=phase_placement(m,g['instances'],placement,reused=bool(reused))
        if is_r256(g['instances']):
            assert orientations['macro_r']==0,'R256 native phase currently supports exact N orientation only'
            receipt['R256_rigid_translation_um']=[.095,.07]
        assert set(placement)==set(g['instances'])
        width=align(max(x+m['leaves'][g['instances'][n]]['die_um'][0] for n,(x,y) in placement.items())+padding)
        height=align(max(y+m['leaves'][g['instances'][n]]['die_um'][1] for n,(x,y) in placement.items())+padding)
        if reused:
            # A source-bound scene may intentionally retain routing whitespace.
            assert reused['width_um']>=width and reused['height_um']>=height
            width=reused['width_um'];height=reused['height_um']
        for n,(x,y) in placement.items():
            w,h=m['leaves'][g['instances'][n]]['die_um']
            for other,(xx,yy) in placement.items():
                if n>=other:continue
                ww,hh=m['leaves'][g['instances'][other]]['die_um']
                assert x+w<=xx or xx+ww<=x or y+h<=yy or yy+hh<=y,('Overlapping frozen leaves',n,other)
        def point(end):
            name=end['instance'];pin=plans[g['instances'][name]][end['pin']]
            if 'xy_um' in pin:x,y=pin['xy_um']
            else:
                b=pin['box_dbu'];x=(b[0]+b[2])/4000;y=(b[1]+b[3])/4000
            if orientations[name]:
                from placement_orientation import transform
                x,y=transform((x,y),m['leaves'][g['instances'][name]]['die_um'],orientations[name])
            dx,dy=placement[name];gx=(x+dx-.095)/4;gy=(y+dy-.07)/4
            assert abs(gx-round(gx))<1e-7 and abs(gy-round(gy))<1e-7,(name,end['pin'],x,y)
            return round(gx),round(gy)
        nx,ny=int(width/4),int(height/4)
        border=[(x,8) for x in range(8,nx-8)]+[(nx-8,y) for y in range(9,ny-8)]+[(x,ny-8) for x in range(nx-9,7,-1)]+[(8,y) for y in range(ny-9,8,-1)]
        top_pins=sorted({e['pin'] for c in g['connections'].values() for e in [c['driver'],*c['sinks']] if e['instance']=='TOP'})
        assert len(top_pins)<len(border)
        external={pin:border[(i*len(border))//len(top_pins)] for i,pin in enumerate(top_pins)}
        if reused:
            external={pin:tuple(point)for pin,point in reused['external_grid_pins'].items()}
            assert set(external)==set(top_pins)and len(set(external.values()))==len(external)
            assert set(external.values())<=set(border)
        if a.electrical_placement_report:
            # Actual terminal assignment is distinct from the optimistic
            # placement objective. Use unique existing perimeter grid sites;
            # the independent capacitance diagnostic measures these real sites.
            constraints={row['net']:row['physical_driver']['max_capacitance_ff']
                         for row in json.loads(a.electrical_placement_report.read_text())['rows']}
            groups=[]
            for bit,c in g['connections'].items():
                ends=[c['driver'],*c['sinks']];top=[e['pin']for e in ends if e['instance']=='TOP']
                if not top:continue
                actual=[point(e)for e in ends if e['instance']!='TOP'];assert actual
                x0=min(v[0]for v in actual);x1=max(v[0]for v in actual)
                y0=min(v[1]for v in actual);y1=max(v[1]for v in actual)
                budget=constraints.get('net_'+bit,float('inf'))
                groups.extend((budget,pin,(x0,y0,x1,y1))for pin in top)
            external={};available=set(border)
            for budget,pin,(x0,y0,x1,y1)in sorted(groups):
                assert pin not in external
                def cost(p):
                    x,y=p;return(max(x1,x)-min(x0,x)+max(y1,y)-min(y0,y),
                                abs(2*x-x0-x1)+abs(2*y-y0-y1),x,y)
                chosen=min(available,key=cost);available.remove(chosen);external[pin]=chosen
            assert set(external)==set(top_pins)
        terminals={}
        for bit,c in g['connections'].items():
            terminals['net_'+bit]=[external[e['pin']] if e['instance']=='TOP' else point(e) for e in [c['driver'],*c['sinks']]]
        all_points=[point for ends in terminals.values() for point in ends]
        assert len(all_points)==len(set(all_points)), 'Overlapping terminal landings'
        (a.out/'placement.json').write_text(json.dumps(dict(placements_um=placement,orientations=orientations,width_um=width,height_um=height,
             external_grid_pins=external,terminals=terminals,graph=str(a.graph),graph_sha256=sha(a.graph)),indent=2)+'\n')
        if reused:assert json.loads((a.out/'placement.json').read_text())==reused,'Reconstructed actual pins/PG/terminals differ from selected placement'
        if a.s_translation_proposal:
            from s_pair_placement import apply_proposal
            before=terminals;original_path=a.out/'placement.json';(a.out/'before-s-translation.json').write_bytes(original_path.read_bytes())
            changed,proposal,bindings=apply_proposal(a.s_translation_proposal,a.reuse_placement/'placement.json',a.manifest,a.graph,reused,m,g);receipt['inputs'].update(bindings)
            old_origin=placement['macro_s'];placement=changed['placements_um'];delta=[int(round((placement['macro_s'][i]-old_origin[i])/4))for i in range(2)]
            terminals={
                'net_'+bit:[external[e['pin']]if e['instance']=='TOP'else point(e)for e in[c['driver'],*c['sinks']]]
                for bit,c in g['connections'].items()}
            for bit,c in g['connections'].items():
                name='net_'+bit;expected=[tuple(v[i]+(delta[i]if e['instance']=='macro_s'else 0)for i in range(2))for v,e in zip(before[name],[c['driver'],*c['sinks']])]
                assert terminals[name]==expected,('Fresh actual-pin reconstruction differs from S-only translation',name)
            weak=priority_outputs(g);assert all(terminals[name]==before[name]for name in weak)
            all_points=[v for ends in terminals.values()for v in ends];assert len(all_points)==len(set(all_points))
            pair_lengths=[]
            for bit,c in g['connections'].items():
                ends=[c['driver'],*c['sinks']]
                if len(ends)==2 and{e['instance']for e in ends}=={'macro_s','s_port'}:
                    u,v=terminals['net_'+bit];pair_lengths.append(4*(abs(u[0]-v[0])+abs(u[1]-v[1])))
            assert len(pair_lengths)==proposal['pair_count']and sum(pair_lengths)==proposal['sum_pair_hpwl_um']
            changed['terminals']=terminals;original_path.write_text(json.dumps(changed,indent=2)+'\n')
            result=dict(proposal=str(a.s_translation_proposal),proposal_sha256=sha(a.s_translation_proposal),old_origin_um=old_origin,new_origin_um=placement['macro_s'],actual_pair_hpwl_sum_um=sum(pair_lengths),actual_pair_count=len(pair_lengths),unchanged_constrained_endpoint_nets=len(weak),actual_pin_reconstruction_passed=True,all_other_origins_and_masks_unchanged=True,die_unchanged=True,whole_system_qualified=False)
            (a.out/'s-translation.json').write_text(json.dumps(result,indent=2)+'\n');receipt['S_only_translation']=result
        if a.expand_routing_halo_um:
            from routing_halo import expand
            helper=Path(__file__).with_name('routing_halo.py');receipt['inputs'][str(helper)]=sha(helper)
            changed=expand(reused,a.expand_routing_halo_um)
            placement=changed['placements_um'];width=changed['width_um'];height=changed['height_um']
            external={n:tuple(v)for n,v in changed['external_grid_pins'].items()};nx=int(width/4);ny=int(height/4)
            terminals={
                'net_'+bit:[external[e['pin']]if e['instance']=='TOP'else point(e)for e in [c['driver'],*c['sinks']]]
                for bit,c in g['connections'].items()}
            assert terminals=={n:[tuple(v)for v in ends]for n,ends in changed['terminals'].items()},'Independent actual-pin reconstruction differs from translated scene'
            (a.out/'placement.json').write_text(json.dumps(changed,indent=2)+'\n')
            (a.out/'routing-halo.json').write_text(json.dumps(dict(parent=str(a.reuse_placement),additional_halo_um=a.expand_routing_halo_um,
                old_area_um2=reused['width_um']*reused['height_um'],new_area_um2=width*height,
                all_relative_macro_positions_preserved=True,macro_masks_unchanged=True,whole_system_qualified=False),indent=2)+'\n')
        if a.cap_lower_bound_only:
            assert not a.plan_only
            from upper_cap_bound import inspect
            helper=Path(__file__).with_name('upper_cap_bound.py');receipt['inputs'][str(helper)]=sha(helper)
            bound=inspect(m,g,terminals,a.out,receipt['inputs'],sha)
            receipt.update(passed=True,stage='wire-cap-lower-bound-only',
                placement_proven_cap_infeasible=bound['low_variant_wire_only_violations']>0,
                scope='Executed actual-driver/shortest-wire necessary-condition diagnostic only. Passing the diagnostic is never geometry, routing or timing acceptance.')
            return
        if a.plan_only:
            receipt.update(passed=True,stage='placement-preflight-only',net_count=len(terminals),
                           scope='Input, nonoverlap and actual terminal landing validation only. No routing/physical/timing acceptance.')
            return
        def progress(row):
            row['unix_time']=time.time();(a.out/'progress.json').write_text(json.dumps(row)+'\n')
            print(json.dumps(row),flush=True)
        if a.router in ('cpp','openroad'):
            from tree_router_cpp import route as route_compiled
            helper=Path(__file__).with_name('ordinary_zero_pattern.h');receipt['inputs'][str(helper)]=sha(helper)
            helper=Path(__file__).with_name('tree_router_cpp.py');receipt['inputs'][str(helper)]=sha(helper)
            header=Path(__file__).with_name('resource_search.h');receipt['inputs'][str(header)]=sha(header)
            if a.route_trial_attempts:
                pool=Path(__file__).with_name('router_trial_pool.py');receipt['inputs'][str(pool)]=sha(pool)
            locked=[];limits={}
            if a.lock_native_output_routes:
                diagnostic=a.reuse_placement/'wire-cap-lower-bound.json';parent=json.loads((a.reuse_placement/'receipt.json').read_text())
                assert parent['outputs'][diagnostic.name]==sha(diagnostic);receipt['inputs'][str(diagnostic)]=sha(diagnostic)
                bounds=json.loads(diagnostic.read_text());assert bounds['executed']and bounds['research_model']
                rows={row['net']:row for row in bounds['rows']}
                remaining={name:row['physical_driver']['max_capacitance_ff']for name,row in rows.items()}
                if a.route_residual_budget:
                    from placement_residual_budget import budgets
                    measured=json.loads((a.route_residual_budget.parent/'receipt.json').read_text())
                    for path in (a.manifest,a.graph):assert measured['inputs'][str(path)]==sha(path)
                    actual=json.loads(a.route_residual_budget.read_text())
                    assert any(Path(row['placement'])==a.reuse_placement for row in actual['placements']),'Measured native/input bound does not include selected placement'
                    remaining,bindings=budgets(a.route_residual_budget,rows)
                    receipt['inputs'].update(bindings)
                technology=ROOT/'project/experiments/block_v1/technology-2um-v1.json';receipt['inputs'][str(technology)]=sha(technology);model=json.loads(technology.read_text())
                per_edge=bounds['ff_per_um_base']*model['electrical']['estimate_variants']['high']*model['geometry_um']['pitch']
                locked=priority_outputs(g)
                for name in locked:
                    bit=name[4:];c=g['connections'][bit];row=rows[name]
                    assert row['driver']==c['driver']and c['sinks']
                    # A padded Link8 repeats one real source on its unused
                    # input lanes. Preserve every physical sink and its load;
                    # the invariant is one receiver macro, not one pin.
                    assert len({s['instance']for s in c['sinks']})==1
                    assert all(g['instances'][s['instance']]=='control_link8'for s in c['sinks'])
                    limits[name]=math.floor(remaining[name]/per_edge+1e-12)
                locked.sort(key=lambda n:(-rows[n]['wire_capacitance_lower_bound_ff']['high']/rows[n]['physical_driver']['max_capacitance_ff'],n))
                (a.out/'locked-original-output-search.json').write_text(json.dumps(dict(nets=locked,wire_limits_grid_edges=limits,
                    negotiated_priority=a.negotiate_priority_routes,
                    measured_native_and_minimum_input_pin_cap_subtracted=bool(a.route_residual_budget),
                    scope='Search ordering and optional immutable upper paths only. Optional measured native ground/minimum input pin subtraction is source bound; unselected default ignores them. Both modes omit via/coupling and possibly larger actual input capacitance, remain failure-only necessary conditions; complete actual geometry/RC/300MHz remains mandatory.'),indent=2)+'\n')
            if a.router=='openroad':
                from openroad_router_probe import route as route_openroad
                for path in (Path(__file__).with_name('openroad_router_probe.py'),Path(__file__).with_name('openroad_grid.py'),
                             ROOT/'project/experiments/block_v1/overlay.py',ROOT/'project/experiments/block_v1/odb_geometry.tcl'):
                    receipt['inputs'][str(path)]=sha(path)
                assert a.route_trials==1, 'OpenROAD runs one 16-thread search per independent slot'
                branches,proof=route_openroad(terminals,nx,ny,a.seed,a.out,limits,a.openroad_congestion_iterations,a.openroad_global_router,a.openroad_guide_pitch_um)
            else:
                branches,proof=route_compiled(terminals,nx,ny,a.seed,80,a.out,trials=a.route_trials,heuristic_weight=a.route_heuristic_weight,locked_names=locked,wire_limits=limits,negotiated_priority=a.negotiate_priority_routes,defer_access_vias=a.defer_access_vias,congestion_scale=a.route_congestion_scale,history_product=a.multiply_congestion_history,initial_order=a.route_initial_order,bidirectional_two_terminal=a.bidirectional_two_terminal,adaptive_heuristic=a.route_adaptive_heuristic,nonpreferred_cost=a.route_nonpreferred_cost,pareto_wire_budget=bool(a.route_residual_budget),trial_attempts=a.route_trial_attempts,resource_label_limit=a.route_resource_labels,critical_first=a.route_critical_first,ordinary_congestion_scale=a.route_ordinary_congestion_scale,ordinary_search_margin=a.route_ordinary_search_margin,ordinary_zero_pattern=a.route_ordinary_zero_pattern)
        else:
            branches,proof=route(terminals,nx,ny,seed=a.seed,progress=progress)
        (a.out/'trees.json').write_text(json.dumps(branches)+'\n')
        (a.out/'search.json').write_text(json.dumps(proof,indent=2)+'\n')
        receipt.update(passed=True,net_count=len(terminals),instance_count=len(g['instances']),search=proof,
                       scope='All extracted signal, clock and reset boundary nets routed as connected disjoint grid trees. Actual geometry readback, PG and combined timing remain separate mandatory gates.')
    finally:
        receipt['outputs']={p.name:sha(p) for p in a.out.iterdir() if p.is_file()}
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':main()
