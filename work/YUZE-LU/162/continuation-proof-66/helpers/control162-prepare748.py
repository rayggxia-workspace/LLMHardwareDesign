from pathlib import Path
p=Path(__file__).parent;s=(p/'control162-verify708.py').read_text(encoding='utf-8').replace('online707','online747').replace('f453014340c19a963036e2ddf988f920a53f9165','a0fe946d080c8725cbdbde66ba7ed05cbc1f935b');compile(s,'verify748','exec');(p/'control162-verify748.py').write_bytes(s.encode())
