"""Freeze, simulate and hash the candidate stored-link/SRAM boundary.

Raw local_s_base ports exclude group arbiters/pj_mem_port and controllers.
Measured slots are a boundary experiment, never a P/U path calibration.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser()
    for name in ('origin','link','output'):p.add_argument(name,type=Path)
    a=p.parse_args();a.output.mkdir(exist_ok=False);manifest=json.loads((a.origin/'manifest.json').read_text())
    names=['rtl/s_sram/local_s_base.sv','rtl/s_sram/block_feed_s16k_sram.sv','s_sram_256x128_freepdk45.v']
    for name in names:
        source=a.origin/name
        if sha(source)!=manifest['sha256'][name]:raise ValueError('frozen SRAM source differs '+name)
        shutil.copyfile(source,a.output/source.name)
    if sha(a.link)!='7a852eebeb6988b2dc448bec9f4dfd48cdad56728c7ad07633008ed614c15571':
        raise ValueError('frozen #195 stored_link differs')
    shutil.copyfile(a.link,a.output/'stored_link.sv')
    shutil.copyfile('project/experiments/block_synthesis/tb_resident_transport.sv',a.output/'tb_resident_transport.sv')
    shutil.copyfile(__file__,a.output/'run_transport_probe.py')
    here='/mnt/'+a.output.drive[0].lower()+a.output.as_posix()[2:]
    tool='/tmp/yzl-issue219-iverilog12-20261109/install/bin/'
    commands=[['wsl.exe','--cd',str(a.output),'--exec',tool+'iverilog','-g2012','-s','tb_resident_transport','-o','probe.vvp',
               'tb_resident_transport.sv','stored_link.sv','local_s_base.sv','block_feed_s16k_sram.sv','s_sram_256x128_freepdk45.v']]
    def run(command,name):
        with (a.output/name).open('xb') as f:r=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
        return r.returncode
    if run(commands[0],'compile.log')!=0:raise ValueError('candidate boundary compile failed')
    reports=[]
    for mode in range(3):
        command=['wsl.exe','--cd',str(a.output),'--exec',tool+'vvp','probe.vvp',f'+INIT={mode}']
        commands.append(command);log=a.output/f'simulate-{mode}.log'
        if run(command,log.name)!=0:raise ValueError('candidate boundary positive failed')
        raw=log.read_bytes();matches=re.findall(rb'PASS candidate_transport transfers=(\d+) commits=(\d+) releases=(\d+) min_slots=(\d+) max_slots=(\d+)',raw)
        if len(matches)!=1:raise ValueError('missing candidate boundary summary')
        count,commits,releases,low,high=map(int,matches[0])
        if (count,commits,releases)!=(64,64,64) or low!=high:raise ValueError('candidate boundary accounting/profile differs')
        reports.append({'initialization':mode,'transfers':count,'commits':commits,'releases':releases,'inclusive_slots':low,'log_sha256':sha(log)})
    negative=['wsl.exe','--cd',str(a.output),'--exec',tool+'vvp','probe.vvp','+INIT=1','+FAULT=1'];commands.append(negative)
    code=run(negative,'negative-ack.log');raw=(a.output/'negative-ack.log').read_bytes()
    if code==0 or b'source release before destination ACK' not in raw:raise ValueError('ACK fault was not detected')
    result={'passed':True,'reports':reports,'negative_ack_returncode':code,'commands':commands,
            'sha256':{f.name:sha(f) for f in sorted(a.output.iterdir()) if f.is_file()},
            'scope':'unchanged stored_link plus two real 16KiB SRAM raw ports, serialized copies and reservation/offer/ACK stalls; excludes group adapters/arbiters, LC/MC, simultaneous sends, physical timing, system/energy/token/s'}
    (a.output/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':True,'reports':reports,'negative_ack_returncode':code}))


if __name__=='__main__':main()
