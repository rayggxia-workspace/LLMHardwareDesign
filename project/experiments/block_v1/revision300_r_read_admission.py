"""Admit only the shared-read R validation/physical/final/interface queues."""
import revision300_admission as admission

if __name__ == '__main__':
    admission.RUNS=tuple('block-v1-20261101-'+n for n in ('826','827','828','829'))
    admission.main()
