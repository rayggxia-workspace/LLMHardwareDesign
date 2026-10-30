"""Admission for only the three new V repair queues; R's original controller stays."""
import revision300_admission as admission

if __name__=='__main__':
    admission.RUNS=tuple('block-v1-20261031-'+n for n in('766','767','768'))
    admission.main()
