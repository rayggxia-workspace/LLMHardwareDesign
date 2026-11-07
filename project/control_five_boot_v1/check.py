"""Check each five-type control shell with explicit native and bank boundaries."""
from pathlib import Path
import argparse,json,hashlib,re,subprocess
H=Path(__file__).resolve().parent;P=H.parent;C=P/'control_rtl_min_v0_1';B=P/'control_boot_v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def call(cmd,path):
 with path.open('wb') as f:subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--bank',type=Path,required=True)
 p.add_argument('--kind',type=int,choices=range(5),required=True);p.add_argument('--verilator',required=True);p.add_argument('--yosys',required=True);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();o=a.out.resolve();o.mkdir(parents=True,exist_ok=True)
 assert sha(a.bank)=='6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
 stubs=[]
 for path in (a.stage/'native-p/design/pu_p_group.sv',a.stage/'native-p/design/pu_u_group.sv',a.stage/'cfj/design/block_cfj_cf.sv',a.stage/'cfj/design/block_cfj_j.sv'):
  target=o/path.name;target.write_text(path.read_text().split(');',1)[0]+');\nendmodule\n');stubs.append(target)
 bank=o/'bank.v';bank.write_text(a.bank.read_text().split('  reg [DATA_WIDTH-1:0]    mem',1)[0]+'endmodule\n');stubs.append(bank)
 base=a.stage/('cfj' if a.kind in (1,2,4) else 'native-p')
 storage=base/'staged/native/block_feed_s16k_sram.sv'
 sources=[C/(x+'.sv') for x in ('mc_min_controller','lc_min_controller','two_local_link')]
 sources += [B/(x+'.sv') for x in ('control_pm','control_boot_manager')]
 sources += [H/(x+'.sv') for x in ('native_result_fifo','native_control_endpoint','five_control_top','typed_boot_front','five_boot_top')]
 sources += [P/'control_native_v1'/(x+'.sv') for x in ('pj_native_service','ucf_native_service')]
 sources.append(storage)
 assert not any(x.name.startswith('tb_') for x in sources)
 call([a.verilator,'--lint-only','--timing','--Wall','-Wno-fatal','--top-module','five_boot_top',f'-GKIND={a.kind}','-I'+str(C),*stubs,*sources],o/'lint.log')
 warnings=re.findall(r'%Warning-([A-Z0-9_]+)',(o/'lint.log').read_text())
 bad=set(warnings)&{'LATCH','MULTIDRIVEN','UNOPTFLAT','PINMISSING','WIDTHTRUNC'}
 assert not bad,bad
 script=o/'check.ys';script.write_text('read_verilog -sv -lib '+' '.join(json.dumps(str(x)) for x in stubs)+'\nread_verilog -sv -I'+str(C)+' '+' '.join(json.dumps(str(x)) for x in sources)+f'\nchparam -set KIND {a.kind} five_boot_top\nhierarchy -check -top five_boot_top\nsynth -top five_boot_top -noabc\ncheck -assert\nwrite_json '+json.dumps(str(o/'control.json'))+'\n')
 call([a.yosys,'-s',script],o/'synth.log');design=json.loads((o/'control.json').read_text())
 def matches(name,leaf):return name==leaf or design['modules'].get(name,{}).get('attributes',{}).get('hdlname')==leaf
 def count(name,leaf):
  if matches(name,leaf):return 1
  return sum(count(c['type'],leaf) for c in design['modules'].get(name,{}).get('cells',{}).values() if c['type'] in design['modules'])
 bank_count=count('five_boot_top','s_sram_256x128_freepdk45');assert bank_count==12,bank_count
 native_name=('pu_u_group','block_cfj_cf','block_cfj_cf','pu_p_group','block_cfj_j')[a.kind]
 native_count=count('five_boot_top',native_name);assert native_count==2,(native_name,native_count)
 d={'schema':'five-native-boot-structure/1','kind':a.kind,'passed':True,'pm_banks':bank_count,'native_groups':native_count,
    'native_module':native_name,'testbench_memory_in_top':False,'warnings':{x:warnings.count(x) for x in sorted(set(warnings))},
    'source_sha256':{str(x):sha(x) for x in sources},'scope':'Control/glue structure with explicit native and SRAM bank boundaries; full function uses real groups; no new mapped timing or physical qualification.'}
 d['artifacts_sha256']={x.name:sha(x) for x in o.iterdir() if x.is_file()}
 (o/'report.json').write_text(json.dumps(d,indent=2)+'\n');print('PASS five-boot structure kind',a.kind)
if __name__=='__main__':main()
