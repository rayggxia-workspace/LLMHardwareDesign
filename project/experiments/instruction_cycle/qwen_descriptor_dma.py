"""Source-derived native typed DMA for the drained 105530 page-one prefix.

Cycles count elapsed core edges before the sampled edge, as in the native
DDR trace. The service side owns a two-beat record through its final returned
beat. Shared arbitration with an unrelated active client requires a wider
fabric model.
"""

from qwen_native_ddr import require


BURST_BYTES = 64
RECORD_BYTES = 128
SLOTS_PER_CHANNEL = 32
DESCRIPTOR_CRC_BYTES = 124


class TypedReadFabric:
    """Model the isolated-client states of mc_dma_fabric_typed_p."""

    def __init__(self, ddr):
        self.ddr = ddr
        # The fixture's reset purge advances transport_generation from 1 to 2
        # before accepting native calls and leaves all beat serials at zero.
        self.generation = 2
        self.serials = [0] * (2 * SLOTS_PER_CHANNEL)
        self.last_response = -1
        self.open_record = None

    @property
    def mode(self):
        return self.ddr.mode

    def _allocate(self, entry, client):
        self.serials[entry] += 1
        serial = self.serials[entry]
        require(serial <= 65535, "typed beat serial rollover requires a transport fence")
        return (self.generation << 32) | (serial << 16) | (entry << 10) | (client << 6)

    def _entry(self, offer_cycle, client, local_tag, address):
        require(type(offer_cycle) is int and offer_cycle > self.last_response,
                "typed transfer overlaps another active client or response")
        require(type(client) is int and 0 <= client < 9 and type(local_tag) is int
                and 0 <= local_tag < 1 << 32 and type(address) is int and 0 <= address < 1 << 34
                and address % BURST_BYTES == 0, "invalid typed record beat")
        base = address - (local_tag & 1) * BURST_BYTES
        require(base % RECORD_BYTES == 0, "native typed record must be aligned")
        identity = (client, local_tag & ~1, base)
        if local_tag & 1:
            require(self.open_record == identity, "typed beat has no matching reserved first half")
            self.open_record = None
        else:
            require(self.open_record is None, "another typed record is open")
            self.open_record = identity
        return (base >> 11) & 1

    def read_serial(self, offer_cycle, client, local_tag, address, *, response_ready=None):
        channel = self._entry(offer_cycle, client, local_tag, address)
        # With one client and no live beat, the lowest entry is free. RESERVED
        # and OFFERED each occupy a registered edge before the physical gate.
        global_tag = self._allocate(channel * SLOTS_PER_CHANNEL, client)
        lane = 2 * channel
        phy_ready_cycle = offer_cycle + 2
        admitted = phy_ready_cycle + int(self.mode and (phy_ready_cycle + lane) % 5 == 0)
        returned = self.ddr.read(phy_ready_cycle, lane, global_tag, address)
        response = returned + 1  # the response skid is registered
        if response_ready is not None:
            while not response_ready(response):
                response += 1
                require(response - returned < 4096, "typed client held its return skid")
        self.last_response = response
        return {"client_accept": offer_cycle, "phy_admit": admitted, "phy_return": returned,
                "client_response": response, "global_tag": global_tag, "lane": lane}

    def read_descriptor(self, offer_cycle, client, local_tag, address):
        require(local_tag % 2 == 0 and self.open_record is None, "descriptor requires a complete fresh record")
        phy_ready_cycle = offer_cycle + 2
        lane = 2 * ((address >> 11) & 1)
        require(not self.mode or (phy_ready_cycle + lane) % 5,
                "first typed descriptor beat needs a sibling lane during its physical stall")
        channel = self._entry(offer_cycle, client, local_tag, address)
        first_entry = channel * SLOTS_PER_CHANNEL
        # The next half reserves the second entry while the first is live.
        # As the first physical offer is consumed, the second takes its lane.
        first_tag = self._allocate(first_entry, client)
        second_tag = self._allocate(first_entry + 1, client)
        admitted, returned = self.ddr.read_pair(phy_ready_cycle, lane,
                                                [(first_tag, address), (second_tag, address + BURST_BYTES)])
        responses = [cycle + 1 for cycle in returned]
        self.last_response = responses[-1]
        self.open_record = None
        return {"client_accepts": [offer_cycle, offer_cycle + 1], "phy_admits": admitted, "phy_returns": returned,
                "client_responses": responses, "global_tags": [first_tag, second_tag], "lane": lane}


def fetch_descriptor(fabric, call, offer_cycle, serial=1, *, provider_ready=None):
    """Return source admission, DDR lifecycle and LC provider timing for a P0 call."""
    require(call["target"] == 0 and type(serial) is int and 0 < serial < 1 << 31,
            "unsupported serial descriptor source")
    address = call["descriptor_address"]
    tag = serial << 1
    result = fabric.read_descriptor(offer_cycle, 0, tag, address)
    # Each descriptor half is copied directly from its registered skid into
    # the LC parameter register. The final copy enters the CRC state. Its 124
    # scans exclude the stored CRC, then DONE crosses into SERVICE_OFFER.
    assembled = result["client_responses"][-1]
    crc_complete = assembled + DESCRIPTOR_CRC_BYTES
    provider_offer = crc_complete + 2
    accepted = provider_offer
    if provider_ready is not None:
        while not provider_ready(accepted):
            accepted += 1
            require(accepted - provider_offer < 4096, "provider held the verified descriptor")
    result.update(descriptor_address=address, local_tags=[tag, tag + 1], assembled=assembled,
                  crc_complete=crc_complete, provider_offer=provider_offer, service_accept=accepted)
    return result
