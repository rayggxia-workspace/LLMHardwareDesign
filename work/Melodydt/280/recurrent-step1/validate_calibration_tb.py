"""Check the gate-calibration testbench against its candidate RTL before gate replay."""
from pathlib import Path
from hashlib import sha256
import json, re, subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BIN=Path('D:/EDA/modeltech64_2020.4/win64')
checks={}
for name in ('qwen35','falcon-wide'):
    work=ROOT/'tmp/recurrent-step1'/(name+'-cal')
    rtl=(HERE/'rtl/block_v1_r_qwen35.sv'
         if name=='qwen35' else ROOT/'tmp/recurrent-step1/falcon-wide/block_v1_r.sv')
    segments=json.loads((work/'segments.json').read_bytes())
    (work/'ends.txt').write_text('\n'.join(str(s['end_command']) for s in segments)+'\n')
    count=len((work/'commands.txt').read_text().splitlines())
    def run(cmd):
        p=subprocess.run(list(map(str,cmd)),cwd=work,capture_output=True,text=True,check=True)
        return p.stdout+p.stderr
    run([BIN/'vlog.exe','-sv',rtl,HERE/'calibrate_tb.sv'])
    log=run([BIN/'vsim.exe','-c','-onfinish','exit','-do',
             'onbreak {quit -code 1}; run -all; quit -f','work.calibrate_tb',f'+count={count}'])
    assert 'GATE_REPLAY_PASS' in log
    windows=[list(map(int,w)) for w in re.findall(r'WINDOW (\d+) (\d+) (\d+) (\d+)',log)]
    assert len(windows)==12
    assert all(c-b==b-a and b>a for _,a,b,c in windows)
    checks[name]=dict(windows_ps=windows,log=log,rtl_sha256=sha256(rtl.read_bytes()).hexdigest(),
                     tb_sha256=sha256((HERE/'calibrate_tb.sv').read_bytes()).hexdigest())
    print(name,'CALIBRATION_TB_PASS',[(w[2]-w[1])//5000 for w in windows])
(HERE/'calibration-tb-check.json').write_text(json.dumps(checks,indent=2)+'\n')
