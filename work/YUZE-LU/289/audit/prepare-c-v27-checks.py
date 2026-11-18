from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=r/'audit/C-v27-physical'
s=(r/'audit/c-main-material.sbatch').read_text().replace('out=$r/audit/C-main-clock4-physical-v1/rcx-material-$SLURM_JOB_ID','out=$r/audit/C-v27-physical/rcx-material-$SLURM_JOB_ID').replace('sourcepath=$r/cu/diagnostics/C-main-v1-rcx','sourcepath=$r/cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base').replace('before-rcx.def','6_final.def').replace('after-rcx.def','6_post_rcx.def').replace('after-rcx.odb','6_post_rcx.odb').replace('C-v20-native-clock4','C-v27-joint-e20-h30')
(p/'rcx-material.sbatch').write_text(s)
q=p/'oai221-isolated';q.mkdir(exist_ok=False)
(q/'export.py').write_text('''from pathlib import Path
import pya,json,hashlib
p=Path.cwd();source=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v20-native-clock4/flow/results/nangate45/c-overlay-current/base/6_final.gds');lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/gds/NangateOpenCellLibrary.gds');out={}
for label,g in [('merged',source),('library',lib)]:
 l=pya.Layout();l.read(str(g));c=l.cell('OAI221_X4');assert c is not None;opts=pya.SaveLayoutOptions();opts.select_cell(c.cell_index());l.write(str(p/(label+'.gds')),opts);out[label]=dict(source=str(g),source_sha256=hashlib.sha256(g.read_bytes()).hexdigest(),export_sha256=hashlib.sha256((p/(label+'.gds')).read_bytes()).hexdigest())
(p/'export-binding.json').write_text(json.dumps(out,indent=2))
''')
s=(r/'c-focused.sbatch').read_text();s=s[:s.index('set -euo pipefail')]+'''set -euo pipefail
out=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v27-physical/oai221-isolated
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu --pwd "$out" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; klayout -b -r export.py > export.log 2>&1; deck=/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc; echo "4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147  $deck" | sha256sum -c - > deck-identity.txt; for name in merged library; do klayout -b -r "$deck" -rd "in_gds=$PWD/$name.gds" -rd "report_file=$PWD/$name.lyrdb" > "$name.log" 2>&1; done'
''';(q/'run.sbatch').write_text(s.replace('yzl-289-C-diag','yzl-C-oai221').replace('/c-focused-%j.log','/audit/C-oai221-%j.log'))
