from pathlib import Path
h=Path(__file__).parent
for old,new in [(637,640),(638,641)]:
 s=(h/('control162-refill'+str(old)+'-remote.py')).read_text(encoding='utf-8').replace('sready'+str(old)+'-directional-bidirectional-refill','sready'+str(new)+'-directional-bidirectional-refill').replace("'source-400',0)","'source-407',0)").replace('older359/source400','older359/source407')
 (h/('control162-refill'+str(new)+'-remote.py')).write_bytes(s.encode())
