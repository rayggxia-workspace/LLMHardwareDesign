"""One exact own slow search slot becomes the new full regression."""
from pathlib import Path
import ast,subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-regression-launch142.py');q=ast.literal_eval(ast.parse(p.read_text(encoding='utf-8')).body[1].value)
q=q.replace("source=b/'source-142'","source=b/'source-144'").replace("m['commit']=='415069fbe00e9706eee8bfcfeec842ec4b0ac878'","m['commit']=='4e44f5fa9c5374c27b631b452f88c9f0440f9a2e'")
q=q.replace('sready142-independent-congestion-regression','sready144-product-history-regression').replace('1411','1460')
q=q.replace("b/'source-140'","b/'source-142'").replace("source-140/project/experiments/control_v1/system_upper.py","source-142/project/experiments/control_v1/system_upper.py")
q=q.replace('router-congestion-regression-01','router-history-product-regression-01').replace('00-r-sready142-search-regression','00-r-sready144-history-product-regression')
q=q.replace('Retire one exact own slow coupled-weight4 ordering search to admit full default-plus-new search-order regression; preserve all old evidence, other search controls, parent allocations and physical gates. Not a completed physical failure.',
            'Retire only exact own slow source142 weight4 search1460, which completed round0 and is still in round1, to admit full default-plus-product-history regression. Preserve uncoupled and coupled controls, all old specs/partial results, parent allocation, other tasks and physical gates. Not a completed physical failure.')
compile(q,'actual_product_regression_admission','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55).decode())
