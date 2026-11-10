"""Pure JSON postprocessing; never runs an EDA tool or predicts token/s."""
import argparse
import hashlib
import json
from pathlib import Path

MACRO_AREA_MM2 = 0.092462050025


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
                grouped.setdefault(key, []).append(dict(reset_mode=run['reset_mode'], seed=run['seed'], **measure))
        result['components'][name] = dict(passed=component['passed'], scenarios=grouped,
            throughput=[dict(reset_mode=run['reset_mode'], seed=run['seed'], **run['throughput'])
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
        old = modules['block_feed_s16k_sram']['standard_cell_area_um2']
        new = modules['block_feed_s16k_1r1w']['standard_cell_area_um2']
        shared = modules['shared_a_pool32']['standard_cell_area_um2']
        result['area']['new_module_standard_cell_delta_um2'] = shared + 2*(new-old)
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
