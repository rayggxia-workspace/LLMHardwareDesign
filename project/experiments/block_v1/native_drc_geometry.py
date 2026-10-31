"""Exact orthogonal marker/rectangle overlap after the read-only native scan.

This narrows geometry candidates. It does not establish GDS connectivity or
grant a DRC waiver; all original markers, bounding hits and ambiguities survive.
"""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import re


def vertices(geometry):
    assert geometry.startswith('polygon: ')
    tokens=list(filter(None,re.split(r'[(),;\s]+',geometry.split(': ',1)[1])))
    assert len(tokens)>=8 and len(tokens)%2==0
    coords=[Fraction(t)*2000 for t in tokens]
    assert all(x.denominator==1 for x in coords),'Polygon is off the native DBU grid'
    points=[(int(coords[i]),int(coords[i+1]))for i in range(0,len(coords),2)]
    assert all((a[0]==b[0])!=(a[1]==b[1])for a,b in zip(points,points[1:]+points[:1]))
    return points


def overlap(points,box):
    """Integer DBU area by exact vertical slabs, including concave indentations."""
    x0,y0,x1,y1=box;assert x0<x1 and y0<y1
    cuts=sorted({x0,x1}|{x for x,y in points if x0<x<x1})
    area=0
    for left,right in zip(cuts,cuts[1:]):
        twice_mid=left+right
        ys=sorted(a[1]for a,b in zip(points,points[1:]+points[:1])
                  if a[1]==b[1]and 2*min(a[0],b[0])<twice_mid<2*max(a[0],b[0]))
        assert len(ys)%2==0
        for lo,hi in zip(ys[::2],ys[1::2]):
            assert lo<hi
            area+=(right-left)*max(0,min(hi,y1)-max(lo,y0))
    return area


def diagnose(index,summary):
    artifacts=index['tasks']['native-drc-locate-c']['artifacts']
    artifact=artifacts['native-drc-location.json']
    receipt=artifacts['receipt.json']['content'];assert receipt['passed']is True
    assert receipt['outputs']['native-drc-location.json']==artifact['sha256']
    located=artifact['content'];assert located['passed']is True
    assert located['report_sha256']==summary['report_sha256']
    assert located['marker_count']==len(located['markers'])==summary['total_items']
    rows=[]
    for row in located['markers']:
        marker=row['marker'];number=marker['index'];original=summary['items'][number]
        assert marker['category']==original['category']
        assert marker['original_geometry']in original['values']
        if not marker['category'].endswith('_ANTENNA'):continue
        points=vertices(marker['original_geometry'])
        box=[min(p[k]for p in points)for k in (0,1)]+[max(p[k]for p in points)for k in (0,1)]
        twice_area=abs(sum(a[0]*b[1]-b[0]*a[1]for a,b in zip(points,points[1:]+points[:1])))
        assert 2*overlap(points,box)==twice_area>0
        hits=[dict(**hit,intersection_area_dbu2=overlap(points,hit['bbox_dbu']))for hit in row['hits']]
        candidates=sorted({h['net']for h in hits if h['intersection_area_dbu2']>0})
        assert set(candidates)<=set(row['candidate_nets'])
        rows.append(dict(index=number,category=marker['category'],original_geometry=marker['original_geometry'],
            bounding_candidate_nets=row['candidate_nets'],positive_area_candidate_nets=candidates,
            fields=original['float_fields'],hits=hits))
    nets=sorted({net for row in rows for net in row['positive_area_candidate_nets']})
    return dict(schema='block-v1-native-drc-polygon-diagnosis/1',passed=True,
        locator_sha256=artifact['sha256'],source_odb_sha256=located['source_odb_sha256'],
        drc_report_sha256=summary['report_sha256'],antenna_markers=len(rows),
        unresolved=[row['index']for row in rows if len(row['positive_area_candidate_nets'])!=1],
        narrowed=[row['index']for row in rows if row['bounding_candidate_nets']!=row['positive_area_candidate_nets']],
        input_networks={net:located['terminals'][net]for net in nets},markers=rows,
        scope='Exact orthogonal marker/native conductor rectangle overlap only; no proof of GDS electrical connectivity, diode capacity, etch sequence or repaired DRC')


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('locator_index',type=Path);parser.add_argument('drc_summary',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();assert not args.output.exists()
    result=diagnose(json.loads(args.locator_index.read_text()),json.loads(args.drc_summary.read_text()))
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({key:result[key]for key in ['antenna_markers','unresolved','narrowed']}))
