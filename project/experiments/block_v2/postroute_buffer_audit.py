"""Strict readback for one measured combinational cell, never a timing waiver."""
import hashlib

INSTANCE = 'place571072'
OLD_MASTER = 'BUF_X4'
NEW_MASTER = 'CLKBUF_X3'


def compare_def_lines(before, after):
    """Require every DEF byte except this exact component master to be equal."""
    non_target = hashlib.sha256()
    changed = []
    for old, new in __import__('itertools').zip_longest(before, after):
        assert old is not None and new is not None, 'DEF line count changed'
        if old == new:
            non_target.update(old)
            continue
        assert old.lstrip().startswith(('- '+INSTANCE+' '+OLD_MASTER+' ').encode()), 'Unrelated DEF changed'
        assert new == old.replace((' '+OLD_MASTER+' ').encode(), (' '+NEW_MASTER+' ').encode(), 1), 'More than master changed'
        changed.append(dict(before=old.decode().rstrip('\n'), after=new.decode().rstrip('\n')))
    assert len(changed) == 1, 'Expected exactly one component-master edit'
    return dict(identical_non_target_geometry=True, identical_target_terminal_connections=True,
                unchanged_all_routes_and_ports=True, unchanged_all_placement=True,
                non_target_def_sha256=non_target.hexdigest(), changed=changed)


def pin_contact_audit(master_lines, wire_lines, x=1110360, y=1727600):
    """Prove every old M1 wire contact still lies inside a real new M1 pin.

    This exact instance is R0. Both libraries' actual rectangles are measured,
    rather than assuming that names or logical pin compatibility imply contact.
    Native whole DRC/connectivity/GDS checks remain unconditional.
    """
    pins = {}
    for line in master_lines:
        row = line.rstrip('\n').split('\t')
        if row[0] not in (OLD_MASTER, NEW_MASTER):
            continue
        master, width, height, pin, direction, layer, *coords = row
        assert int(height) == 2800 and int(width) == {OLD_MASTER: 2660, NEW_MASTER: 1900}[master]
        assert layer == 'metal1' and pin in ('A', 'Z')
        a, b, c, d = map(int, coords)
        pins.setdefault((master, pin), []).append((a+x, b+y, c+x, d+y))
    assert set(pins) == {(master, pin) for master in (OLD_MASTER, NEW_MASTER) for pin in ('A', 'Z')}
    def intersection(a, b):
        box = (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))
        return box if box[0] < box[2] and box[1] < box[3] else None
    contacts = {'A': [], 'Z': []}
    for line in wire_lines:
        label, layer, kind, *coords = line.rstrip('\n').split('\t')
        assert label in contacts
        if layer != 'metal1':
            continue
        box = tuple(map(int, coords))
        for old in pins[(OLD_MASTER, label)]:
            hit = intersection(box, old)
            if hit:
                assert any(new[0] <= hit[0] and new[1] <= hit[1] and new[2] >= hit[2] and new[3] >= hit[3]
                           for new in pins[(NEW_MASTER, label)]), 'Existing wire contact misses real replacement pin'
                contacts[label].append(dict(wire_box_dbu=list(box), old_contact_dbu=list(hit)))
    assert all(contacts.values()), 'Both actual data pins must retain physical contacts'
    return dict(passed=True, instance=INSTANCE, orientation='R0', location_dbu=[x,y],
                contact_checks=contacts, replacement_fits_original_footprint=True,
                scope='Measured single R0 buffer contacts only; no final macro qualification')
