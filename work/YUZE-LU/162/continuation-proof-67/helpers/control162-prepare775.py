from pathlib import Path
p=Path(__file__).parent;s=(p/'control162-read739.py').read_text(encoding='utf-8').replace('live-readback-739','live-readback-775').replace("[('dynamic-05/node4',4850,95391),('dynamic-05/node2',5190,95341)]","[('dynamic-06/node26',5490,96222),('dynamic-06/node26',5493,96222)]")
compile(s,'read775','exec');(p/'control162-read775.py').write_bytes(s.encode())
