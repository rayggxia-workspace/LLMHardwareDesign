from pathlib import Path
import subprocess,sys
h=Path(__file__).parent;s=(h/'control162-config579.py').read_text(encoding='utf-8').replace('config579','config581').replace('binding-audit-579','binding-audit-581')
s=s.replace("cfg['pg_audit']==str(scene/'pg')","cfg['pg_audit']==str(scene/'pg-audit')").replace("Path(path).parent==scene and Path(path).name=='sta-'+variant","Path(path).parent==scene/'timing' and Path(path).name==variant")
needle="   for folder in ['r256-padding-program-events-473','r256-padding-program-event-audit-480']:"
extra="""   assert set(fr['initial_results'])=={'initial-1-162.json','initial-2-162.json','initial-2-163.json'}
   geometry=next(t['spec']for t in candidates if '-geometry-'in Path(t['path']).stem);pg=next(t['spec']for t in candidates if '-pg-'in Path(t['path']).stem)
   assert geometry['args'][geometry['args'].index('--out')+1]==cfg['geometry']and pg['args'][pg['args'].index('--out')+1]==cfg['pg_audit']and pg['args'][pg['args'].index('--pg-audit')+1]==cfg['geometry']
   for variant,path in cfg['timing'].items():
    t=next(t['spec']for t in candidates if t['spec']['script']=='system_sta.py'and t['spec']['args'][t['spec']['args'].index('--rc-variant')+1]==variant);ta=t['args'];assert ta[ta.index('--out')+1]==path and ta[ta.index('--upper-geometry')+1]==cfg['geometry']and'--stitch-native-access'in ta and'--audit-native-coverage'in ta
"""
assert s.count(needle)==1;s=s.replace(needle,extra+needle);p=h/'control162-config581.py';assert not p.exists();p.write_bytes(s.encode());compile(s,str(p),'exec');subprocess.run([sys.executable,str(p)],check=True)
