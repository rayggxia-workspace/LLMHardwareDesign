"""Hash actual native timing sources; source-directory policy is input data."""
import argparse
import json
from pathlib import Path
from native_inventory import sha


def build(package,inventory,view_directory,platform):
    package=Path(package);view_directory=Path(view_directory);platform=Path(platform)
    inv=json.loads(Path(inventory).read_text())
    def reference(path):return {'path':str(path.resolve()),'sha256':sha(path)}
    libs=[platform/'lib/NangateOpenCellLibrary_typical.lib']
    libs+=sorted(p for p in view_directory.rglob('*.lib') if p.name!='NangateOpenCellLibrary_typical.lib')
    lefs=[platform/'lef/NangateOpenCellLibrary.tech.lef',platform/'lef/NangateOpenCellLibrary.macro.mod.lef']
    candidates=[p for p in view_directory.rglob('*.lef') if not p.name.endswith('.tech.lef')]
    # Use the source's exact physical pin abstract when supplied alongside its
    # ordinary abstract; no hand-edited geometry is created here.
    for p in sorted(candidates):
        if p.with_name(p.stem+'-exact.lef').exists():continue
        lefs.append(p)
    result={'top':inv['top'],'liberties':list(map(reference,libs)),'lefs':list(map(reference,lefs))}
    for kind,suffix in [('odb','odb'),('netlist','v'),('spef','spef'),('sdc','sdc')]:
        path=package/'native'/('6_final.'+suffix)
        assert sha(path)==inv['files']['native/6_final.'+suffix]['sha256']
        result[kind]=reference(path)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('package','inventory','view_directory','platform','output'):p.add_argument(n,type=Path)
    a=p.parse_args();result=build(a.package,a.inventory,a.view_directory,a.platform)
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
