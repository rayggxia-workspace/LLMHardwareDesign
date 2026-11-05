from pathlib import Path
import subprocess
p=Path(r'D:\Data\电路实验\control162-add88-command.py');s=p.read_text()
for old,new in [('arbiter-setup-04','arbiter-setup-05'),('00-j','00-k'),('composition-arbiter-06','composition-arbiter-07'),('native-arbiter-sta-18','native-arbiter-sta-19'),('pg-arbiter-08','pg-arbiter-09'),('pg-arbiter-checks-05','pg-arbiter-checks-06'),('pg-arbiter-delivery-06','pg-arbiter-delivery-07'),('din[632]','din[633]')]:s=s.replace(old,new)
target=p.with_name('control162-add88-retry633.py');assert not target.exists();target.write_text(s);subprocess.run(['python',str(target)],check=True)
