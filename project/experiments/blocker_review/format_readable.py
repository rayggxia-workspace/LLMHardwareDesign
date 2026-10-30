"""Format display copies only; all raw native gzip bytes remain unchanged."""
from pathlib import Path
import csv,io,sys
out=Path(sys.argv[1]);changed=0
for p in (out/'evidence').rglob('*'):
 if not p.is_file() or 'readable' not in p.parts:continue
 before=p.read_text(encoding='utf-8')
 if p.suffix=='.tsv':
  rows=list(csv.reader(io.StringIO(before),delimiter='\t'));s=io.StringIO();csv.writer(s,delimiter='\t',lineterminator='\n',quoting=csv.QUOTE_ALL).writerows(rows);after=s.getvalue()
  assert list(csv.reader(io.StringIO(after),delimiter='\t'))==rows
 else:after=before.rstrip()+'\n'
 if before!=after:p.write_text(after,encoding='utf-8',newline='\n');changed+=1
print('FORMATTED_DISPLAY_COPIES_ONLY',changed,'raw gzip unchanged; decoded TSV values identical')
