"""Keep unchanged sampling rows and refresh length/rank for the single moved M10."""
import csv
from pathlib import Path
import sys


def pins(path):
    result=[]
    with Path(path).open() as f:
        n=int(next(f).split()[-1])
        for i in range(n):
            index,p,c=map(int,next(f).split()); assert index==i
            result.append([tuple(map(int,next(f).split())) for _ in range(p)])
            for _ in range(c): next(f)
    return result


previous,new=pins(sys.argv[1]),pins(sys.argv[2]); assert len(previous)==len(new)==1184
changed=[i for i,(a,b) in enumerate(zip(previous,new)) if a!=b]; assert len(changed)==1
with Path(sys.argv[3]).open() as f:
    reader=csv.DictReader(f,delimiter='\t')
    print(*reader.fieldnames,sep='\t')
    for r in reader:
        i,j,w,s=(int(r[k]) for k in reader.fieldnames)
        if i in changed:
            a,b=new[i][0],new[i][j]; s=sum(abs(p-q) for p,q in zip(a,b)); w=1
        print(i,j,w,s,sep='\t')
