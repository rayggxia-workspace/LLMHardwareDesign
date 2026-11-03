"""Independent H1 static probes. No HDL/numerical/physical execution.

Imports the current checker without calling its file-writing check_all().
Writes only a new review JSON; refuses to overwrite an earlier audit attempt.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf8'))


def sequential(program):
    # The two insertion probes use G1/A-only without branch targets.
    for pc, ins in enumerate(program['instructions']):
        ins['next'] = 0 if ins['op'] == 'HALT' else pc + 1


def record(op, a=0, imm=0):
    return dict(op=op, flags=0, a=a, b=0, c=0, imm=imm, next=0, aux=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[5])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    review = (root / 'work/Melodydt/151/h1/review').resolve()
    dest = args.output.resolve()
    if review not in dest.parents or dest.exists():
        raise ValueError('output must be a new file inside this package review directory')
    source = root / 'scripts/check_h1_graphs.py'
    source_bytes = source.read_bytes()
    spec = importlib.util.spec_from_file_location('h1_independent_target', str(source))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    data = root / 'project/experiments/hybrid_control/h1/v0_1'
    target = load(data / 'target.json')
    graphs = [load(p) for p in sorted((data / 'graphs').glob('*.json'))]
    assert len(graphs) == 3
    normals = []
    expected = [(48, 1184), (88, 2016), (81, 1808)]
    for graph, (records, image_bytes) in zip(graphs, expected):
        program = mod.compile_graph(graph, target)
        binary = mod.encode(program)
        metadata, image = mod.metadata(graph, program)
        assert len(program['instructions']) == records and len(binary) == 16 * records
        assert len(image) == metadata['product_image_bytes'] == image_bytes
        header = struct.unpack('<8sHHHHIIII32s', image[:64])
        assert header[:5] == (b'H1IRv001', records, len(program['objects']), len(program['parameters']), 6)
        assert header[5:9] == (64, 64 + len(binary), 64 + len(binary) + 64 * len(program['objects']),
                               64 + len(binary) + 64 * len(program['objects']) + 32 * len(program['parameters']))
        assert header[9] == hashlib.sha256(mod.canonical(graph)).digest()
        assert image[64:64 + len(binary)] == binary
        for pc, ins in enumerate(program['instructions']):
            decoded = struct.unpack('<BBHHHIHH', binary[16 * pc:16 * (pc + 1)])
            assert decoded == tuple([mod.OPS[ins['op']]] + [ins[k] for k in ['flags', 'a', 'b', 'c', 'imm', 'next', 'aux']])
        scenarios = []
        for predicate in ([False, True] if graph['output']['kind'] == 'select' else [False]):
            run = mod.execute(graph, target, program, predicate)
            expected_calls = sum(1 if c['kernel'] == 'A2' else 2 for c in graph['calls'])
            assert run['native_calls'] == expected_calls
            assert run['counts']['EXPORT'] == run['counts']['WAIT_HOST_STORED'] == run['counts']['CLOSE_OUTPUT'] == 1
            assert run['trace'][-1]['live'] == []
            scenarios.append({k: v for k, v in run.items() if k != 'trace'})
        normals.append(dict(graph=graph['name'], records=records, image_bytes=image_bytes,
                            image_sha256=sha(image), scenarios=scenarios))
    probes = []

    def probe(name, expected_code, graph=None, target_change=None, program_change=None, predicate=False):
        g, t = copy.deepcopy(graph or graphs[0]), copy.deepcopy(target)
        if target_change:
            target_change(t)
        result = dict(case=name, expected_reject=expected_code)
        try:
            program = mod.compile_graph(g, t)
            if program_change:
                program_change(program)
            run = mod.execute(g, t, program, predicate)
        except mod.Reject as exc:
            result.update(observed=str(exc), passed=str(exc) == expected_code)
        except Exception as exc:
            result.update(observed=type(exc).__name__ + ':' + str(exc), passed=False)
        else:
            result.update(observed='ACCEPTED', passed=False,
                          accepted_summary={k: v for k, v in run.items() if k != 'trace'})
        probes.append(result)

    probe('edge_bytes_inconsistent_with_slots', 'E_EDGE_STORE_BUDGET', target_change=lambda t: t.update(edge_store_bytes=4096))
    probe('edge_store_has_no_owner', 'E_PORT_PROFILE', target_change=lambda t: t.update(edge_store_port_owners=0))
    probe('target_native_S_missing', 'E_NATIVE_RESOURCE_BUDGET', target_change=lambda t: t['native_leaves'].update(S=0))
    probe('target_declares_64bit_records', 'E_RECORD_WIDTH', target_change=lambda t: t.update(record_bits=64))
    one_a = copy.deepcopy(graphs[0])
    one_a['calls'] = one_a['calls'][:1]
    one_a['output'] = dict(kind='direct', object=one_a['calls'][0]['output'])

    def relocate_pending_dest(p):
        ins = p['instructions']
        at = next(i for i, x in enumerate(ins) if x['op'] == 'STORE') + 1
        obj = ins[at - 1]['b']
        ins[at:at] = [record('FREE', obj), record('ALLOC', obj)]
        sequential(p)

    probe('free_pending_destination_then_relocate', 'E_FREE_INFLIGHT', graph=one_a, program_change=relocate_pending_dest)

    def duplicate_export(p):
        ins = p['instructions']
        at = next(i for i, x in enumerate(ins) if x['op'] == 'CLOSE_OUTPUT')
        obj = ins[at]['a']
        ins[at:at] = [record('EXPORT', obj, 256), record('WAIT_HOST_STORED', obj)]
        sequential(p)

    probe('same_output_exported_twice', 'E_DUPLICATE_EXPORT', program_change=duplicate_export)
    probe('IF_true_target_out_of_range', 'E_PC_RANGE', graph=graphs[2], predicate=True,
          program_change=lambda p: next(x for x in p['instructions'] if x['op'] == 'IF').update(b=65535))
    probe('IF_false_target_out_of_range', 'E_PC_RANGE', graph=graphs[2], predicate=False,
          program_change=lambda p: next(x for x in p['instructions'] if x['op'] == 'IF').update(c=65535))

    def close_without_ack(p):
        index = next(i for i, x in enumerate(p['instructions']) if x['op'] == 'WAIT_HOST_STORED')
        obj = p['instructions'][index]['a']
        p['instructions'][index] = record('CLOSE_OUTPUT', obj)
        sequential(p)

    probe('close_output_before_host_ack', 'E_OUTPUT_CLOSE_BEFORE_ACK', program_change=close_without_ack)
    late_p = copy.deepcopy(graphs[2])
    late_p['output']['capture'] = 'AFTER_FIRST_BRANCH'
    probe('predicate_capture_after_acceptance', 'E_PREDICATE_LIFETIME', graph=late_p)

    def free_before_second_consumer(p):
        # left F2 row1 has been stored; right F2 has not consumed the fork source.
        at = next(i for i, x in enumerate(p['instructions'])
                  if x['op'] == 'PARAM' and x['b'] == 2 and x['c'] == 1)
        p['instructions'][at] = record('FREE', p['objects'].index('a'))
        sequential(p)
        # G3 targets must remain legal after changing an instruction without insertion.

    probe('fork_source_free_after_only_left_consumer', 'E_FREE_BEFORE_CONSUMER_ACK',
          graph=graphs[2], program_change=free_before_second_consumer)
    assert source.read_bytes() == source_bytes, 'checker changed during the audit; use a fresh attempt'
    result = dict(status='PASS_INDEPENDENT_H1_STATIC_REVIEW' if all(p['passed'] for p in probes) else 'FINDINGS_OPEN',
                  checker_sha256=sha(source_bytes), audit_sha256=sha(Path(__file__).read_bytes()),
                  python=sys.version, normal_graphs=normals, independent_probes=probes,
                  graph_scenarios=4, physical_or_RTL_execution=False,
                  scope='Three fixtures and stated malformed controls only; no all-graph, numerical, RTL, quality or physical proof.',
                  historical_findings=[
                      dict(source_sha256='88a4d535b0b8d14d09d56d1701dfbfd671af49f8f14e12b678d3be95a8edf87b',
                           issue='pending destination FREE/ALLOC relocated slot1 to slot0 and was accepted'),
                      dict(source_sha256='88a4d535b0b8d14d09d56d1701dfbfd671af49f8f14e12b678d3be95a8edf87b',
                           issue='contradictory target capacity/owner/native-leaf/record-width fields accepted'),
                      dict(source_sha256='013d4ce71f3f86c2bda7c40ac326a96a0b770d9086b5684f628fd5cf8d05f2be',
                           issue='duplicate EXPORT+WAIT_HOST_STORED accepted the same 256word output twice')])
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf8'))
    print(json.dumps(dict(status=result['status'], source=result['checker_sha256'],
                          probes=len(probes), failures=[p['case'] for p in probes if not p['passed']], output=str(dest))))
    return 0 if result['status'].startswith('PASS_') else 2


if __name__ == '__main__':
    raise SystemExit(main())
