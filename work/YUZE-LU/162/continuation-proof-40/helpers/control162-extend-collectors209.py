from pathlib import Path
p=Path(r'D:\Data\电路实验\control162-extend-collectors198.py');s=p.read_text(encoding='utf-8')
s=s.replace("records=['s-ready-balanced-fast-source172.json','s-ready-balanced-cpp-source172.json']","records=['s-ready-exact-fast-source172.json','s-ready-exact-cpp-source172.json']").replace('control162-collector198-source-proof.json','control162-collector209-source-proof.json').replace('anchor="\'s-ready-cpp-weighted-local-source172.json\'"','anchor="\'s-ready-balanced-cpp-source172.json\'"')
exec(compile(s,'discover_exact_overlap_routes209','exec'))
