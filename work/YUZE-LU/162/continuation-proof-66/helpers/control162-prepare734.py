from pathlib import Path
p=Path(__file__).parent;s=(p/'control162-watch686.py').read_text(encoding='utf-8');s=s.replace("out=h/'control162-watch686'","out=h/'control162-watch734'",1).replace("h/'control162-watch662'","h/'control162-watch686'",1);compile(s,'monitor734','exec');(p/'control162-watch734.py').write_bytes(s.encode())
