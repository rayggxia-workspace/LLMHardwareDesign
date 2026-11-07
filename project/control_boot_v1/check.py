"""Lint and synthesize the boot/control shell with explicit P and SRAM boundaries."""
from pathlib import Path
import argparse,json,re,hashlib,subprocess
H=Path(__file__).resolve().parent;P=H.parent;C=P/'control_rtl_min_v0_1';T=P/'control_dual_p_top_v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def call(cmd,path):
 with path.open('wb') as f:subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--bank',type=Path,required=True)
 p.add_argument('--verilator',required=True);p.add_argument('--yosys',required=True);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();o=a.out.resolve();o.mkdir(parents=True,exist_ok=True)
 original=a.stage/'design/pu_p_group.sv';raw=original.read_bytes()
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()=='3dd63bf7b07d7d5a10fefe3f6c557ed559aaf47b'
 ps=o/'pu_p_group.sv';ps.write_text(raw.decode().split(');',1)[0]+');\nendmodule\n')
 bs=o/'bank.v';bs.write_text(a.bank.read_text().split('  reg [DATA_WIDTH-1:0]    mem',1)[0]+'endmodule\n')
 storage=a.stage/'staged/native/block_feed_s16k_sram.sv'
 sources=[C/(x+'.sv') for x in ('mc_min_controller','lc_min_controller','two_local_link')]
 sources += [T/(x+'.sv') for x in ('dual_p_control_top','p_control_endpoint','p_word_link')]
 sources += [H/(x+'.sv') for x in ('control_pm','control_boot_manager','control_boot_top')]
 sources += [P/'control_native_v1'/(x+'.sv') for x in ('pj_native_service','ucf_native_service','stored_link')]
 sources += [P/'control_r4_v0_1/p_stored_ack_guard.sv',storage]
 assert not any(x.name.startswith('tb_') for x in sources)
 call([a.verilator,'--lint-only','--timing','--Wall','-Wno-fatal','--top-module','control_boot_top','-I'+str(C),ps,bs,*sources],o/'lint.log')
 warnings=re.findall(r'%Warning-([A-Z0-9_]+)',(o/'lint.log').read_text())
 bad=set(warnings)&{'LATCH','MULTIDRIVEN','UNOPTFLAT','PINMISSING','WIDTHTRUNC'}
 assert not bad,bad
 script=o/'check.ys';script.write_text('read_verilog -lib '+json.dumps(str(ps))+' '+json.dumps(str(bs))+'\nread_verilog -sv -I'+str(C)+' '+' '.join(json.dumps(str(x)) for x in sources)+'\nhierarchy -check -top control_boot_top\nsynth -top control_boot_top -noabc\ncheck -assert\nwrite_json '+json.dumps(str(o/'control.json'))+'\n')
 call([a.yosys,'-s',script],o/'synth.log')
 design=json.loads((o/'control.json').read_text())
 def count(name,leaf):
  if name==leaf:return 1
  return sum(count(c['type'],leaf) for c in design['modules'].get(name,{}).get('cells',{}).values() if c['type'] in design['modules'])
 assert count('control_boot_top','s_sram_256x128_freepdk45')==12
 assert count('control_boot_top','pu_p_group')==2
 d={'schema':'control-boot-structure/1','synthesis_structure_passed':True,'testbench_modules':False,'pm_sram_banks':12,'p_group_boundaries':2,
    'warnings':{x:warnings.count(x) for x in sorted(set(warnings))},'source_sha256':{str(x):sha(x) for x in sources},
    'scope':'Current MC/LC, PM interfaces, loader, CRC and link synthesized. P group and OpenRAM banks are explicit macro boundaries. Full mapping/timing/physical remains pending.'}
 d['artifacts_sha256']={x.name:sha(x) for x in o.iterdir() if x.is_file()}
 (o/'report.json').write_text(json.dumps(d,indent=2)+'\n');print('PASS boot/control structure with 12 PM banks and 2 P boundaries')
if __name__=='__main__':main()
