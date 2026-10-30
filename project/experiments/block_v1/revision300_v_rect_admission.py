"""Admit only the selected one-RECT V final queues, no retry/cancellation."""
import revision300_admission as admission

if __name__ == "__main__":
    admission.RUNS = tuple("block-v1-20261031-"+n for n in ("804","805","806"))
    admission.main()
