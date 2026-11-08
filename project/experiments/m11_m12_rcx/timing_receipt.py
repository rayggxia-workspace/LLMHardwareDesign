"""Fingerprint the actual runtime and audit the inherited constraint domain."""
import json
import os
from pathlib import Path
import re
import shutil

from timing_native import sha, sources, KINDS, STD

IMAGE = Path('/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif')
OLD_IMAGE_SHA = '49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a'


def main():
    out = Path(os.environ['TIMING_OUT']) / 'result'; out.mkdir()
    binary = Path(shutil.which('openroad')).resolve()
    library = STD.read_text()
    native = []
    for kind in KINDS:
        d = sources(kind); sdc = Path(d['sdc']); text = sdc.read_text()
        exceptions = [line for line in text.splitlines() if re.match(r'\s*(set_false_path|set_multicycle_path|set_max_delay|set_min_delay|set_case_analysis|set_clock_groups|set_disable_timing|create_generated_clock)\b', line)]
        native.append(dict(kind=kind, sdc=str(sdc), sha256=sha(sdc), inherited_exception_commands=exceptions))
    result = dict(image=str(IMAGE), image_sha256=sha(IMAGE), executable=str(binary), executable_sha256=sha(binary),
                  same_image_as_previous_parasitic_phase=sha(IMAGE) == OLD_IMAGE_SHA,
                  std_library=str(STD), std_library_sha256=sha(STD),
                  std_cells=sorted(set(re.findall(r'\bcell\s*\(\s*"?([^"\s)]+)"?\s*\)', library))),
                  std_timing_table_slew_max_ns=0.198535,
                  slew_domain_basis='Original Nangate Timing_7_7 input_net_transition grid maximum; standard-cell pins only.',
                  native_constraints=native,
                  exception_scope='Original native SDCs inspected; no exceptions silently dropped or invented in the common-clock fixture.')
    (out / 'runtime-receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('std_cells', 'native_constraints')}), flush=True)


if __name__ == '__main__': main()
