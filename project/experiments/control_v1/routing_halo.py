"""Translate a source-bound physical scene without changing relative macros."""
import copy


def expand(scene,halo):
    assert halo in (512,1024,2048)
    result=copy.deepcopy(scene);shift=halo//4
    nx=scene['width_um']//4;ny=scene['height_um']//4
    assert nx*4==scene['width_um']and ny*4==scene['height_um']
    result['width_um']+=2*halo;result['height_um']+=2*halo
    result['placements_um']={n:[x+halo,y+halo]for n,(x,y)in scene['placements_um'].items()}
    external={};mapping={}
    for name,(x,y)in scene['external_grid_pins'].items():
        if x==8:p=(8,y+shift)
        elif x==nx-8:p=(nx+2*shift-8,y+shift)
        elif y==8:p=(x+shift,8)
        else:
            assert y==ny-8;p=(x+shift,ny+2*shift-8)
        assert (x,y)not in mapping;mapping[(x,y)]=p;external[name]=list(p)
    assert len(set(map(tuple,external.values())))==len(external)
    result['external_grid_pins']=external
    result['terminals']={n:[list(mapping.get(tuple(p),(p[0]+shift,p[1]+shift)))for p in points]for n,points in scene['terminals'].items()}
    all_points=[tuple(p)for ends in result['terminals'].values()for p in ends]
    assert len(all_points)==len(set(all_points))
    assert result['orientations']==scene['orientations']and result['graph_sha256']==scene['graph_sha256']
    return result
