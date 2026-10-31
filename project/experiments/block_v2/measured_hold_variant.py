"""Two bounded physical-delay candidates; identical RTL and signoff contract."""
def derive(prototype, count):
    assert count in (4,8)
    if count==4:return prototype
    text=prototype.decode('utf-8')
    changes=[('buffers_per_endpoint\\t4\\t','buffers_per_endpoint\\t8\\t'),
             ('for {set i 0} {$i<4} {incr i} {','for {set i 0} {$i<8} {incr i} {'),
             ('[$core xMax]-20000','[$core xMax]-36000')]
    for before,after in changes:
        assert text.count(before)==1,before
        text=text.replace(before,after,1)
    return text.encode('utf-8')
