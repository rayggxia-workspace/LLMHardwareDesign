"""Read existing child placement transforms from frozen P/J ODBs, once each."""
import json
import os
from pathlib import Path
import subprocess

from lower_inventory import sha

BASE=Path('/public/home/yuzelu/PingyangHuang')

def main():
    out=Path(os.environ['LOWER_OUT']);out.mkdir()
    refs=json.loads((BASE/'issue-215-top-pex-zOz2uxIr/route-206.json').read_text());result={}
    for kind,children in [('P0',['store','multiply','gate']),('J0',['store','lease','arithmetic'])]:
        odb=Path(refs['native_masks'][kind]['path']).with_suffix('.odb')
        text='read_db {'+str(odb)+'}\nset b [ord::get_db_block]\nset fp [open positions.tsv w]\n'
        text+='puts $fp "DBU\\t[$b getDbUnitsPerMicron]"\n'
        for name in children:
            text+='set i [$b findInst {'+name+'}]\nif {$i eq "NULL"} {error "Missing accepted child"}\n'
            text+='set t [$i getTransform]\nset xy {}\nforeach pair {{0 0} {1000000 0} {0 1000000}} {\nset p [odb::new_Point {*}$pair]\n$t apply $p\nlappend xy [$p getX] [$p getY]\nodb::delete_Point $p\n}\n'
            text+='puts $fp "'+name+'\\t[join $xy \\t]"\n'
        text+='close $fp\nputs CHILD_POSITIONS_COMPLETE\nexit\n'
        folder=out/kind;folder.mkdir();script=folder/'positions.tcl';script.write_text(text)
        with (folder/'openroad.log').open('xb') as f:subprocess.run(['openroad','-no_init','-exit',str(script.resolve())],cwd=folder,stdout=f,stderr=subprocess.STDOUT,check=True)
        lines=(folder/'positions.tsv').read_text().splitlines();dbu=int(lines[0].split()[1]);rows={}
        for line in lines[1:]:
            name,*v=line.split();ox,oy,xx,yx,xy,yy=map(float,v)
            matrix=[[(xx-ox)/1e6,(xy-ox)/1e6],[(yx-oy)/1e6,(yy-oy)/1e6]]
            assert all(x in [-1.,0.,1.] for r in matrix for x in r)
            rows[name]=dict(offset_um=[ox/dbu,oy/dbu],matrix=matrix)
        assert set(rows)==set(children)
        result[kind]=dict(source_odb=str(odb),source_odb_sha256=sha(odb),transforms=rows,positions_sha256=sha(folder/'positions.tsv'))
    (out/'positions.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)

if __name__=='__main__':main()
