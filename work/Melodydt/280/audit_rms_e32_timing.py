"""Count the RMS E32 arithmetic-cycle discrepancy; never add it to wall time."""
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import sys


def audit(paths):
    rows=[]
    for path in paths:
        data=json.loads(path.read_text())
        accepted=json.loads(path.with_name('arithmetic-capture-check.json').read_text())
        if not accepted['passed'] or not data['n_counts_reconciled']: raise ValueError('unaccepted capture')
        grouped=defaultdict(lambda:dict(services=0,product_packets=0))
        for signature,count in data['rms_service_counts'].items():
            match=re.fullmatch(r'([^:]+):site(\d+):words(\d+):eps\d+:shift\d+:out\d+',signature)
            if not match: raise ValueError('unknown signature '+signature)
            window,site,words=match.groups();row=grouped[(window,int(site))]
            row['services']+=count;row['product_packets']+=2*int(words)*count
        for (window,site),row in grouped.items():
            observed=data['n_leaf_by_window'][window][site]
            if observed.get('e_product_packets_calls',0)!=row['product_packets']:
                raise ValueError('RMS product count mismatch')
            if observed.get('e_product_packets_modeled_cycles',0)!=9*row['product_packets']:
                raise ValueError('TLM cycle assumption changed')
            rows.append(dict(capture=str(path),capture_sha256=sha256(path.read_bytes()).hexdigest(),window=window,site=site,
                             tlm_product_cycles=9*row['product_packets'],measured_continuous_product_cycles=18*row['product_packets'],
                             additional_arithmetic_cycles=9*row['product_packets'],**row))
    return dict(scope='RMS arithmetic resource cycles only; overlap, SRAM, wrapper and idle scheduling excluded; not a corrected token latency',
                measured_product_contract='four S32 lanes: four 64-bit input handshakes, two six-stage arithmetic halves, two output handshakes = 18 cycles',
                rows=rows)


if __name__=='__main__':
    output=Path(sys.argv[1]);paths=list(map(Path,sys.argv[2:]));result=audit(paths)
    output.write_text(json.dumps(result,indent=2)+'\n');print('RMS_E32_TIMING_AUDIT_PASS',len(result['rows']))
