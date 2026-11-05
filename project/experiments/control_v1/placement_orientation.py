"""Rigid native geometry transforms; preserve the declared upper-grid phase."""

def shift(size, rotation):
    w,h=size
    assert rotation in range(4)
    return [(0.,0.),(.165-w%4,-.025),(.19-w%4,.14-h%4),(.025,.165-h%4)][rotation]


def transform(point,size,rotation):
    x,y=point;w,h=size
    assert rotation in range(4)
    return [(x,y),(w-y,x),(w-x,h-y),(y,h-x)][rotation]
