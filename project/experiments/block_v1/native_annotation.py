"""No connected RC driver may be unannotated, including clock drivers."""
import re


def inspect(folder):
    text=(folder/'annotation.rpt').read_text()
    match=re.search(r'Found (\d+) unannotated drivers\.\n(.*?)Found (\d+) partially unannotated drivers\.',text,re.S)
    assert match,'Missing complete native annotation report'
    names=[line.strip()for line in match[2].splitlines()if line.strip()]
    assert len(names)==int(match[1])and len(set(names))==len(names)
    rows={}
    for line in(folder/'annotation-connectivity.tsv').read_text().splitlines():
        name,count=line.split('\t');assert name not in rows;rows[name]=count
    checks=dict(all_native_drivers_resolved=set(rows)==set(names),
        all_unannotated_drivers_have_zero_connected_fanout=all(count=='0'for count in rows.values()),
        no_partial_drivers=int(match[3])==0)
    return dict(passed=all(checks.values()),checks=checks,unannotated_unused_drivers=len(names),
        partial_drivers=int(match[3]),connected_or_unresolved=[n for n,c in rows.items()if c!='0'],
        scope='Every native unannotated driver resolved with flat fanout through all arcs; separate connected-clock control is required')
