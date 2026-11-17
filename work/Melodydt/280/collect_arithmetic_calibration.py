"""Verify small arithmetic receipts and index sampled energy, without model totals."""
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def collect(root):
    specifications = []
    models = ('llama', 'granite', 'qwen3', 'falcon', 'qwen35', 'phi', 'gemma')
    for model, job in zip(models, (38830436, 38830711, 38830712, 38831450, 38831451, 38831452, 38831453)):
        specifications.append((model, 'rms_e32', root/'rms-e32-power-01'/('power-%s' % job)))
    for model, pair in zip(models, ((38828633,38828634),(38828998,38828999),(38829008,38829009),
                                   (38829006,38829007),(38829004,38829005),(38829000,38829001),(38829002,38829003))):
        for job in pair:
            specifications.append((model, 'rms_n', root/'common-arithmetic-n-01'/('n-%s' % job)))
    for kind, bundle, job in (('softmax',1,38831680),('rope',1,38831681),('scan',2,38831748),('apply',2,38831749),
                              ('scan',2,38831838),('apply',2,38831839)):
        specifications.append(('mixed',kind,root/('public-operator-power-%02d'%bundle)/('operator-%s'%job)))
    records=[]
    for model,kind,path in specifications:
        data=json.loads((path/'calibration.json').read_text())
        subprocess.run(['sha256sum','--quiet','-c','results.sha256'],cwd=path,check=True)
        if data['wire_parasitics_loaded'] or data['timing_signoff']:
            raise ValueError('unexpected physical scope')
        if not data['samples'] or data.get('synthetic',False):
            raise ValueError('missing real samples')
        groups=defaultdict(list)
        for i,sample in enumerate(data['samples']):
            p=path/('sample-%03d'%i)
            if json.loads((p/'receipt.json').read_text())!=sample:
                raise ValueError('sample differs from receipt')
            for key,name in (('vectors_sha256','vectors.txt'),('input_sha256','vectors.txt'),
                             ('rtl_log_sha256','rtl.log'),('run_log_sha256','run.log')):
                if key in sample and digest(p/name)!=sample[key]:
                    raise ValueError('sample input/log changed')
            if 'capture_sha256' in sample and digest(Path(sample['capture']))!=sample['capture_sha256']:
                raise ValueError('captured operands changed')
            if kind=='rms_n' and not sample['rtl_factor_equal']:
                raise ValueError('N factor mismatch')
            powers=sample.get('components',{'core':{'power':sample.get('power')}})
            for component in powers.values():
                for state,activity in component['power'].items():
                    if activity.get('annotated',activity.get('annotation_bits',0))<=0:
                        raise ValueError('unannotated power')
            if sample['incremental_nj']<0:
                raise ValueError('negative increment')
            signature=sample['signature']
            groups[(sample.get('capture',''),signature)].append(sample)
        rows=[]
        for (capture,signature),samples in sorted(groups.items()):
            energies=[s['incremental_nj'] for s in samples]
            rows.append(dict(capture=capture,signature=signature,samples=len(samples),minimum_nj=min(energies),
                             maximum_nj=max(energies),mean_nj=sum(energies)/len(energies),
                             windows_ps=sorted(set(s['window_ps'] for s in samples))))
        records.append(dict(model=model,kind=kind,result=str(path/'calibration.json'),
                            result_sha256=digest(path/'calibration.json'),manifest_sha256=digest(path/'results.sha256'),
                            samples=len(data['samples']),groups=rows,excluded_samples=data.get('excluded_samples',[]),
                            source_commit=(path.parent/'source-commit.txt').read_text().strip(),
                            scope=data['scope']))
    return dict(created_utc=datetime.now(timezone.utc).isoformat(),passed=True,
                scope='Sampled incremental arithmetic energy only; not full model power or corrected latency',
                estimator='RTL boundary VCD propagation in mapped Nangate45 typical cells, active minus equal-length idle',
                system_sram_bits=512,nominal_clock_mhz=300,wire_parasitics_loaded=False,timing_signoff=False,
                non_additive=['rms_e32 overlaps provider in apply','rope wrapper and provider are already summed'],
                remaining=['all-call workload weighting','SRAM/wait and idle residency','TLM/RTL schedule reconciliation',
                           'large RMS apply cross-bank or chunked staging','model-specific GELU/router/recurrent arithmetic'],
                records=records)


if __name__=='__main__':
    result=collect(Path(sys.argv[1]));Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n')
    print('ARITHMETIC_CALIBRATION_INDEX_PASS',len(result['records']),sum(r['samples'] for r in result['records']))
