"""Validate accounting invariants independently of the estimator's summation."""
from hashlib import sha256
import json
from math import isclose,isfinite
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
for model in sys.argv[1:] or ('qwen3','llama','granite','phi','gemma','qwen35','falcon'):
    p=HERE/(model+'_tlm_power_v3_arithmetic.json');d=json.loads(p.read_bytes())
    base=HERE/(model+'_tlm_power_v2_no_wire.json');b=json.loads(base.read_bytes())
    assert sha256(base.read_bytes()).hexdigest()==d['baseline_sha256']
    cp=HERE/'arithmetic-model-counts'/(model+'.json');counts=json.loads(cp.read_bytes())
    assert sha256(cp.read_bytes()).hexdigest()==d['counts_sha256']
    for name,h in d['calibration_sha256'].items():assert sha256((HERE/'arithmetic-calibration-results'/name).read_bytes()).hexdigest()==h
    assert set(d['windows'])=={'prefill','first_token','decode'}
    for window,w in d['windows'].items():
        old=b['windows'][window]
        for k in ('elapsed_ps','tokens','tokens_per_second'):assert w[k]==old[k]
        assert w['ddr']==old['components']['ddr_devices']
        components=w['arithmetic_components'];assert not any(k=='rms_e32' for k in components)
        phase=counts['phases']['prefill' if window=='prefill' else 'decode']
        expected={k:v for k,v in phase['operator_counts'].items() if k.split(':')[0]==window and phase['operator_shapes'][k]['kind'] not in ('rope','rope_native','softmax')}
        assert {row['signature']:row['calls'] for row in w['operation_audit']}==expected
        for item in list(components.values())+[w[k] for k in ('arithmetic_increment','estimated_on_chip','estimated_on_chip_plus_ddr')]:
            for values in item.values():assert len(values)==2 and all(isfinite(v) for v in values) and 0<=values[0]<=values[1]
            for e in (0,1):
                nj=item['energy_nj_per_window'][e]
                assert isclose(item['energy_mj_per_token'][e],nj/1e6/w['tokens'],rel_tol=1e-12,abs_tol=1e-12)
                assert isclose(item['average_power_w'][e],nj*1000/w['elapsed_ps'],rel_tol=1e-12,abs_tol=1e-12)
        for e in (0,1):
            extra=sum(x['energy_nj_per_window'][e] for x in components.values())
            assert isclose(extra,w['arithmetic_increment']['energy_nj_per_window'][e],rel_tol=1e-12)
            chip=w['estimated_on_chip']['energy_nj_per_window'][e];total=w['estimated_on_chip_plus_ddr']['energy_nj_per_window'][e]
            assert isclose(chip,old['covered_on_chip_subtotal']['energy_nj_per_window'][e]+extra,rel_tol=1e-12)
            assert isclose(total,chip+w['ddr']['energy_nj_per_window'][e],rel_tol=1e-12)
    print('ARITHMETIC_ACCOUNTING_PASS',model)
