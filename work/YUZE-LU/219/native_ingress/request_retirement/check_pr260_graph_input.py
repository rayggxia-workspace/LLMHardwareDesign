"""Verify a graph-compiled deployment against the pinned PR 260 input readers."""
import argparse
import importlib.util
import json
from pathlib import Path

from publish_native_request_handoff import hash_file, read, require


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(program, memory, phases_path, pr260, dram_library, dram_config, output):
    audit = load_module(pr260 / 'native_rtl_retirements.py', 'pr260_rtl')
    tlm = load_module(pr260 / 'run_native_tlm_cases.py', 'pr260_tlm')
    phases = read(phases_path)
    deployment = hash_file(program / 'proof.sha256')
    require(phases['request_sha256'] == deployment, 'phase bindings name a different graph program')
    evidence = audit.program_binding(program, deployment, phases['phases'])
    require(evidence['expected_pages'] == phases['total_pages'], 'PR 260 page coverage differs')
    with (program / 'mother-pages.tsv').open() as mother, (program / 'mother-targets.tsv').open() as targets:
        rows = audit.program_pages(mother, targets)
        total = 0
        for binding in phases['phases']:
            for index in range(binding['pages']):
                row = next(rows, None)
                expected = binding['step'], index, binding['first_generation'] + index
                require(row is not None and row[:3] == expected, 'PR 260 page generation differs')
                total += 1
        require(next(rows, None) is None and total == evidence['expected_pages'], 'unexpected program pages')
    bad = [dict(row) for row in phases['phases']]
    bad[-1]['graph_sha256'] = '0' * 64
    try:
        audit.program_binding(program, deployment, bad)
    except ValueError as e:
        require('different phase graphs' in str(e), 'wrong graph rejected for unrelated reason')
    else:
        raise ValueError('PR 260 accepted a different phase graph')

    memory_seal = read(memory.parent / 'memory-binding.json')
    require(memory_seal['write_binding']['package_proof_sha256'] == deployment
            and memory_seal['write_binding']['write_table_sha256'] == hash_file(program / 'ddr-writes.tsv')
            and memory.is_file() and dram_library.is_file() and dram_config.is_file(),
            'PR 260 DDR setup names a different deployment or lacks an asset')
    manifest = dict(inputs=dict(program=str(program.resolve()), memory=str(memory.resolve()),
                                dram_library=str(dram_library.resolve()), dram_config=str(dram_config.resolve()),
                                deployment_sha256=deployment),
                    cases={'request-128': dict(mode='request', sram_port_bits=128,
                                               dma_fabric_budget=True, kv_read_window=8)})
    output.mkdir()
    case_path = output / 'pr260-tlm-cases.json'
    case_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
    name, _, replay, _ = next(tlm.commands(case_path.resolve(), output.resolve()))
    require(replay[3] == str(program.resolve()) and replay[8] == deployment,
            'PR 260 command changed the program or proof')
    evidence.update(tlm_case=name, launch_contract_checked=True, actual_execution=False,
                    phase_bindings_sha256=hash_file(phases_path),
                    rtl_reader_sha256=hash_file(pr260 / 'native_rtl_retirements.py'),
                    tlm_launcher_sha256=hash_file(pr260 / 'run_native_tlm_cases.py'),
                    graph_mismatch_rejected=True, memory_binding_sha256=hash_file(memory.parent / 'memory-binding.json'))
    (output / 'pr260-input-proof.json').write_text(json.dumps(evidence, sort_keys=True, indent=2) + '\n')
    print(json.dumps(evidence, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('program', 'memory', 'phases', 'pr260', 'dram_library', 'dram_config', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    verify(args.program, args.memory, args.phases, args.pr260, args.dram_library, args.dram_config, args.output)


if __name__ == '__main__':
    main()
