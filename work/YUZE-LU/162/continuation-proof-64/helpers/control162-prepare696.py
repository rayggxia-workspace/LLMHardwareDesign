from pathlib import Path
p=Path(__file__).parent;s=(p/'control162-read694.py').read_text(encoding='utf-8').replace('readback-694','readback-696')
old="if '--seed'in a and a[a.index('--seed')+1]==str(seed):matches.append((p,s,a))";new="if '--out'in a and Path(a[a.index('--out')+1]).parent.name==str(seed):matches.append((p,s,a))";assert old in s;s=s.replace(old,new);compile(s,'read696','exec');(p/'control162-read696.py').write_bytes(s.encode())
