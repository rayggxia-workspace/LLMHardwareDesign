from pathlib import Path
import tempfile,subprocess
with tempfile.TemporaryDirectory(dir='.local',prefix='grid-overlay-control-') as tmp:
 root=Path(tmp).resolve();src=root/'source';p=src/'compiler/characterizer/delay.py';p.parent.mkdir(parents=True);p.write_bytes(Path('.local/delay-reference155.py').read_bytes());before=p.read_bytes()
 subprocess.run(['python','project/experiments/s_sram/parallel_grid_overlay.py','--source',str(src),'--destination',str(root/'overlay'),'--receipt',str(root/'proof.json')],check=True)
 assert p.read_bytes()==before
 print('PASS: exact native method patch compiles and preserves original source')
