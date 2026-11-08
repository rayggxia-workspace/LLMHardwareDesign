"""Strictly gate all declared distributed-node/Miller timing variants."""
import argparse
import json
from pathlib import Path
import re
from native_inventory import sha


def collect(out):
    rows=[]
    drivers=set()
    for line in (out/'upper-owners.tsv').read_text().splitlines():
        net,direction,instance,master,pin=line.split('\t')
        if direction=='OUTPUT':drivers.add(instance+'/'+pin)
    assert drivers,'actual upper-driver inventory absent'
    for projection in ('distributed','driver','farthest_sink'):
        for scale in range(3):
            name=projection+'-coupling-'+str(scale);path=out/(name+'-counts.tsv')
            log=(out/(name+'.log')).read_text()
            assert not re.search(r'\[ERROR |STA-0366|STA-0450|STA-0471|STA-0432',log),'invalid timing annotations'
            annotation=(out/(name+'-annotation.rpt')).read_text()
            # One-space entries are wholly/partially unannotated drivers;
            # two-space entries underneath are missing loads. All new nets
            # must have complete parasitic annotation, including native ends.
            missing={s.strip().replace('\\','') for s in annotation.splitlines()
                     if re.match(r'^ \S',s)}
            assert not drivers.intersection(missing),('upper driver lacks full parasitics',sorted(drivers.intersection(missing)))
            counts={k:int(v) for k,v in (line.split() for line in path.read_text().splitlines())}
            assert set(counts)=={'setup','hold','capacitance','slew','fanout'}
            summary=out/(name+'-summary.rpt')
            slacks={k:float(v) for k,v in re.findall(r'worst slack (max|min) (-?[\d.]+)',summary.read_text())}
            rows.append({'variant':name,'violations':counts,'slack_ns':slacks,
                'spef_sha256':sha(out/(name+'.spef')),'report_sha256':sha(summary),
                'passed':set(slacks)=={'max','min'} and min(slacks.values())>=0 and not any(counts.values())})
    result={'passed':all(r['passed'] for r in rows),'variants':rows,
            'scope':'actual flat native circuit and original TT300MHz constraints; fresh joint-native-context upper RC; research stack'}
    (out/'timing.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed']
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args();print(json.dumps(collect(a.output)))
