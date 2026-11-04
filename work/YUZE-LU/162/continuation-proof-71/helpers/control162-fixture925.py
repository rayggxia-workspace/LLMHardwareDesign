from pathlib import Path
import subprocess,json
h=Path(__file__).parent;out=h/'control162-refresh-fixture925';out.mkdir(exist_ok=True)
for period in (8,16):
 target=out/('route-'+str(period)+'.txt');assert not target.exists()
 p=subprocess.run([str(h/'control162-native-refresh924.exe'),str(h/'control162-batch-fixture899/input-899.txt'),str(target),'--critical-first','--native-prefix-first','--native-batch-ripup','--pin-access=ordinary-first','--native-refresh='+str(period)],capture_output=True)
 rows=[json.loads(l)for l in Path(str(target)+'.native-prefix.log').read_text().splitlines()if l.startswith('{')]
 print(json.dumps(dict(period=period,returncode=p.returncode,stderr=p.stderr.decode(),refreshes=[x for x in rows if x.get('native_full_refresh')],last=[x for x in rows if 'conflict_nodes'in x][-1])))
