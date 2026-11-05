"""Read only the documented SSH endpoint banner, without authentication."""
import socket,json,time
from pathlib import Path
from datetime import datetime,timezone

d=dict(time=datetime.now(timezone.utc).isoformat(),endpoint='10.129.166.172:22')
start=time.monotonic()
try:
    with socket.create_connection(('10.129.166.172',22),timeout=8)as conn:
        d['tcp_connected_seconds']=time.monotonic()-start
        conn.settimeout(8)
        d['initial_server_banner']=conn.recv(256).decode('ascii',errors='replace')
except OSError as err:
    d['error']=str(err)
d['elapsed_seconds']=time.monotonic()-start
line=json.dumps(d,ensure_ascii=False)
with Path(__file__).with_suffix('.jsonl').open('a',encoding='utf-8')as f:f.write(line+'\n')
print(line)
