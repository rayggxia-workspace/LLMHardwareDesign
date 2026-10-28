"""Compile the approved six-resource union and a shared passive-wire contract.

This is preparation, NOT a frozen/implemented base. Every original logical bit
and physical pin is retained. Both modes must actually consume the same fixed
conductors before the eventual common-base checker may accept either mode.
"""
from pathlib import Path
from collections import Counter, defaultdict
import argparse, csv, gzip, hashlib, itertools, json, math
import numpy as np
import pandas as pd
from inventory import load, owner, pin_names

CASES = ['act', 'mxu', 'opentpu_aux', 'gemm', 'vector', 'llaccel_aux']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def dump(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def prepare(root, out):
    root, out = Path(root), Path(out)
    assert not out.exists(), 'Refuse existing common-base preparation'
    maps = load(root/'inventory/pin_logical_mapping.json')
    frame, pinsets = {}, {}
    for c in CASES:
        meta = load(root/(c+'.meta.json'))
        frame[c] = [v/meta['units_per_micron'] for v in meta['die_dbu']][2:]
        d = pd.read_csv(root/(c+'_pin_coordinates.csv'), low_memory=False)
        a, proposed = d[d.plan == 'A'].set_index('pin'), d[d.plan == 'C'].set_index('pin')
        replacement = {'act': ('trial-inputs-act-access-publication-r04','act_C_access_r03_all_pins.csv'),
                       'gemm': ('trial-inputs-gemm-electrical-publication-r04', 'gemm_C_electrical_r03_all_pins.csv'),
                       'mxu': ('trial-inputs-mxu-repair-r04', 'mxu_C_repair_r03_all_pins.csv'),
                       'llaccel_aux': ('trial-inputs-llsys-pg-r03', 'llaccel_aux_C_pg_r03_all_pins.csv')}.get(c)
        if replacement:
            p = (root if c in ['act','llaccel_aux'] else root.parent)/replacement[0]/replacement[1]
            assert p.exists(), p
            proposed = pd.read_csv(p, low_memory=False).set_index('pin')
        optimized = a.copy()
        p = root/'full_cohort_controls'/(c+'-Aopt.csv.gz')
        assert p.exists(), p
        edge = pd.read_csv(p, low_memory=False).set_index('pin')
        for column in ['x_um', 'y_um', 'x0_um', 'y0_um', 'x1_um', 'y1_um']:
            optimized.loc[edge.index, column] = edge[column]
        optimized['plan'] = 'Aopt'
        optimized['moved'] = (abs(optimized.x_um-a.x_um)>1e-6)|(abs(optimized.y_um-a.y_um)>1e-6)
        assert set(a.index) == set(proposed.index) == set(maps[c])
        proposed = proposed.loc[a.index]
        for v in [optimized, proposed]:
            assert all(v[k].equals(a[k]) for k in ['layer', 'direction', 'use', 'net'])
            assert np.allclose(v.x1_um-v.x0_um, a.x1_um-a.x0_um)
            assert np.allclose(v.y1_um-v.y0_um, a.y1_um-a.y0_um)
        pinsets[c] = {'Aopt': optimized, 'C': proposed}
    nets, graphs = {}, {}
    for design in ['opentpu', 'llaccel']:
        graph = load(root/'partition-r02'/(design+'_partition_graph.json.gz'))
        graphs[design] = graph
        bybit = defaultdict(list)
        for inst, cell in graph['top_module']['cells'].items():
            c = owner(inst, design)
            for name, port in graph['frontier'][cell['type']]['ports'].items():
                for pin, bit in zip(pin_names(name, port), cell['connections'][name]):
                    assert isinstance(bit, int)
                    bybit[bit].append({'kind': 'ITERM', 'case': c, 'pin': pin, 'direction': port['direction'],
                                       'original_pin_layer': str(pinsets[c]['Aopt'].loc[pin, 'layer'])})
        for name, port in graph['top_module']['ports'].items():
            for pin, bit in zip(pin_names(name, port), port['bits']):
                key=bit if isinstance(bit,int) else 'LITERAL_OUTPUT_'+pin
                term={'kind': 'TOP_IO', 'pin': pin, 'direction': port['direction'], 'layer': 'NEW_PARENT_POLICY_NOT_YET_IMPLEMENTED'}
                if isinstance(bit,str):
                    term.update({'literal':bit,'physical_constant_net':'Distinct declaration; physical driver/lowering still required, never short all same-valued ports'})
                bybit[key].append(term)
        nets[design] = {str(bit): terms for bit, terms in bybit.items()}
    # Explicitly select actual read buses, not synthetic lanes or new protocols.
    selected = {}
    for design, c, bus in [('opentpu', 'act', 'r_data'), ('llaccel', 'gemm', 'gemm_a_rdata')]:
        bits = {int(q['semantic_bit']): str(q['parent_bit']) for q in maps[c].values() if q['semantic_bus'] == bus}
        assert set(range(256)) <= set(bits)
        selected[design] = [bits[i] for i in range(256)]
        for bit in selected[design]:
            terms = nets[design][bit]
            assert len(terms) == 2 and all(q['kind'] == 'ITERM' for q in terms)
            assert Counter(q['direction'] for q in terms) == {'input': 1, 'output': 1}
    # Enumerated placement proxy uses both designs' real connection counts.
    weights = Counter()
    for graph in nets.values():
        for terms in graph.values():
            cs = sorted({q['case'] for q in terms if q['kind'] == 'ITERM'})
            for a, b in itertools.combinations(cs, 2):
                weights[a, b] += 1
    snap = lambda x: round(math.ceil(x/11.2-1e-8)*11.2, 6)
    gap, margin = snap(192.), snap(80.)
    candidates = []
    for perm in itertools.permutations(CASES):
        col1 = max(frame[perm[i]][0] for i in [0, 2, 4])
        pos, y = {}, margin
        for i in [0, 2, 4]:
            pos[perm[i]] = [margin, y]
            pos[perm[i+1]] = [snap(margin+col1+gap), y]
            y = snap(y+max(frame[perm[i]][1], frame[perm[i+1]][1])+gap)
        # Require at least one mixed row and one mixed column by active mode.
        mode = lambda c: 'opentpu' if c in ['act', 'mxu', 'opentpu_aux'] else 'llaccel'
        if not any(mode(perm[i]) != mode(perm[i+1]) for i in [0, 2, 4]):
            continue
        if not any(len({mode(perm[i]) for i in column}) > 1 for column in [[0, 2, 4], [1, 3, 5]]):
            continue
        center = {c: np.array(pos[c])+np.array(frame[c])/2 for c in CASES}
        cost = sum(n*float(abs(center[a]-center[b]).sum()) for (a, b), n in weights.items())
        w = snap(max(pos[c][0]+frame[c][0] for c in CASES)+margin)
        h = snap(max(pos[c][1]+frame[c][1] for c in CASES)+margin)
        candidates.append((cost, w*h, perm, pos, w, h, col1))
    cost, area, perm, pos, width, height, col1 = min(candidates)
    # Shared M10 segments occupy the explicit inter-column corridor. They are
    # real finite two-terminal passive resources, not arbitrary intersections.
    prewires = []
    cx = round(.095+round((margin+col1+gap/2-.095)/3.2)*3.2, 6)
    ys=[]
    for design in ['opentpu','llaccel']:
        for bit in selected[design]:
            for term in nets[design][bit]:
                for scheme in ['Aopt','C']:
                    ys.append(float(pinsets[term['case']][scheme].loc[term['pin'],'y_um'])+pos[term['case']][1])
    center_y=float(np.median(ys))
    first_y=max(margin+64,min(center_y-3.5*96,height-margin-64-32-7*96))
    for i in range(256):
        x = round(cx+(i % 32-16)*3.2, 6)
        y = round(.07+round((first_y+(i//32)*96.-.07)/1.6)*1.6, 6)
        prewires.append({'resource': 'R'+format(i, '04d'), 'layer': 'metal10', 'x0_um': x-.4, 'y0_um': y-.4,
                         'x1_um': x+.4, 'y1_um': y+32.+.4, 'centerline_length_um': 32., 'width_um': .8,
                         'pad_A_xy_um': [x, y], 'pad_B_xy_um': [x, y+32.]})
    for q in prewires:
        assert 0<q['x0_um']<q['x1_um']<width and 0<q['y0_um']<q['y1_um']<height
        for c in CASES:
            x,y=pos[c];w,h=frame[c]
            assert not (q['x0_um']<x+w and q['x1_um']>x and q['y0_um']<y+h and q['y1_um']>y),'Proposed common corridor intersects a macro outline'
    bindings = []
    for design in ['opentpu', 'llaccel']:
        for i, bit in enumerate(selected[design]):
            terms = nets[design][bit]
            source = next(q for q in terms if q['direction'] == 'output')
            sink = next(q for q in terms if q['direction'] == 'input')
            bindings.append({'mode': design, 'resource': 'R'+format(i, '04d'), 'original_parent_bit': bit,
                             'source_case': source['case'], 'source_pin': source['pin'], 'source_pin_layer': source['original_pin_layer'],
                             'sink_case': sink['case'], 'sink_pin': sink['pin'], 'sink_pin_layer': sink['original_pin_layer'],
                             'bus_selection': 'Original read bus bits0:255; 32-byte research cut, not a new lane/protocol'})
    out.mkdir(parents=True)
    placements = [{'case': c, 'instance': 'u_'+c, 'x_um': pos[c][0], 'y_um': pos[c][1], 'width_um': frame[c][0],
                   'height_um': frame[c][1], 'orientation': 'R0', 'enabled_in': 'opentpu' if c in ['act','mxu','opentpu_aux'] else 'llaccel'} for c in CASES]
    pd.DataFrame(placements).to_csv(out/'common_floorplan.csv', index=False)
    pd.DataFrame(prewires).to_csv(out/'shared_prewire_geometry.csv', index=False)
    pd.DataFrame(bindings).to_csv(out/'shared_prewire_bindings.csv', index=False)
    for scheme in ['Aopt', 'C']:
        pd.concat([pinsets[c][scheme].reset_index().assign(case=c) for c in CASES], ignore_index=True).to_csv(out/(scheme+'_all_24767_pins.csv'), index=False, float_format='%.6f')
    dump(out/'complete_mode_nets.json', nets)
    contract = {'status': 'PREPARATION_COMPLETE_BASE_NOT_ROUTED_OR_FROZEN', 'frozen': False,
                'approved_resource_policy': 'Six original functional resources; interleaved common placement; both modes must physically reuse shared fixed conductors',
                'original_signal_pins': sum(len(pinsets[c]['C']) for c in CASES), 'instances': placements,
                'original_constant_TOP_IO_declarations':37,
                'additional_parent_infrastructure_inventory_complete':False,
                'frame_um': [0, 0, width, height], 'shared_fixed_passive_components': 256,
                'R0_placement_phase_pitch_um':11.2,
                'shared_wire_total_length_um': 8192., 'shared_wire_topology_and_budget_same_for_Aopt_and_C': True,
                'shared_resource_sets_identical_between_modes': True,
                'private_fixed_connections': 'Other original intra-system graphs retain full bit semantics; no change of protocol/pipeline/cache/computation',
                'inactive_selected_connections': 'Keep the unselected system electrically defined using direct M11/M12 original-source-to-sink bypass; do not share active passive components or leave sink gates floating',
                'idle_policy_pending_physical_implementation': 'Selected clock domains use original clock, other domains constant-clock stopped; reset and external inactive inputs explicitly defined, costs and checks mandatory',
                'shared_compute_claim': False, 'source_graph_SHA': {k: g['source_partition_sha256'] for k,g in graphs.items()},
                'functional_bit_graph_modified': False, 'original_handoff_still_unknown': True,
                'placement_proxy': {'enumerated_candidates': len(candidates), 'block_center_weighted_L1_um': cost, 'not_actual_wire_or_RC': True},
                'prewire_position_proxy':'Median endpoint Y across both modes AND Aopt/C, in a macro-outline-free corridor. PG/actual metal access and rules remain unverified.',
                'required_before_freeze': ['Six selected physical view sources and independent access/native checks', 'Record all inherited full-rule/STA failures',
                    'Actual lower-layer escape, PG/clock/private preconnections and finite shared wire implementation',
                    'Whole conductor/connectivity and exact lower-layer manifests', 'Actual active/idle infrastructure and costs',
                    'Same lower physical hashes for both complete functional modes', 'Actual M11/M12 access/routes/DRC/RC/STA and complete function checks'],
                'not_claimed': ['common base physically completed', 'system function implemented', 'M1-M10 frozen', 'full DRC/STA/electrical qualification', 'area benefit']}
    assert contract['original_signal_pins'] == 24767
    dump(out/'preparation_contract.json', contract)
    dump(out/'artifact_index.json', {p.name: {'sha256': sha(p), 'bytes': p.stat().st_size} for p in out.iterdir() if p.is_file()})
    print('COMMON_BASE_PREPARATION_ONLY', len(placements), 'instances;', 24767, 'pins;', 256, 'shared passive resources; NOT FROZEN')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    prepare(a.root, a.out)
