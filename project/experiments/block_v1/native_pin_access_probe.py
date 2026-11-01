"""Actual sealed-CTS baseline/via-only access probe, parallel within allocation.

This does not reroute the block, modify fixed pins or qualify a physical repair.
"""
import concurrent.futures
import json
import os
from pathlib import Path
import re
import subprocess
import time
from native_allocation_group import file_sha,memory_snapshot


def verify(root,out,cpus):
    assert cpus==16
    base=out.parents[2];source=base/'block-v1-20261027-113/tasks/native-diode-hook-probe'
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed']is True
    odb=source/'protected-cts.odb';assert file_sha(odb)==receipt['outputs'][odb.name]
    original=file_sha(odb)
    candidate=base/'block-v1-20261027-080/tasks/native-run-transaction6k-a'
    candidate_receipt=json.loads((candidate/'receipt.json').read_text());assert candidate_receipt['passed']is True
    sdc=candidate/'flow/results/nangate45/bv1_transaction6k_A/base/4_cts.sdc'
    assert file_sha(sdc)==candidate_receipt['outputs'][str(sdc.relative_to(candidate))]
    native=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef')
    assert file_sha(native)==json.loads((root/'project/experiments/block_v1/technology.json').read_text())['native_tech_sha256']
    scripts={}
    for name in ['detail_route.tcl','global_route.tcl','pin_access.tcl','variables.yaml']:
        path=Path('/OpenROAD-flow-scripts/flow/scripts')/name
        if path.exists():
            rows=path.read_text().splitlines()
            scripts[name]=dict(sha256=file_sha(path),selected_lines=[dict(line=i+1,text=line)for i,line in enumerate(rows)
                if re.search(r'via_access_layer|VIA_ACCESS_LAYER|DETAILED_ROUTE_ARGS|VIA_IN_PIN',line)])
    tech=native.read_text();sections={}
    for layer in ['metal9','metal10','via9']:
        sections[layer]=re.search(r'(?ms)^LAYER '+layer+r'\s*\n(.*?)^END '+layer+r'\s*$',tech).group(1)
    memory=memory_snapshot();parallel=2 if memory['MemAvailable']>=48*1024**3 else 1
    def one(mode):
        folder=out/mode;folder.mkdir()
        args='-via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10'
        if mode=='via-only':args+=' -via_access_layer metal10'
        script='read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib\n'
        script+='read_db {%s}\nread_sdc {%s}\nset_thread_count 8\n'%(odb,sdc)
        script+='set_routing_layers -signal metal1-metal10\npin_access '+args+'\nputs "BV1_PIN_ACCESS_COMPLETE '+mode+'"\n'
        (folder/'access.tcl').write_text(script)
        started=time.time();env=dict(os.environ,OMP_NUM_THREADS='8',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        with(folder/'access.log').open('w')as stream:
            code=subprocess.run(['openroad','-no_init','-exit','access.tcl'],cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
        text=(folder/'access.log').read_text()
        viable=code==0 and 'BV1_PIN_ACCESS_COMPLETE '+mode in text and not re.search(r'\[ERROR\b',text)
        return dict(mode=mode,args=args,started=started,finished=time.time(),returncode=code,
                    pin_access_viable=viable,log_sha256=file_sha(folder/'access.log'),
                    diagnostics=[line for line in text.splitlines()if re.search(r'\[ERROR|\[WARN|access point|APs|PIN_ACCESS_COMPLETE',line)])
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel)as pool:cases=list(pool.map(one,['baseline','via-only']))
    assert cases[0]['pin_access_viable'],'Unchanged baseline failed; preserve logs'
    assert file_sha(odb)==original and file_sha(sdc)==candidate_receipt['outputs'][str(sdc.relative_to(candidate))]
    record=dict(schema='block-v1-native-pin-access-probe/1',passed=True,allocated_cpus=cpus,
                maximum_concurrent_cpu_ceilings=8*parallel,memory_preflight=memory,cases=cases,
                source_receipt_sha256=file_sha(source/'receipt.json'),source_odb_sha256=original,
                native_tech_sha256=file_sha(native),native_sections=sections,actual_flow_scripts=scripts,
                qualified_block_repair=False,scope='Read-only actual protected CTS pin-access baseline and via-only viability; terminal rejection is recorded, not waived; no routing/RC/DRC repair claim')
    (out/'native-pin-access-probe.json').write_text(json.dumps(record,indent=2)+'\n')
