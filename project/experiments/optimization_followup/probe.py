"""Run unchanged independent payload/FIFO checks on the followup header."""
from pathlib import Path
from generate import load

if __name__=='__main__':
    load(Path(__file__).resolve().parent.parent/'optimization_sweep/probe.py','followup_parent_probe').main()
