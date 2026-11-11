from pathlib import Path
from generate import load

if __name__=='__main__':
    load(Path(__file__).resolve().parent.parent/'optimization_sweep/probe.py','bridge_parent_probe').main()
