"""Requalify unchanged F300 top routing with the newly qualified S implementation.
The original F netlist/connections remain intact; S is linked by master identity.
"""
import sys, os, shutil, subprocess, json, re, hashlib
from pathlib import Path
from xml.etree import ElementTree as ET
c=Path(sys.argv[1]).resolve(); q=c/'qualification-v2'; out=c/'parent-F'; out.mkdir()
assert json.loads((c/'formal/receipt.json').read_text())['passed']
assert json.loads((c/'formal/state-preservation.json').read_text())['passed']
phy=json.loads((q/'physical-receipt.json').read_text())
assert phy['full_deck_items']==0 and phy['native_drc_empty']
leaf_counts=dict(line.split() for line in (c/'independent-sta-counts.tsv').read_text().splitlines())
assert set(leaf_counts)=={'setup','hold','capacitance','slew','fanout'} and all(int(v)==0 for v in leaf_counts.values()),leaf_counts
old=Path('/public/home/yuzelu/project-circuit/main-blockv2-f300-side-01')
suffix=Path('flow/results/nangate45/f-native-frame/base')
res=out/suffix; res.mkdir(parents=True)
for kind in ('logs','reports','objects'): (out/'flow'/kind/'nangate45/f-native-frame/base').mkdir(parents=True,exist_ok=True)
for ext in ('odb','def','v','sdc','spef'): shutil.copyfile(old/suffix/f'6_final.{ext}',res/f'6_final.{ext}')
config=(old/'config.mk').read_text()
replacements={}
for kind,new in [('LIBS',q/'local_s_base.lib'),('LEFS',q/'local_s_base.lef'),('GDS',q/'flow/results/nangate45/local_s_base/base/6_final.gds')]:
    match=re.search(r'^export ADDITIONAL_'+kind+r' = (.*)$',config,re.M); assert match
    paths=match[1].split(); found=[]
    for i,p in enumerate(paths):
        if 'issue-200-compact-local-s' in p or Path(p).name=='local_s_base.lef':
            found.append(p);paths[i]=str(new)
    assert len(found)==1,(kind,found)
    replacements[found[0]]=str(new)
    config=config[:match.start(1)]+' '.join(paths)+config[match.end(1):]
(out/'config.mk').write_text(config)
libs=re.search(r'^export ADDITIONAL_LIBS = (.*)$',config,re.M)[1]
env=os.environ.copy();env.update(CFJ_FINAL_ODB=str(res/'6_final.odb'),CFJ_OVERLAY_DIR=str(out),CFJ_FINAL_LIBS=libs,F_ELECTRICAL_SOURCE=str(out),F_ELECTRICAL_AUDIT=str(out/'independent-electrical'),F_ELECTRICAL_LIBS=libs)
(out/'independent-electrical').mkdir()
def run(args,log):
    with (out/log).open('w') as f: subprocess.run(list(map(str,args)),cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
(out/'control-sta.tcl').write_text((old/'control-sta.tcl').read_text()+'\ncheck_antennas -report_file '+str(out/'antenna.rpt')+'\n')
run(['openroad','-no_init','-exit',out/'control-sta.tcl'],'native-audit.log')
run(['openroad','-no_init','-exit',old/'independent-electrical.tcl'],'independent-electrical/run.log')
counts=dict(line.split() for line in (out/'independent-electrical/sta-counts.tsv').read_text().splitlines())
run(['make','-C','/OpenROAD-flow-scripts/flow',f'DESIGN_CONFIG={out}/config.mk',f'WORK_HOME={out}/flow','NUM_CORES=8','do-gds'],'gds.log')
deck=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc')
assert hashlib.sha256(deck.read_bytes()).hexdigest()=='4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147'
run(['klayout','-b','-r',deck,'-rd',f'in_gds={res}/6_final.gds','-rd',f'report_file={out}/full-deck.lyrdb'],'full-deck.log')
items=len(ET.parse(out/'full-deck.lyrdb').findall('.//items/item'))
same_inputs={ext:hashlib.sha256((res/f'6_final.{ext}').read_bytes()).hexdigest() for ext in ('odb','def','v','sdc','spef')}
assert all(same_inputs[ext]==hashlib.sha256((old/suffix/f'6_final.{ext}').read_bytes()).hexdigest() for ext in same_inputs)
native_empty=(out/'native-openroad-drc.rpt').stat().st_size==0
antenna_log=(out/'native-audit.log').read_text()
antenna_zero=bool(re.search(r'Found 0 net violations',antenna_log))
report=dict(passed=all(int(v)==0 for v in counts.values()) and items==0 and native_empty and antenna_zero, antenna_zero=antenna_zero,native_drc_empty=native_empty,unchanged_parent_hashes=same_inputs,counts=counts,full_deck_items=items,replacements=replacements,functional_basis='Unchanged F netlist plus S state-boundary LEC and state/clock/reset/init preservation')
(out/'receipt.json').write_text(json.dumps(report,indent=2))
assert report['passed'],report
