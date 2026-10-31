"""Compare sealed original and derived native markers without changing rules."""
from collections import Counter
from decimal import Decimal
import hashlib,json,re
from pathlib import Path


def main():
    folder=Path(__file__).resolve().parent
    original=folder.parent/'v-physical-localization-557/block-v1-20261030-557/tasks/revision300-v-spacing-localize/revision300-v-physical-localization.json'
    derived=folder/'block-v1-20261030-560/tasks/revision300-v-marker-probe/explicit-native-drc.rpt'
    source=json.loads(original.read_text(encoding='utf-8'));text=derived.read_text(encoding='utf-8')
    pattern=(r'violation type: Metal Spacing\n\s*srcs: net:([^\n]+)\n'
             r'\s*bbox = \(([-\d.]+), ([-\d.]+)\) - '
             r'\(([-\d.]+), ([-\d.]+)\) on Layer (metal\d+)')
    normalize=lambda name,layer,box:(name.replace('\\',''),layer,*box)
    before=Counter(normalize(m['marker']['net'],m['marker']['layer'],m['marker']['bbox_dbu'])for m in source['markers'])
    after=Counter()
    for match in re.finditer(pattern,text):
        name,a,b,c,d,layer=match.groups()
        values=[Decimal(x)*2000 for x in (a,b,c,d)]
        assert all(x==int(x)for x in values)
        after[normalize(name,layer,list(map(int,values)))]+=1
    assert sum(before.values())==445
    assert sum(after.values())==text.count('violation type:')==440
    removed=before-after;added=after-before
    assert not added and sum(removed.values())==5
    indices=[i for i,row in enumerate(source['markers'])
             if normalize(row['marker']['net'],row['marker']['layer'],row['marker']['bbox_dbu'])in removed]
    result=dict(passed=True,original_count=445,derived_count=440,removed_count=5,added_count=0,
                removed_original_marker_indices=indices,
                original_json_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
                derived_native_report_sha256=hashlib.sha256(derived.read_bytes()).hexdigest(),
                helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                physical_qualified=False,
                scope='Marker comparison only.440 native spacing violations remain. Failed path-iterator RECT readback does not prove complete metal union equality.')
    (folder/'marker-difference.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps(result))


if __name__=='__main__':main()
