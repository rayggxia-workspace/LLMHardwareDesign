"""Add exact CUGR24 record discovery after the same unchanged-source checks."""
from pathlib import Path

p=Path(r'D:\Data\电路实验\control162-extend-collectors185.py')
s=p.read_text(encoding='utf-8')
assert 's-ready-cpp-localdensity-source172.json'in s and'collector185-source-proof'in s
s=s.replace('s-ready-cpp-localdensity-source172.json','s-ready-cugr24phase-source172.json').replace('collector185-source-proof','collector184-source-proof').replace('exact1850 discovery','exact1840 discovery')
exec(compile(s,'verified_1840_collector_extension','exec'))
