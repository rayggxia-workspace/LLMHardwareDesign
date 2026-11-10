"""Pure JSON postprocessing; never runs an EDA tool or predicts token/s."""
import argparse
import hashlib
import json
from pathlib import Path

MACRO_AREA_MM2 = 0.092462050025


def bind_measurement(run, measure):
    """Retain run identity without silently overwriting conflicting receipts."""
    identity = dict(reset_mode=run['reset_mode'], seed=run['seed'],
                    variant=run.get('variant', 'default'))
    for key in identity.keys() & measure.keys():
        if type(identity[key]) is not type(measure[key]) or identity[key] != measure[key]:
            raise ValueError('measurement/run identity mismatch: ' + key)
    merged = dict(identity)
    merged.update(measure)
    return merged


def analyze(path):
    report = json.loads(path.read_text(encoding='utf-8'))
    result = dict(result_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  source_commit=report['source_commit'], passed=report['passed'],
                  functional_passed=report['functional_passed'], job=report['job'], node=report['node'],
                  scope=report['scope'], components={}, area={})
    for name, component in report['components'].items():
        grouped = {}
        for run in component['runs']:
            for index, measure in enumerate(run['measurements']):
                key = run.get('variant', 'default') + ':' + str(measure.get('scenario', measure.get('case', index)))
                grouped.setdefault(key, []).append(bind_measurement(run, measure))
        result['components'][name] = dict(passed=component['passed'], scenarios=grouped,
            throughput=[bind_measurement(run, run['throughput'])
                        for run in component['runs'] if 'throughput' in run])
    area = report['mapped_area']
    result['area']['mapped'] = area
    result['area']['macro_budget'] = dict(
        basis='Conditional copy of the verified existing 4KiB 1RW macro footprint; excludes interconnect, standard cells and physical implementation.',
        bank_mm2=MACRO_AREA_MM2,
        baseline=dict(P_count=2, P_physical_KiB_each=16, U_KiB=16, total_KiB=48,
                      banks=12, macro_mm2=12*MACRO_AREA_MM2),
        candidate=dict(P_count=2, P_logical_KiB_each=16, P_physical_KiB_each=32,
                       U_KiB=16, shared_KiB=32, total_physical_KiB=112,
                       banks=28, macro_mm2=28*MACRO_AREA_MM2),
        delta=dict(physical_KiB=64, banks=16, macro_mm2=16*MACRO_AREA_MM2))
    if area.get('status') == 'passed':
        modules = area['modules']
        new = modules['block_feed_s16k_1r1w']['standard_cell_area_um2']
        shared = modules['shared_a_pool32']['standard_cell_area_um2']
        candidate_config = modules['block_feed_s16k_1r1w'].get('configuration', {})
        baseline = modules.get('block_feed_s16k_bank_rw')
        if baseline is not None and baseline.get('configuration', {}).get('ECHO_WRITE_DATA') == 0 and candidate_config.get('ECHO_WRITE_DATA') == 0:
            old = baseline['standard_cell_area_um2']
            result['area']['new_module_standard_cell_delta_um2'] = shared + 2*(new-old)
            result['area']['standard_cell_delta_baseline'] = dict(module='block_feed_s16k_bank_rw', configuration=dict(ECHO_WRITE_DATA=0))
            result['area']['production_baseline_comparison'] = dict(status='available', local_backend_delta_each_um2=new-old)
        else:
            result['area']['production_baseline_comparison'] = dict(status='not_available', reason='Requires actual bank_rw baseline and candidate both mapped with explicit ECHO_WRITE_DATA=0; historical default-echo/plain-only mapping is not that comparison.')
        plain = modules.get('block_feed_s16k_sram')
        if plain is not None:
            result['area']['plain_reference'] = dict(
                module='block_feed_s16k_sram', configuration=plain.get('configuration', 'not_recorded'),
                candidate_configuration=candidate_config or 'not_recorded',
                delta_um2=shared+2*(new-plain['standard_cell_area_um2']),
                scope='Reference only; this is not the R4 P local bank_rw baseline.')
        result['area']['standard_cell_delta_scope'] = 'Shared pool plus two local-memory backend replacements only; excludes any modified P integration logic.'
    result['token_s'] = dict(status='not_evaluated', reason='Native RTL microbench cycles do not establish the legacy S32/S96 model throughput. A separately validated calibration is required.')
    return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--result', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True); args = parser.parse_args()
    result = analyze(args.result)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(passed=result['passed'], output=str(args.out), source_commit=result['source_commit'])))


if __name__ == '__main__':
    main()
