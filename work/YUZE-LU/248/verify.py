"""Offline integrity, baseline, RTL receipts, and metadata sanity checks only."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
sys.path.insert(0,str(REPO/'project/experiments/stream_quant_synthesis'))
from collect import verify
import numeric
import planner


def main():
    verified=0;runs=sorted(ROOT.glob('run[0-9][0-9]'))
    for folder in runs:verified+=verify(folder)
    assert len(runs)==13
    result=json.loads((ROOT/'summary.json').read_text())
    from report import contents
    audit=json.loads(contents(ROOT/'run13')['results/metadata-audit.json'])
    receipt12=json.loads((ROOT/'run12/receipt.json').read_text())
    assert audit['passed'] and len(audit['cases'])==2
    assert audit['prior_result_sha256']==receipt12['index']['files']['results/result.json']['sha256']
    assert all(x['exact_prior_RESULT_except_labels'] for x in audit['cases'])
    assert result['model_cases']==65 and result['exact_baseline_checks']==12
    assert result['native_full_model_tokens_s'] is None and result['energy_J_per_token'] is None
    for name,digest in result['reemitted_operand_requirements'].items():
        path=ROOT/name;assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
        bundle=json.loads(path.read_text())
        assert not bundle['deployment_qualified'] and not bundle['complete_static_net_set']
        for net in bundle['connections']:
            assert net['physical_pin_binding'] is None
            if net['driver'].startswith('DMA.'):assert net['data_width']==512
    print(json.dumps(dict(passed=True,run_packages=len(runs),embedded_files_verified=verified,metadata_audit_cases=2,
                          numeric=numeric.check_contract(),DP=planner.test())))


if __name__=='__main__':main()
