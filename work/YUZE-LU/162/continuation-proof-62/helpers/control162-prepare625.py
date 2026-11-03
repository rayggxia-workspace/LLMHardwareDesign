from pathlib import Path
h=Path(__file__).parent;s=(h/'control162-config592-remote.py').read_text(encoding='utf-8').replace('r256-final-chain-binding-audit-592','r256-final-chain-binding-audit-625').replace("[('sready589-zero-pattern-controlled',[5890])]", "[('sready614-pattern-weight-controls',[6140,6141])]").replace('current S5380 candidate5890 and7 immutable task specifications','current S5380 candidates6140/6141 and14 immutable task specifications')
(h/'control162-config625-remote.py').write_bytes(s.encode())
