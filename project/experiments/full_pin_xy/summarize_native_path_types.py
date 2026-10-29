"""Classify actual OpenSTA text paths without relabelling removal as hold.

Reports contain a bounded number per group, not every path. Source worst-slack
text is replayed independently; this parser never infers a passing full check.
"""
from pathlib import Path
import gzip,hashlib,json,re


def raw(path):
    data=Path(path).read_bytes()
    return gzip.decompress(data) if str(path).endswith('.gz') else data


def summarize(folder):
    folder=Path(folder);receipt_raw=raw(folder/'execution.json.gz');q=json.loads(receipt_raw)
    assert q['native_returncode']==0 and q['all_sources_unchanged']
    assert all(q['source_worst_slacks_exactly_replayed'].values())
    result={'scope':'BOUNDED_ACTUAL_PATH_TYPE_DIAGNOSIS_NOT_ALL_PATH_ENUMERATION_OR_REPAIR',
      'case':q['case'],'source_kind':q['source_kind'],'source_receipt_sha256':hashlib.sha256(receipt_raw).hexdigest(),
      'full_qualification':False,'paths':[],'source_path_SHA256':{}}
    for kind,delay in [('setup','max'),('hold','min')]:
        name=kind+'_paths.txt';data=raw(folder/(name+'.gz'))
        assert hashlib.sha256(data).hexdigest()==q['files'][name]['sha256']
        result['source_path_SHA256'][name]=hashlib.sha256(data).hexdigest()
        subset=[]
        for block in re.split(r'(?=Startpoint:)',data.decode('utf-8')):
            if not block.startswith('Startpoint:'):continue
            slack=re.findall(r'([-\d.]+)\s+slack \((MET|VIOLATED)\)',block)
            assert len(slack)==1 and re.search(r'Path Type: (\w+)',block)[1]==delay
            check_type='UNCLASSIFIED_'+delay.upper()
            for phrase,label in [('library recovery time','RECOVERY'),('library removal time','REMOVAL'),('library setup time','SETUP'),('library hold time','HOLD')]:
                if phrase in block:check_type=label;break
            if check_type.startswith('UNCLASSIFIED') and 'output external delay' in block:
                check_type='OUTPUT_'+delay.upper()
            row={'delay_type':delay,'check_type':check_type,
              'path_group':re.search(r'Path Group: (.*)',block)[1],
              'startpoint':re.search(r'Startpoint: (.*)',block)[1],
              'endpoint':re.search(r'Endpoint: (.*)',block)[1],
              'slack_ns':float(slack[0][0]),'reported_status':slack[0][1]}
            subset.append(row)
        assert subset and min(r['slack_ns'] for r in subset)==q['source_'+kind+'_ns']
        result['paths']+=subset
    result['worst_observed_by_check_type']={t:min((r for r in result['paths'] if r['check_type']==t),key=lambda r:r['slack_ns']) for t in sorted({r['check_type'] for r in result['paths']})}
    result['interpretation']='Actual source report units ns. Grouped sample includes source global extrema, but a missing type is not proof of coverage or pass; original full check-type/constraint/parasitic reports remain authoritative.'
    return result
