"""Preserve every independent DRC item and summarize without waiving rules."""
import collections
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def summarize(path):
    raw=Path(path).read_bytes();root=ET.fromstring(raw)
    assert root.tag=='report-database'
    items=root.find('items');assert items is not None
    rows=[]
    for item in items:
        category=item.findtext('category');assert category
        category=category.strip("'")
        values=[v.text or '' for v in item.findall('values/value')]
        fields={}
        for value in values:
            match=re.fullmatch(r'\[#([^\]]+)\] float: (.+)',value)
            if match:
                key,text=match.groups();assert key not in fields
                number=float(text);assert math.isfinite(number)
                fields[key]=number
        rows.append(dict(category=category,cell=item.findtext('cell'),
                         multiplicity=item.findtext('multiplicity'),values=values,float_fields=fields))
    return dict(schema='block-v1-independent-drc-summary/1',
        report_sha256=hashlib.sha256(raw).hexdigest(),report_bytes=len(raw),
        top_cell=root.findtext('top-cell'),total_items=len(rows),
        categories=dict(sorted(collections.Counter(row['category']for row in rows).items())),
        items=rows,scope='Exact independent deck items, including antenna and native metal spacing; no exclusions or waivers')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('report',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();assert not args.output.exists()
    result=summarize(args.report)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ['report_sha256','total_items','categories']}))
