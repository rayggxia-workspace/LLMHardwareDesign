from pathlib import Path
p=Path(r'D:\Data\电路实验\control162-local-density-status196.py')
exec(compile(p.read_text(encoding='utf-8').replace('range(1960,1963)','range(2070,2073)').replace('[1960,1962]','[2070,2072]').replace('00-j-sready196-strong-local-','00-j-sready208-exact-overlap-').replace('residual-196','residual-208').replace('pin-load-196','pin-load-208'),'exact_overlap_status208','exec'))
