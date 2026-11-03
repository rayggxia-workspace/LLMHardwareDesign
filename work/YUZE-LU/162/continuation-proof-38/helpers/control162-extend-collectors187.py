"""Discover the shorter-wire placement comparison with original acceptance intact."""
from pathlib import Path

p=Path(r'D:\Data\电路实验\control162-extend-collectors185.py');s=p.read_text(encoding='utf-8')
assert 's-ready-cpp-localdensity-source172.json'in s
s=s.replace('s-ready-cpp-localdensity-source172.json','s-ready-cpp-shortwire-source172.json').replace('collector185-source-proof','collector187-source-proof').replace('exact1850 discovery','exact1851 discovery')
exec(compile(s,'verified_1851_collector_extension','exec'))
