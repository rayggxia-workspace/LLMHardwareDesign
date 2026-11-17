import pathlib,subprocess,sys,os
p=pathlib.Path(__file__).resolve().parent;f=p/'mesh25';f.mkdir(exist_ok=True)
(f/'prepare.py').write_text((p/'prepare.py').read_text().replace('/2000/50)', '/2000/25)'))
subprocess.run([sys.executable,str(f/'prepare.py')],check=True)
for name in ['edge_projection.py','pilot.py','check_pilot.py']:(f/name).write_text((p/name).read_text())
subprocess.run([sys.executable,str(f/'edge_projection.py')],check=True)
if not (f/'node_edge').exists():(f/'node_edge').symlink_to(p/'node_edge')
subprocess.run([sys.executable,str(f/'pilot.py')],env=dict(os.environ,PROJECTION_PREFIX='edge-'),check=True)
subprocess.run([sys.executable,str(f/'check_pilot.py')],env=dict(os.environ,PROJECTION_PREFIX='edge-'),check=True)
