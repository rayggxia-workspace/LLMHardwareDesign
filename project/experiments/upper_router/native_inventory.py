"""Read actual native ODB terminals; never turn a logical bundle into a guessed pin.

Run using `openroad -python native_inventory.py package output.json`.  This is
read-only with respect to the qualified package. Geometry remains integer DBU.
"""
import hashlib
import json
from pathlib import Path
import sys


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def export(package, output):
    import odb
    package = Path(package).resolve()
    source = package / 'native/6_final.odb'
    db = odb.dbDatabase.create()
    odb.read_db(db, str(source))
    block = db.getChip().getBlock()
    die = block.getDieArea()
    terms = {}
    for term in block.getBTerms():
        net = term.getNet()
        pins = []
        for pin in term.getBPins():
            for box in pin.getBoxes():
                pins.append({'layer': box.getTechLayer().getName(),
                             'rect': [box.xMin(), box.yMin(), box.xMax(), box.yMax()]})
        drivers, sinks = [], []
        if net:
            for t in net.getITerms():
                entry = {'instance': t.getInst().getName(), 'master': t.getInst().getMaster().getName(),
                         'pin': t.getMTerm().getName()}
                (drivers if t.getIoType() == 'OUTPUT' else sinks).append(entry)
        terms[term.getName()] = {'direction': term.getIoType(), 'native_net': net.getName() if net else None,
                                 'signal_type': term.getSigType(), 'shapes': pins,
                                 'drivers': drivers, 'sinks': sinks}
    macros = []
    cells = {}
    for inst in block.getInsts():
        master = inst.getMaster()
        cells[master.getName()] = cells.get(master.getName(), 0) + 1
        if master.isBlock():
            b = inst.getBBox()
            macros.append({'instance': inst.getName(), 'master': master.getName(),
                           'rect': [b.xMin(), b.yMin(), b.xMax(), b.yMax()],
                           'orientation': inst.getOrient()})
    out = {'schema_version': 'native-pin-inventory/1', 'top': block.getName(),
           'dbu_per_micron': block.getDbUnitsPerMicron(),
           'die': [die.xMin(), die.yMin(), die.xMax(), die.yMax()],
           'files': {str(p.relative_to(package)): {'sha256': sha(p), 'bytes': p.stat().st_size}
                     for p in sorted((package / 'native').glob('6_final.*'))},
           'terms': terms, 'macros': macros, 'cells': cells,
           'physical_qualified': False, 'scope': 'read-only inventory, not joint-top acceptance'}
    Path(output).write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({'top': out['top'], 'terminals': len(terms), 'macros': len(macros),
                      'm10_terminals': sum(any(s['layer'] == 'metal10' for s in t['shapes']) for t in terms.values())}))


if __name__ == '__main__':
    if len(sys.argv) == 5 and sys.argv[1] == '--tsv':
        tsv, package, output = Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
        terms, macros, cells = {}, [], {}
        for row in tsv.read_text().splitlines():
            fields = row.split('\t'); tag, values = fields[0], fields[1:]
            if tag == 'DESIGN':
                top, dbu, *die = values
            elif tag == 'TERM':
                name, direction, net, sig = values
                terms[name] = {'direction': direction, 'native_net': net, 'signal_type': sig,
                               'shapes': [], 'drivers': [], 'sinks': []}
            elif tag == 'SHAPE':
                name, layer, *coords = values
                terms[name]['shapes'].append({'layer': layer, 'rect': list(map(int, coords))})
            elif tag == 'OWNER':
                name, direction, instance, master, pin = values
                terms[name]['drivers' if direction == 'OUTPUT' else 'sinks'].append(
                    {'instance': instance, 'master': master, 'pin': pin})
            elif tag == 'CELL':
                cells[values[0]] = cells.get(values[0], 0) + 1
            elif tag == 'MACRO':
                instance, master, orientation, *coords = values
                macros.append({'instance': instance, 'master': master, 'orientation': orientation,
                               'rect': list(map(int, coords))})
            else:
                raise ValueError('unknown inventory record')
        result = {'schema_version': 'native-pin-inventory/1', 'top': top, 'dbu_per_micron': int(dbu),
                  'die': list(map(int, die)), 'terms': terms, 'macros': macros, 'cells': cells,
                  'files': {str(p.relative_to(package)): {'sha256': sha(p), 'bytes': p.stat().st_size}
                            for p in sorted((package/'native').glob('6_final.*'))},
                  'physical_qualified': False, 'scope': 'read-only inventory, not joint-top acceptance'}
        output.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'top': top, 'terminals': len(terms), 'macros': len(macros),
                          'm10_terminals': sum(any(s['layer']=='metal10' for s in t['shapes']) for t in terms.values())}))
    else:
        export(sys.argv[1], sys.argv[2])
