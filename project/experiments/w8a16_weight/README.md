# W8-first record frontend candidate (Refs #250)

This unit implements four **register** banks, each 18 × 64 B = 1152 B;
4608 B data plus validity, identities, decode and read mux must be included in
the new M leaf area. It adds no private/shared SRAM. The standalone 1024-bit
W port is an internal M unit interface; it is not a proposed M10 escape bus.
One 64 B DMA response and one 128 B raw-M read may run in the same cycle only
on different banks. This is not a 1RW SRAM claim. Result buffers are external:
the control implementation owns two independent 32 B result slots.

## Byte format and mathematical evidence

An ordinary K128 × N8 record is 1088 B: 1024 B signed W8, then eight little
endian FP16 scales (16 B), then 48 B zero padding. A head record is 1152 B:
the same 1024 B W8 and eight groups of eight FP16 scales (128 B), because
head scaling is per K16. Weight bytes are `[K16 tile][N lane][K lane]`;
one native 128 B operand therefore contains eight rows of sixteen weights.
Ordinary records are one eight-beat K128 raw group; head records are eight
one-beat K16 groups with eight distinct raw tags and matching scale vectors.

`active_n` is 1–8. Inactive W bytes must be zero. Only active FP16 scale
lanes must be positive, finite and nonzero; inactive scale contents are
ignored and the output is canonical zero. Padding is always checked.

`codec.py` reads scalar coordinates directly from frozen public
`Qwen/Qwen2.5-3B-Instruct-GPTQ-Int8` revision
`1fed15cb34975bc0bd699e62b95a539bb06eed42`, model SHA256
`73d70c78b55123ff89d5c3b333f169934703c1fd8138ca1d4942b35b58e2d7d6`.
It independently extracts packed GPTQ qweight/qzeros/g_idx/scales and checks
every W byte against 24 real run38 groups (layers 0/2/17/35, gate/up/down,
first/last K128). Four additional head records use the declared symmetric
head16 derivation from the tied FP16 embedding; these are not native GPTQ
head records. Six actual-weight N-tail records cover N=1/2/7. Encode/decode,
bytewise native W/scales and raw signed integer M dots are all compared.
The Down A fixture is historical Mid64; this is not new Mid32 numerical
qualification. Head A values are directed; no full-head activation claim.

## Bounded state and ownership

Allocation records full key128 `{generation,job,epoch,object_version}`,
logical record32 and a bank generation16. No data reset is needed: every
byte must be returned before a record can become valid. At most 32 DMA
beats may be outstanding across this M frontend's four banks. A chip-wide
MC credit limit must additionally be enforced by the real shared MC ready
arbiter; three per-M counters do not implement a global limit of 32.
Issue and return carry explicit beat,
full key, record and bank generation; reordered returns are accepted once.
`fill_last` marks the highest addressed beat, not return arrival order.
The true held FILLACK must be accepted before READY and native M start.
Wrong/repeated/late commands produce a held bounded fault, without changing
valid ownership or credit. One LC command is accepted per cycle. Real MC
request acceptance is an independent one-beat/cycle port with 32 total
outstanding credits, so alloc/start/input-consumed can overlap another
bank's issue. DMA return acceptance is separately one 64 B beat per cycle.
These finite ports, every actual record setup and external MC latency still
belong in the production timeline; this is not unlimited descriptor issue.
An issue handshake denotes actual MC request acceptance, not a speculative
descriptor. The bridge must rendezvous the real MC ready/valid with this
credit acceptance. Full `(key,record)` identities cannot be reused while old
messages can still arrive; a wrapping finite bank generation is insufficient
by itself to prevent ABA.

Native W output is stable under backpressure. The bank remains leased after
the eighth actual M operand handshake until a matching `input_consumed`
ACK (including `use_sequence`) arrives. It is then reusable independently
of result write ACK. The result owner must carry an independent immutable
ticket; a late result ACK cannot identify work by a reused W-bank generation.
Cancellation stops future issues/operand delivery, drains every already
issued DMA return, and requires a strong external raw/A flush proof before
`drain`. This module does not roll back a partially accumulated M group.
Global reset requires coordinated DMA drain and a fresh full job/epoch key;
finite bank generations alone do not make arbitrarily old reset-era
messages safe.

The old performance model held each W bank until result ACK, despite a
two-result-slot comment. This production candidate frees inputs earlier and
uses the control agent's actual two result slots; it must be recalibrated
with native S128 timing. The conditional historical 9.223 token/s model is
not a qualification for this lifecycle, full S bandwidth, energy or P&R.

## Reproduction and scope

`deploy.py` freezes committed bytes and submits a fresh owned c64 6×10
Slurm run. `job.sh` checks all source SHA256s, hashes the full model once,
then runs six seeds and three initial states with Verilator 5.042. Production
RTL uses strict `--Wall` lint. The harness connects the real `m_group_s32`,
randomizes issue/return order and output stalls, checks credit conservation,
FILLACK/start ordering, tails, malformed scales/padding/weights, duplicate,
wrong generation/use, cancellation with DMA in flight, partial raw flush
and new-identity retry. No simulation is run on login or local hosts.

Latest unit evidence: source `aa490534bc6198fec016de87258523ecc32996ec`,
Slurm 102097, c64 6×10, six seeds × three initial states all passed.
Each run checks 307 native W handshakes and 87 actual raw-M outputs including
directed retries/cancellation; the 34 frozen fixture records independently
contribute 272 native operands and 83 expected raw groups. The receipt
archive and byte-level audit live under `work/YUZE-LU/250/weights/run-05`.
The earlier 102090 harness-exit failure is preserved with its fix and reruns.

This is unit/protocol evidence.
Scale/context/result-storage integration and complete M physical acceptance
remain separate tasks. No claim of whole-model RTL or physical closure.
