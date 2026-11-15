"""Historical pre-PR185 flow; use README.md for the current macro-native compiler."""
import argparse,json,os,subprocess,sys
from hashlib import sha256
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--legacy-diagnostic',action='store_true',
 help='explicitly opt into the historical, non-accepted pre-PR185 flow')
p.add_argument('--environment',type=Path,required=True)
sub=p.add_subparsers(dest='mode',required=True)
c=sub.add_parser('compile');c.add_argument('graph',type=Path);c.add_argument('hardware',type=Path)
c.add_argument('--output',type=Path,required=True);c.add_argument('--width',type=int,default=8)
e=sub.add_parser('evaluate');e.add_argument('package',type=Path)
e.add_argument('--output',type=Path,required=True);e.add_argument('--scene',choices=['diagnostic-zero'],required=True)
e.add_argument('--core-ps',type=int,required=True);e.add_argument('--sram-config',type=Path)
a=p.parse_args()
if not a.legacy_diagnostic:
 p.error('Retired pre-PR185 entry. Use README.md: run_macro_graph_frontend.py, run_macro_selection.py, materialize_native_product.py and package_native_plan.py. Historical diagnostics require --legacy-diagnostic and matching frozen sources.')
config=json.loads(a.environment.read_text());root=Path(__file__).resolve().parent
if config['schema']!='blockv2-mod-runtime-environment/1':raise ValueError('unsupported environment')
for name,seal in config['files'].items():
    raw=Path(name).read_bytes()
    if len(raw)!=seal['bytes'] or sha256(raw).hexdigest()!=seal['sha256']:
        raise ValueError('runtime source differs from pinned environment: '+name)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',
         PYTHONPATH=os.pathsep.join(config['module_roots']+config['extra_python_roots']))
if a.mode=='compile':
    command=[str(root/'compile_graph_input.py'),str(a.graph.resolve()),str(a.hardware.resolve()),
             '--output',str(a.output.resolve()),'--width',str(a.width)]
else:
    command=[str(root/'tlm/run_native_package.py'),str(a.package.resolve()),
             config['dram_library'],config['dram_config'],config['g_reference'],str(a.output.resolve()),
             '--scene',a.scene,'--core-ps',str(a.core_ps)]
    if a.sram_config:command+=['--sram-config',str(a.sram_config.resolve())]
raise SystemExit(subprocess.run([config['python'],'-B',*command],cwd=root,env=env).returncode)
