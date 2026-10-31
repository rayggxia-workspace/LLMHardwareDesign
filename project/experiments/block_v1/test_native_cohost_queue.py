"""Safety controls for spare-CPU admission; no EDA or fake qualification."""
from native_cohost_queue import partition, reserve_memory


def rejected(call):
    try:
        call()
    except AssertionError:
        return
    raise AssertionError('Invalid partition/memory was accepted')


def test():
    assert partition(range(96), range(16), range(16,96)) == list(range(16,96))
    rejected(lambda: partition(range(96), range(16), list(range(17,96))+[0]))
    rejected(lambda: partition(range(96), range(16), range(16,95)))
    rejected(lambda: partition(range(95), range(16), range(16,96)))
    gib=1024**3
    adjusted, reserved=reserve_memory(dict(MemTotal=512*gib,MemAvailable=490*gib),192,8*gib)
    assert reserved==int(192*gib*1.2) and adjusted['MemAvailable']==adjusted['MemTotal']==512*gib-reserved
    # Exactly five numerical tasks beside one physical task; a sixth cannot
    # enter the80-CPU partition even when RAM would otherwise permit it.
    assert len(partition(range(96),range(16),range(16,96)))//16==5
    assert adjusted['MemTotal']-16*gib>=5*int(32*gib*1.2)
    huge, measured=reserve_memory(dict(MemTotal=512*gib,MemAvailable=200*gib),192,300*gib)
    assert measured==300*gib and huge['MemTotal']==212*gib
    rejected(lambda: reserve_memory(dict(MemTotal=240*gib,MemAvailable=200*gib),192,0))
    print('PASS cohost CPU-overlap/missing-CPU/wrong-allocation and forecast/liveRSS memory controls')


if __name__=='__main__':
    test()
