from pathlib import Path
p=Path(r'D:\Data\电路实验\control162-balanced-full198.py');s=p.read_text(encoding='utf-8')
for a,b in [('95098,1980','95098,2091'),('95101,1981','95101,2090'),('s-ready-balanced-fast-source172.json','s-ready-exact-fast-source172.json'),('s-ready-balanced-cpp-source172.json','s-ready-exact-cpp-source172.json'),('sready198fast-','sready209fast-'),('sready198cpp-','sready209cpp-'),('strong-local-native-residual-197','strong-local-native-residual-208'),('strong-local-native-pin-load-197','strong-local-native-pin-load-208'),('[1970]','[2071]'),('sready197-default-replay-verification.json','sready208-quantized-replay-verification.json'),('{1 if kind=="fast"else 4}','{1}'),('matched1970 placement','matched2071 exact-overlap placement'),('strong balanced placement cost oracles and default16','exact-overlap placement cost oracles and quantized16')]:
 assert a in s,a
 s=s.replace(a,b)
exec(compile(s,'exact_overlap_full209','exec'))
