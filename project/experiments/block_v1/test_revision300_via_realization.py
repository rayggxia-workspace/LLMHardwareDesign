"""Negative geometry controls for the planning-only via realization helper."""
from revision300_via_realization import contains, dbu, plan


def main():
    assert contains((0, 0, 10, 10), [(0, 0, 5, 10), (5, 0, 10, 10)])
    assert not contains((0, 0, 10, 10), [(0, 0, 4, 10), (5, 0, 10, 10)])
    assert not contains((0, 0, 10, 10), [(0, 0, 10, 4), (0, 5, 10, 10)])
    assert not contains((0, 0, 10, 10), [(0, 0, 10, 1), (0, 0, 1, 10)])
    assert contains((-10, -10, 0, 0), [(-11, -11, 1, 1)])
    try:
        dbu('0.0001', 2000)
    except AssertionError:
        pass
    else:
        raise AssertionError('Fractional database coordinates were accepted')
    tech = ''.join('LAYER metal%d\n TYPE ROUTING ;\n WIDTH 0.07 ;\nEND metal%d\n' % (i, i)
                   for i in range(1, 11))
    tech += '''VIA via2_5 DEFAULT
 LAYER metal2 ;
 RECT -0.035 -0.035 0.035 0.035 ;
 LAYER via2 ;
 RECT -0.025 -0.025 0.025 0.025 ;
 LAYER metal3 ;
 RECT -0.035 -0.035 0.035 0.035 ;
END via2_5
'''
    record = '- test ( PIN a ) ( PIN b ) + ROUTED metal2 ( 0 0 ) via2_5 NEW metal3 ( 0 0 ) ( 200 0 ) ;'
    marker = 'violation type: Metal Spacing\n net:test net:test\n bbox = (0.035, -0.035) - (0.1, 0.035) on Layer metal3\n'
    result = plan(marker, {'test': record}, tech)
    assert len(result['proposals']) == 1 and not result['rejected']
    changed = result['nets']['test']['changes'][0]['rectangles']
    assert changed['metal3'] == (-70, -70, 200, 70)
    assert changed['via2'] == (-50, -50, 50, 50)
    assert changed['metal2'] == (-70, -70, 70, 70)
    # Same bounding box and same via, but no conductor over the proposed gap.
    no_wire = '- test ( PIN a ) ( PIN b ) + ROUTED metal2 ( 0 0 ) via2_5 ;'
    assert not plan(marker, {'test': no_wire}, tech)['proposals']
    assert not plan(marker.replace('net:test net:test', 'net:test net:other'), {'test': record}, tech)['proposals']
    assert not plan(marker.replace('on Layer metal3', 'on Layer via2'), {'test': record}, tech)['proposals']
    assert not plan(marker.replace('Metal Spacing', 'Short'), {'test': record}, tech)['proposals']
    assert not plan(marker, {}, tech)['proposals']
    assert result['physical_qualified'] is False
    print('PASS: exact union holes, fractional DBU, absent conductor/net, cross-net and cut-layer controls; cut/other metal unchanged')


if __name__ == '__main__':
    main()
