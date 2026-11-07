"""Apply the explicit standalone I/O timing budget to one mapped configuration."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'control_timing_v0_1'))
import close

if __name__ == '__main__':
    close.HERE = HERE
    close.main()
