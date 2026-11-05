from pathlib import Path
p=Path(r'D:\Data\电路实验\control162-local-density-bounds196.py')
exec(compile(p.read_text(encoding='utf-8').replace('source-196','source-197').replace('bounds196','bounds197').replace('cap-config','cap-config').replace('[1960,1961,1962]','[1970,1971,1972]').replace('residual-196','residual-197').replace('pin-load-196','pin-load-197').replace('sready196-strong-local','sready197-balanced-local'),'balanced_local_necessary_bounds197','exec'))
