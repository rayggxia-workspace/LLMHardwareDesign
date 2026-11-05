from pathlib import Path
h=Path(__file__).parent
s=(h/'control162-config581-remote.py').read_text(encoding='utf-8').replace('r256-final-chain-binding-audit-581','r256-final-chain-binding-audit-592')
start=s.index(' mappings=');end=s.index('\n for record,seeds',start)
s=s[:start]+" mappings=[('sready589-zero-pattern-controlled',[5890])]"+s[end:]
s=s.replace("'Read-only final-chain binding audit of all12 current S5380 candidate configurations and84 immutable task specifications.","'Read-only final-chain binding audit of current S5380 candidate5890 and7 immutable task specifications.")
(h/'control162-config592-remote.py').write_bytes(s.encode())
