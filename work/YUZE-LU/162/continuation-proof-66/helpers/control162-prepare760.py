from pathlib import Path
p=Path(__file__).parent;s=(p/'control162-read739.py').read_text(encoding='utf-8').replace('live-readback-739','live-readback-760').replace("[('dynamic-05/node4',4850,95391),('dynamic-05/node2',5190,95341)]","[('dynamic-02/node3',5191,95098),('dynamic-04/node25',5192,95204)]")
compile(s,'read760','exec');(p/'control162-read760.py').write_bytes(s.encode())
