from pathlib import Path
p=Path(r'D:\Data\电路实验\control162-local-density-status196.py')
exec(compile(p.read_text(encoding='utf-8').replace('range(1960,1963)','range(1970,1973)').replace('[1960,1962]','[1970,1972]').replace('00-j-sready196-strong-local-','00-j-sready197-balanced-local-').replace('residual-196','residual-197').replace('pin-load-196','pin-load-197'),'balanced_local_status197','exec'))
