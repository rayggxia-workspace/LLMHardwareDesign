"""Independent checks of measurements, not a reimplementation of model costs.

Reads versioned trace excerpts only. Does not simulate hardware locally.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / 'work/YUZE-LU/250/native-service'


def check():
    m = json.loads((EVIDENCE / 'measured-m-core.json').read_text())
    assert len(m['records']) == 18 and m['Slurm_job'] == 102118
    for trace in m['records']:
        for record, groups in [('5000', 1), ('5001', 8)]:
            rows = [r for r in trace['events'] if r[2] == record]
            response = next(r for r in rows if r[0] == 'RECORD')
            completion, accept, first_A, last_A, input_ACK = map(int, [response[1]] + response[4:8])
            assert [first_A-accept, last_A-accept, input_ACK-accept, completion-accept] == [1, 8, 9, 12]
            assert response[8:] == ['1', '0']
            assert len([r for r in rows if r[0] == 'RAW']) == groups
            assert len([r for r in rows if r[0] == 'RF']) == groups
            RF = [r for r in rows if r[0] == 'RF']
            assert [int(r[4]) for r in RF] == ([128] if groups == 1 else list(range(16, 129, 16)))
    a = json.loads((EVIDENCE / 'measured-a-copy.json').read_text())
    assert len(a['records']) == len(a['single_admitted_A_records']) == 18
    assert a['derived_single_admitted_A_is_measured']
    for trace in a['records']:
        assert trace['copy_first_request_to_last_ACK_inclusive'] == 130
        assert trace['A_aggregate_request_gap'] == 4 and trace['A_RTT'] == 2
        assert trace['first_A_terminal_cmd_delta'] == 126
    for trace in a['single_admitted_A_records']:
        assert len(trace['loads']) == 2
        for load in trace['loads']:
            assert load['terminal_taken_cycle']-load['command_accepted_cycle'] == 66
            assert load['command_to_terminal_cycles'] == 66 and not load['error']
    product = json.loads((EVIDENCE / 'measured-m-product.json').read_text())
    assert product['job'] == 102172 and len(product['records']) == 18
    for trace in product['records']:
        for record in ['5000', '5001', '5010', '5011']:
            responses = [row for row in trace['events'] if row[0] == 'RESPONSE' and row[4] == record and row[2] in {'3', '4'}]
            input_done = next(row for row in responses if row[2] == '3')
            result = next(row for row in responses if row[2] == '4')
            ticket = input_done[3]
            core = next(row for row in trace['events'] if row[0] == 'CORE_EXEC' and row[2] == ticket)
            assert int(input_done[1])-int(core[1]) == 11
            assert int(result[1])-int(core[1]) == (14 if record == '5010' else 16)
            assert int(result[6]) == (2 if record == '5010' else 4)
    quant = json.loads((ROOT / 'project/experiments/native_s_calibration/fixtures/quantizer-102168.json').read_text())
    assert quant['job'] == 102168 and quant['payload_register_bytes'] == 32 and quant['new_SRAM_bytes'] == 0
    for frame in quant['frames']:
        known = frame['known_producer_shift']
        assert len(frame['transactions']) == (48 if known else 80)
        assert frame['summary']['cmd_to_done'] == (60 if known else 95)
        assert all(t['response_offset']-t['request_offset'] == 2 for t in frame['transactions'])
    pipeline = json.loads((EVIDENCE / 'measured-m-pipeline3.json').read_text())
    assert pipeline['job'] == 102202 and len(pipeline['records']) == 18
    for trace in pipeline['records']:
        for record in ['5000', '5001', '5010', '5011']:
            responses = [row for row in trace['events'] if row[0] == 'RESPONSE' and row[4] == record and row[2] in {'3', '4'}]
            input_done = next(row for row in responses if row[2] == '3')
            result = next(row for row in responses if row[2] == '4')
            ticket = input_done[3]
            core = next(row for row in trace['events'] if row[0] == 'CORE_EXEC' and row[2] == ticket)
            assert int(input_done[1])-int(core[1]) == (19 if record == '5001' else 11)
            assert int(result[1])-int(core[1]) == (32 if record == '5001' else 16 if record == '5010' else 18)
            if record == '5001':
                A = [int(row[1])-int(core[1]) for row in trace['events'] if row[0] == 'A' and row[2] == record]
                assert A == [1, 2, 3, 4, 7, 10, 13, 16]
    II1 = json.loads((EVIDENCE / 'measured-m-rf-II1.json').read_text())
    assert II1['job'] == 102228 and len(II1['records']) == 18
    for trace in II1['records']:
        cores = {}
        for record in ['5000', '5001', '5010', '5011', '5020', '5021']:
            responses = [row for row in trace['events'] if row[0] == 'RESPONSE' and row[4] == record and row[2] in {'3', '4'}]
            input_done = next(row for row in responses if row[2] == '3')
            result = next(row for row in responses if row[2] == '4')
            ticket = input_done[3]
            core = next(row for row in trace['events'] if row[0] == 'CORE_EXEC' and row[2] == ticket)
            cores[record] = int(core[1])
            assert int(input_done[1])-int(core[1]) == 11
            assert int(result[1])-int(core[1]) == (16 if record in ('5010', '5020') else 18)
            if record in ('5001', '5020', '5021'):
                A = [int(row[1])-int(core[1]) for row in trace['events'] if row[0] == 'A' and row[2] == record]
                assert A == list(range(1, 9))
        assert cores['5021']-cores['5020'] == 21
    return dict(passed=True, M_measured_traces=18, ordinary_RF_groups=1,
                head_RF_groups=8, A_copy_measured_traces=18, single_A_measured_loads=36,
                M_product_measured_traces=18, M_pipeline3_measured_traces=18, M_RFII1_measured_traces=18, quantizer_native_profiles=2,
                whole_model_numeric_qualification=False)


if __name__ == '__main__':
    print(json.dumps(check()))
