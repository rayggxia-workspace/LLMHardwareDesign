"""Read only this batch's ABC wait state on its allocated compute node."""
import datetime
import json
import os
from pathlib import Path
import subprocess

batch = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-wave2-01')
rows = []
for entry in Path('/proc').iterdir():
    if not entry.name.isdigit():
        continue
    try:
        if (entry / 'comm').read_text().strip() != 'yosys-abc':
            continue
        cwd = (entry / 'cwd').resolve()
        arguments = (entry / 'cmdline').read_bytes().decode().split('\0')
        cgroup = (entry / 'cgroup').read_text()
        if '89480' not in cgroup and batch not in cwd.parents and not any(str(batch) in arg for arg in arguments):
            continue
        row = dict(pid=int(entry.name), cwd=str(cwd), cmdline=arguments,
                   wait_channel=(entry / 'wchan').read_text(), cgroup=cgroup, file_descriptors={})
        for fd in (entry / 'fd').iterdir():
            row['file_descriptors'][fd.name] = os.readlink(str(fd))
        row['abc_scripts'] = {}
        for folder in list(batch.glob('act-cap*/tmp/yosys-abc-*')) + list(cwd.glob('_tmp_yosys-abc-*')):
            for script in folder.glob('*.script'):
                if script.stat().st_size < 256*1024:
                    row['abc_scripts'][str(script)] = script.read_text()
        rows.append(row)
    except (FileNotFoundError, PermissionError):
        pass
print(json.dumps(dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), processes=rows,
    scheduler=subprocess.check_output(['sstat','-n','-P','-j','89480.0,89480.1,89480.2',
        '--format=JobID,AveCPU,MaxRSS'], universal_newlines=True)), indent=2))
