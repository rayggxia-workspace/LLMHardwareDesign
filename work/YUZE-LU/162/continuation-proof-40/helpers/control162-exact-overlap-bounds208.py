from pathlib import Path
p=Path(r'D:\Data\电路实验\control162-local-density-bounds196.py')
exec(compile(p.read_text(encoding='utf-8').replace('source-196','source-207').replace('bounds196','bounds208').replace('[1960,1961,1962]','[2070,2071,2072]').replace('residual-196','residual-208').replace('pin-load-196','pin-load-208').replace('sready196-strong-local','sready208-exact-overlap'),'exact_overlap_necessary_bounds208','exec'))
