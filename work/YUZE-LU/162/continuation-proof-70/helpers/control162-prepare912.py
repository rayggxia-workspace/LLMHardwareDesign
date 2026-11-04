from pathlib import Path
import shutil
h=Path(__file__).parent;out=h/'control162-native-repair912';assert not out.exists();out.mkdir()
for name in ['input.txt','native-paths.txt','diagnostic.json']:shutil.copyfile(h/'control162-native-repair897'/name,out/name)
s=(h/'control162-repair897.py').read_text().replace("out=home/'control162-native-repair897'","out=home/'control162-native-repair912'").replace('budget=16384','budget=65536')
s=s.replace('orders.append(order)','orders.append(order)\nfor _ in range(29):\n order=focus.copy();r.shuffle(order);orders.append(order)')
s=s.replace('batch=i,complete=ok','batch=i,budget=65536,complete=ok');compile(s,'repair912','exec');(h/'control162-repair912.py').write_bytes(s.encode())
