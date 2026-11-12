"""Capture and check registered DMA offers in the pinned #251 RTL test."""
import argparse
import json
from pathlib import Path

from dma_offer import DmaOfferChannel


def instrument(source, destination):
    driver = source.read_text(encoding='utf-8')
    anchor = ' if(!t.reset){\n  uint8_t mfire='
    if driver.count(anchor) != 1:
        raise ValueError('expected unique sample point in the #251 typed DMA driver')
    # The RTL stays unchanged. Read the registered beat table from Verilator
    # 4.038 and use only external VALID, READY and tag for the observed offers.
    sample = ''' if(!t.reset){
  for (int ch = 0; ch < 2; ++ch) {
   uint32_t reserved = 0;
   for (int entry = 0; entry < 32; ++entry)
    if (t.mc_dma_fabric_typed_p__DOT__b_state[32*ch + entry] == 1)
     reserved |= uint32_t(1) << entry;
   int cancel = t.mc_dma_fabric_typed_p__DOT__cancel_entry;
   if (t.mc_dma_fabric_typed_p__DOT__cancel_good && cancel / 32 == ch)
    reserved &= ~(uint32_t(1) << (cancel % 32));
   trace << "OFFER_SAMPLE," << cycle << "," << ch << "," << reserved << ","
         << ((t.d_req_ready >> (2*ch)) & 3);
   for (int lane = 2*ch; lane < 2*ch + 2; ++lane) {
    int entry = int((u64(t.d_req_tag, lane*2) >> 10) & 63);
    if ((t.d_req_valid >> lane) & 1)
     need(entry / 32 == ch, "offer uses entry from wrong channel");
    trace << "," << (((t.d_req_valid >> lane) & 1) ? entry % 32 : -1);
   }
   trace << "\\n";
  }
  uint8_t mfire='''
    with destination.open('x', encoding='utf-8') as output:
        output.write(driver.replace(anchor, sample))


def check_trace(lines):
    states = [DmaOfferChannel(), DmaOfferChannel()]
    cycles = [3, 3]  # The pinned driver samples four reset edges before cycle 4.
    observed_issues = {}
    predicted_issues = {}
    counts = dict(samples=0, issues=0, held_lane_ticks=0, held_blocks_refill=0)
    example = None
    for line in lines:
        if line.startswith('ISSUE,'):
            _, cycle, _, _, lane, tag = line.rstrip().split(',')
            key = int(cycle), int(lane)
            if key in observed_issues:
                raise ValueError(f'duplicate DMA issue at {key}')
            observed_issues[key] = (int(tag) >> 10) & 63
        if not line.startswith('OFFER_SAMPLE,'):
            continue
        _, cycle, ch, reserved, ready, lane0, lane1 = line.rstrip().split(',')
        cycle, ch, reserved, ready, lane0, lane1 = map(int, (cycle, ch, reserved, ready, lane0, lane1))
        if ch not in (0, 1) or cycle != cycles[ch] + 1 or not 0 <= ready < 4 or not 0 <= reserved < 2**32:
            raise ValueError(f'discontinuous DMA sample at cycle {cycle}, channel {ch}')
        state = states[ch]
        observed = tuple(None if entry == -1 else entry for entry in (lane0, lane1))
        if observed != state.entries:
            raise ValueError(f'offer mismatch at cycle {cycle}, channel {ch}: RTL={observed}, replay={state.entries}')
        for lane, entry in enumerate(state.entries):
            if entry is not None and ready & (1 << lane):
                predicted_issues[cycle, 2*ch + lane] = 32*ch + entry
        held = sum(entry is not None and not (ready & (1 << lane))
                   for lane, entry in enumerate(observed))
        nxt = state.advance(reserved, ready)
        refill_without_hold = min(2-held, 4-state.previous_issues-nxt.previous_issues, reserved.bit_count())
        actual_refills = sum(new is not None and (old is None or ready & (1 << lane))
                             for lane, (new, old) in enumerate(zip(nxt.entries, state.entries)))
        if refill_without_hold > actual_refills:
            counts['held_blocks_refill'] += 1
            if example is None:
                example = {'cycle': cycle, 'channel': ch, 'previous_issues': state.previous_issues,
                           'issued': nxt.previous_issues, 'held': held, 'reserved': reserved.bit_count()}
        counts['samples'] += 1
        counts['issues'] += nxt.previous_issues
        counts['held_lane_ticks'] += held
        states[ch], cycles[ch] = nxt, cycle
    if cycles[0] == 3 or cycles[0] != cycles[1] or any(s.entries != (None, None) for s in states):
        raise ValueError('DMA offer trace is missing, incomplete or did not drain')
    if predicted_issues != observed_issues:
        raise ValueError('DMA handshakes disagree with the original ISSUE records')
    return {**counts, 'first_held_block': example}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prepare = sub.add_parser('instrument')
    prepare.add_argument('source', type=Path)
    prepare.add_argument('destination', type=Path)
    check = sub.add_parser('check')
    check.add_argument('logs', type=Path, nargs='+')
    args = parser.parse_args()
    if args.command == 'instrument':
        instrument(args.source, args.destination)
    else:
        outcomes = []
        for path in args.logs:
            with path.open(encoding='utf-8') as source:
                outcomes.append({'log': path.name, **check_trace(source)})
        print(json.dumps(outcomes, indent=2))


if __name__ == '__main__':
    main()
