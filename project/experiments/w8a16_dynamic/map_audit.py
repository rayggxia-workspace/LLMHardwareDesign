"""Audit recovered mapping records; do not run EDA locally."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
from recover import receipts

LIB_SHA='8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1'


def audit(run):
    recovery,files=receipts(run)
    assert 'FAILED' not in recovery['sacct'] and 'COMPLETED' in recovery['sacct']
    source=(run/'source.tar.gz').read_bytes()
    assert hashlib.sha256(source).hexdigest()==recovery['source_archive_sha256']
    with tarfile.open(fileobj=io.BytesIO(source),mode='r:gz') as archive:
        sources={m.name:archive.extractfile(m).read() for m in archive if m.isfile()}
    for line in sources['source.sha256'].decode().splitlines():
        digest,path=line.split('  ',1);assert hashlib.sha256(sources[path]).hexdigest()==digest
    reports=[]
    for top in ('dynamic_s32_merge','dynamic_s32_packer','dynamic_s32_weight_source'):
        prefix='map-'+top+'/'
        row=json.loads(files[prefix+'receipt.json'])
        assert row['passed'] and not row['physical_qualified'] and row['added_sram_bytes']==0
        assert row['liberty_sha256']==LIB_SHA and row['hierarchical_memories']=={}
        assert row['mapped_dff_count']==sum(v for n,v in row['cell_counts'].items() if n.startswith(('DFF','SDFF')))
        assert all(not n.startswith('$') for n in row['cell_counts'])
        for path,digest in row['source_sha256'].items():
            assert hashlib.sha256(sources['source/project/rtl/w8a16_v1/'+path]).hexdigest()==digest
        assert hashlib.sha256(files[prefix+'consumed.scl']).hexdigest()==row['consumed_scl_sha256']
        abc=json.loads(files[prefix+'abc-mapping.json'])
        assert abc['passed'] and abc['returncode']==0 and len(abc['affinity'])<=10
        if row['liberty_conversion_invoked']:
            assert json.loads(files[prefix+'abc-liberty-conversion.json'])['passed']
        log=files[prefix+'map.log'].decode()
        area=float(re.findall(r"Chip area for module '\\"+top+r"': ([\d.]+)",log)[-1])
        assert abs(area-row['mapped_area_um2'])<1e-5
        reports.append(row)
    return dict(passed=True,job=recovery['job'],source_commit=recovery['source_commit'],
                archive_sha256=recovery['archive_sha256'],reports=reports,
                total_independent_instances_area_um2=sum(r['mapped_area_um2'] for r in reports),
                qualification='Mapped LC-owned standard-cell components only. No hard physical boundary, placement/300MHz or integrated system proof.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True)
    args=parser.parse_args();result=audit(args.run)
    (args.run/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,job=result['job'],area_um2=result['total_independent_instances_area_um2'])))
