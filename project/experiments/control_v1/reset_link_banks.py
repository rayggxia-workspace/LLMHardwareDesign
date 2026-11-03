"""Partition Link8 reset loads across fixed, registered-equivalent outputs.

The reset53 native block owns one shared state bit and53 independent output
drivers. This code assigns passive wires; it creates no upper-layer logic.
"""
import collections


def assign(module, rows):
    cell = module['cells']['reset_distribution']
    assert cell['type'] == 'control_reset_distribution_r53'
    outputs = cell['connections']['reset_out']
    assert len(outputs) == 53 and len(set(outputs)) == 53
    groups = collections.defaultdict(list)
    for row in rows:
        groups[row['source_instance']].append(row)
    banks = []
    for source in sorted(groups):
        group = groups[source]
        for offset in range(0, len(group), 16):
            index = 28 + len(banks)
            assert index < 53
            chunk = group[offset:offset+16]
            old = module['cells'][source]['connections']['reset']
            assert len(old) == 1 and old[0] in outputs[:28]
            for row in chunk:
                link = module['cells'][row['instance']]
                assert link['connections']['reset'] == old and row['reset_bit'] == old[0]
                link['connections']['reset'] = [outputs[index]]
                row.update(source_reset_bit=old[0], reset_bit=outputs[index], reset_bank_output=index)
            banks.append(dict(output=index, bit=outputs[index], source_instance=source,
                              original_source_reset_bit=old[0],
                              link_instances=[r['instance'] for r in chunk]))
    assert len(rows) == 316 and len(banks) == 25
    return dict(owner='reset_distribution M1-M10', registered_state_bits=1,
                extra_state_bits=0, original_leaf_branches=28, independent_link_branches=25,
                max_link_loads_per_branch=16, banks=banks,
                contract='All53 outputs share one reset state and one-clock latency; no new payload or reset pipeline stage. Actual reset53 final-cell/formal/physical gates are mandatory.')


def validate(graph, proof):
    assert proof['owner'] == 'reset_distribution M1-M10'
    assert proof['registered_state_bits'] == 1 and proof['extra_state_bits'] == 0
    assert proof['original_leaf_branches'] == 28 and proof['independent_link_branches'] == 25
    assert proof['max_link_loads_per_branch'] == 16
    rows = graph['boundary_links']['links']
    links = {r['instance']: r for r in rows}
    banks = proof['banks']
    assert len(banks) == 25 and {b['output'] for b in banks} == set(range(28, 53))
    assert len({b['bit'] for b in banks}) == 25
    assigned = []
    padding=proof.get('unused_lane_padding')
    assert padding in (None,'local-reset-unused-lanes/1')
    for bank in banks:
        names = bank['link_instances']
        assert 1 <= len(names) <= 16 and len(names) == len(set(names))
        connection = graph['connections'][str(bank['bit'])]
        assert connection['driver'] == dict(instance='reset_distribution',
                                           pin='reset_out['+str(bank['output'])+']', direction='output')
        expected={(n,'reset','input')for n in names}
        for name in names:
            row = links[name]
            assert row['source_instance'] == bank['source_instance']
            assert row['reset_bit'] == bank['bit'] and row['reset_bank_output'] == bank['output']
            assert row['source_reset_bit'] == bank['original_source_reset_bit']
            if padding:
                n=len(row['lanes']);assert 1<=n<=8
                assert [r['lane']for r in row['lanes']]==list(range(n))
                assert row['padded_input_lanes']==8-n and row['padding_input_bit']==bank['bit']
                unused=row['unused_output_bits'];assert len(unused)==len(set(unused))==8-n
                assert all(isinstance(b,int)and str(b)not in graph['connections']for b in unused)
                expected.update((name,'in_data['+str(i)+']','input')for i in range(n,8))
        actual=[(e['instance'],e['pin'],e['direction'])for e in connection['sinks']]
        assert len(actual)==len(set(actual))and set(actual)==expected
        assigned.extend(names)
    assert len(assigned) == 316 and len(set(assigned)) == 316 and set(assigned) == set(links)
