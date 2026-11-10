# Finite shared DMA candidate (Refs #250)

`mc_dma_fabric.sv` is real RTL for nine scope and three W clients, two DDR
channels, each with 32 beat entries and 32 descriptor entries. Entries store
ownership metadata, not returned payload. Return skids are separately counted
64-byte registers. All requests and returns use actual ready/valid; only a
matching client payload ACK returns beat credit. CLOSE closes missing future
issues, while already accepted requests must still issue and return. Explicit
reservation cancellation has a separate ACK and cannot withdraw an offered
backend VALID. Actual backend purge, including startup after reset and serial
exhaustion, is mandatory.

The four physical DDR ports are two per channel. Admission of each held offer
reserves the strict rolling window: previous actual issues + current actual
issues + old/new unacknowledged offers <= 4. At most two offers/channel are
held; all three-cycle actual issue windows are independently checked <= 4.
The saturated theoretical rate is 51.2 GB/s at 300 MHz, subject to finite source
and return service. Source acceptance is earlier than actual DDR issue, and
client ACK is later than return capture; they are not interchangeable events.

The original four fixed-lane skids passed ownership tests but achieved about
87.2% of that nominal rate in the original random-OOO three-M pressure test.
A client has only one64B return port, so fixed DDR-lane landing caused blocking.
An attempted pressure-aware issue arbiter did not help and is not in the
current RTL. Shared landing within channel and finite fair client selection
are now tested at four/six/eight total skids. Eight slots add256B return payload;
six add128B. All extra payload/mux state is counted in MC area. The default is six slots: it passed36runs and independent conservation/service
audits, while shared four slots failed the original service gate. Eight slots
also passed but are retained as a larger reference, not the minimal candidate.
See `DMA_CONTRACT.json` and `work/YUZE-LU/250/weights/dma-*/` for exact sources,
failures, Slurm submissions, compact receipts and independent audits.

Deploy only to a fresh own remote root:

```text
python project/experiments/w8a16_dma/deploy.py --root /public/home/yuzelu/project-circuit/issue250-dma-20261111-NN --receipt work/YUZE-LU/250/weights/dma-NN --skids-per-channel 3
```

Each Slurm job allocates six tasks of ten CPUs, checks strict production RTL,
and executes six seeds x three initial states at serial limits65535 and3.
`collect.py` hashes source/logs/CSVs and can expand on C:; `audit.py` only reads
those receipts locally and independently checks conservation and issue windows.
It does not run local simulation. Current evidence does not qualify complete
M/LC/system integration, MC physical timing/area, or whole-model throughput.
