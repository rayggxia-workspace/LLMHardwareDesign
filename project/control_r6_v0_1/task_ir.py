"""Parse a bounded RAW16/P task graph for the deployed R4 interface."""
from dataclasses import dataclass
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
TARGET = json.loads((HERE / "target.json").read_text(encoding="utf-8"))
SCHEMA = "control-task-ir/0.1"


class IRValidationError(ValueError):
    """An input error reported before image assembly."""


def require(condition, path, detail):
    if not condition:
        raise IRValidationError(f"{path}: {detail}")


def fields(value, names, path):
    require(isinstance(value, dict) and set(value) == set(names.split()),
            path, f"expected exactly these fields: {names}")


def integer(value, low, high, path):
    require(type(value) is int and low <= value <= high, path,
            f"expected integer in [{low}, {high}]")


def identifier(value, path):
    require(isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,47}", value),
            path, "expected a lowercase identifier of at most 48 characters")


@dataclass(frozen=True)
class Buffer:
    name: str
    block: int
    address: int
    completion_token: int


@dataclass(frozen=True)
class Transfer:
    name: str
    edge: int
    source: str
    sink: str
    receive_token: int
    send_token: int | None
    after_ack: tuple[str, ...]


@dataclass(frozen=True)
class Ready:
    transfer: str
    event_id: int
    local_register: int
    mother_register: int
    value: int


@dataclass(frozen=True)
class Graph:
    name: str
    image_ids: tuple[int, int, int]  # mother, LC0, LC1
    buffers: tuple[Buffer, Buffer]  # indexed by block
    transfers: tuple[Transfer, Transfer]  # ordered by physical edge
    ready: Ready
    wait_groups: tuple[tuple[str, ...], ...]


def parse_ir(raw):
    fields(raw, "schema name target images buffers transfers ready wait_groups", "$")
    require(raw["schema"] == SCHEMA, "$.schema", "unsupported IR version")
    require(raw["target"] == TARGET["id"], "$.target", "unsupported hardware target")
    identifier(raw["name"], "$.name")
    fields(raw["images"], "mother local0 local1", "$.images")
    image_ids = []
    for role in ("mother", "local0", "local1"):
        value = raw["images"][role]
        integer(value, 1, 0xffffffff, "$.images." + role)
        image_ids.append(value)
    require(len(set(image_ids)) == 3, "$.images", "image IDs must be distinct")

    buffers = raw["buffers"]
    require(isinstance(buffers, list) and len(buffers) == 2,
            "$.buffers", "one RAW16 buffer on each of the two local controllers is required")
    by_block = {}
    names = {}
    for i, item in enumerate(buffers):
        path = f"$.buffers[{i}]"
        fields(item, "name block address bytes completion_token", path)
        name = item["name"]
        identifier(name, path + ".name")
        require(name != "host" and name not in names, path + ".name", "reserved or duplicate buffer name")
        block = item["block"]
        integer(block, 0, 1, path + ".block")
        require(block not in by_block, path + ".block", "only one object slot per local controller")
        address = item["address"]
        size = TARGET["object_bytes"]
        integer(item["bytes"], size, size, path + ".bytes")
        integer(address, 0, TARGET["s_bytes_per_block"] - size, path + ".address")
        require(address % size == 0, path + ".address", "RAW16 address must be 16-byte aligned")
        token = item["completion_token"]
        integer(token, 0, TARGET["global_token_count"] - 1, path + ".completion_token")
        entry = Buffer(name, block, address, token)
        by_block[block] = entry
        names[name] = entry
    require(by_block[0].completion_token != by_block[1].completion_token,
            "$.buffers", "both active calls require distinct completion credits")

    transfers = raw["transfers"]
    require(isinstance(transfers, list) and len(transfers) == 2,
            "$.transfers", "target requires exactly the two provisioned RAW16 edges")
    by_edge = {}
    transfer_names = set()
    routes = {r["edge"]: (r["source"], r["sink"]) for r in TARGET["routes"]}
    for i, item in enumerate(transfers):
        path = f"$.transfers[{i}]"
        fields(item, "name edge source sink bytes receive_token send_token after_ack", path)
        name = item["name"]
        identifier(name, path + ".name")
        require(name not in transfer_names, path + ".name", "duplicate transfer name")
        transfer_names.add(name)
        edge = item["edge"]
        require(type(edge) is int and edge in routes and edge not in by_edge,
                path + ".edge", "unknown or duplicate physical edge")
        source, sink = item["source"], item["sink"]
        identifier(source, path + ".source")
        identifier(sink, path + ".sink")
        require((source == "host" or source in names) and sink in names,
                path, "unknown transfer endpoint")
        src_block = TARGET["host"] if source == "host" else names[source].block
        require((src_block, names[sink].block) == routes[edge], path,
                "endpoints do not match the provisioned route")
        integer(item["bytes"], TARGET["object_bytes"], TARGET["object_bytes"], path + ".bytes")
        receive = item["receive_token"]
        send = item["send_token"]
        integer(receive, 0, TARGET["local_token_count"] - 1, path + ".receive_token")
        if source == "host":
            require(send is None, path + ".send_token", "host has no local send credit")
        else:
            integer(send, 0, TARGET["local_token_count"] - 1, path + ".send_token")
        dependencies = item["after_ack"]
        require(isinstance(dependencies, list) and all(isinstance(x, str) for x in dependencies),
                path + ".after_ack", "expected list of transfer names")
        by_edge[edge] = Transfer(name, edge, source, sink, receive, send, tuple(dependencies))
    ingress, forward = (by_edge[r["edge"]] for r in TARGET["routes"])
    require(not ingress.after_ack and forward.after_ack == (ingress.name,),
            "$.transfers.after_ack", "forward must depend on exactly the ingress store ACK")

    ready = raw["ready"]
    fields(ready, "transfer event_id local_register mother_register value", "$.ready")
    require(ready["transfer"] == forward.name, "$.ready.transfer",
            "consumer must report READY for the forward edge")
    integer(ready["event_id"], 0, TARGET["event_id_count"] - 1, "$.ready.event_id")
    for field in ("local_register", "mother_register"):
        integer(ready[field], 0, TARGET["register_count"] - 1, "$.ready." + field)
    integer(ready["value"], 0, 0xffffffff, "$.ready.value")

    groups = raw["wait_groups"]
    require(isinstance(groups, list) and 1 <= len(groups) <= 2,
            "$.wait_groups", "expected one or two completion groups")
    joined = []
    for i, group in enumerate(groups):
        require(isinstance(group, list) and 1 <= len(group) <= 2 and
                all(isinstance(x, str) and x in names for x in group),
                f"$.wait_groups[{i}]", "expected active buffer names")
        joined.extend(group)
    require(sorted(joined) == sorted(names), "$.wait_groups",
            "each task completion must be consumed exactly once")
    return Graph(raw["name"], tuple(image_ids), (by_block[0], by_block[1]),
                 (ingress, forward), Ready(**ready), tuple(tuple(g) for g in groups))


def load_ir(path):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, "$", f"duplicate JSON key {key!r}")
            value[key] = item
        return value

    try:
        raw = json.loads(pathlib.Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise IRValidationError(f"invalid UTF-8 JSON: {exc}") from exc
    return parse_ir(raw)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=pathlib.Path)
    args = parser.parse_args()
    try:
        graph = load_ir(args.input)
    except (IRValidationError, OSError) as exc:
        parser.exit(2, f"{exc}\n")
    print(f"Admitted {graph.name} for {TARGET['id']}")
