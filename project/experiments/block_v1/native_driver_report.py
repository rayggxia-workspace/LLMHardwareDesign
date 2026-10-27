"""Strict receipt of real ODB used-signal driver inventories."""


def inspect(text):
    rows=text.splitlines()
    assert rows,'Missing driver inventory'
    assert rows[-1].startswith('SUMMARY\t'),'Driver inventory lacks terminal summary'
    tail=rows[-1].split('\t')
    assert len(tail)==3
    assert all(x.isdigit()for x in tail[1:])
    used,bad=map(int,tail[1:]);assert used>0 and 0<=bad<=used
    seen=set()
    for line in rows[:-1]:
        fields=line.split('\t')
        assert len(fields)==4 and fields[0]=='UNDRIVEN' and fields[1]
        assert fields[1]not in seen and fields[2].isdigit()and int(fields[2])>0
        seen.add(fields[1])
    assert len(seen)==bad,'Driver detail and summary counts differ'
    return dict(passed=bad==0,used_signal_nets=used,undriven_used_signal_nets=bad,
                scope='Actual ODB input/output directions on used non-PG nets; floating connected nets are failures')
