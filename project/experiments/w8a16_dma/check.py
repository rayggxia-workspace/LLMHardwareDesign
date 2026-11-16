"""Strict production DMA RTL and independent finite transport scoreboard; Slurm only."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--seed',type=int,required=True);p.add_argument('--serial-limit',type=int,default=65535);p.add_argument('--skids-per-channel',type=int,choices=(2,3,4),default=3);a=p.parse_args();assert len(os.sched_getaffinity(0))==10;a.out.mkdir(parents=True,exist_ok=False)
 rtl=a.source/'project/rtl/mother_control_native/mc_dma_fabric.sv';cpp=a.source/'project/experiments/w8a16_dma/dma.cpp';v='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
 def run(cmd,name):
  with(a.out/name).open('w')as f:subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
 run([v,'--lint-only','--Wall','--top-module','mc_dma_fabric',rtl],'lint.log')
 run([v,'--cc','--exe','--build','--Wall','--timescale-override','1ns/1ps','--x-initial','unique','--top-module','mc_dma_fabric',"-GSERIAL_LIMIT=16'd"+str(a.serial_limit),'-GSKIDS_PER_CHANNEL='+str(a.skids_per_channel),'-j','10','--Mdir',a.out/'obj','-CFLAGS','-std=c++17 -Wall -Wextra -Werror',rtl,cpp],'build.log')
 runs=[]
 for initial in(0,1,2):
  name=f'initial-{initial}.log';run([a.out/'obj/Vmc_dma_fabric',a.seed,initial,a.out/f'timing-{initial}.csv'],name);receipt=(a.out/name).read_text().strip();assert receipt.startswith('PASS DMA ');runs.append(dict(initial=initial,receipt=receipt))
 result=dict(passed=True,source_commit=(a.source/'source-commit.txt').read_text().strip(),RTL_SHA256=hashlib.sha256(rtl.read_bytes()).hexdigest(),seed=a.seed,serial_limit=a.serial_limit,return_skids_per_channel=a.skids_per_channel,runs=runs,scope='Actual production finite DMA RTL; synthetic deterministic transport payload, no model/whole-system/physical claim. Serial-limit3 is an explicit exhaustion configuration; production65535 separately checked.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
