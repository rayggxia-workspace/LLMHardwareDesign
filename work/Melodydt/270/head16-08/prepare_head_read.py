"""Pipeline the serialized vocabulary read on a matching accepted SRAM response."""

import argparse
from hashlib import sha256
from pathlib import Path


EXPECTED = {
    "s128_vocabulary_retire.sv": "fdc13fa7f793804368ac37c3403192784a09a774686f07064986ba860c1cddd0",
    "s128_vocabulary_tile_consumer.sv": "94d42412765695cecd090115fcc3a8f77a4301f988ead5582ca1374badc64e89",
    "native_vocabulary_product_terminal.sv": "3b50343641bb24d78e5544e66263fb356f030260143755f768da8aa1ab8434b4",
}


def edit(source, old, new):
    if source.count(old) != 1:
        raise ValueError("unexpected source context: " + old)
    return source.replace(old, new, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    root = args.source / "project/rtl/block_local_native"
    sources = {}
    for name, seal in EXPECTED.items():
        data = (root / name).read_bytes()
        if sha256(data).hexdigest() != seal:
            raise ValueError("sealed vocabulary path changed: " + name)
        sources[name] = data.decode("utf-8").replace("\r\n", "\n")

    name = "s128_vocabulary_retire.sv"
    source = sources[name]
    source = edit(source, "    output wire [31:0] s_read_tag,", 
                  "    output wire [31:0] s_read_tag,\n    output wire [31:0] s_expected_rsp_tag,")
    source = edit(source, "s_rsp_tag==s_read_tag", "s_rsp_tag==next_index")
    source = edit(source, "    assign s_read_valid=!reset && state==ISSUE;\n    assign s_read_address=address;\n    assign s_read_tag=next_index;",
                  """    // The response is identified by next_index. A replacement request
    // may accept on that edge without changing the retiring tag.
    wire replace_read=state==RESPONSE && s_rsp_valid && s_rsp_ready && valid_response && remaining>4;
    assign s_read_valid=!reset && (state==ISSUE || replace_read);
    assign s_read_address=address+10'(replace_read);
    assign s_read_tag=next_index+(replace_read ? 32'd4 : 32'd0);
    assign s_expected_rsp_tag=next_index;""")
    source = edit(source, "                        state<=ISSUE;",
                  "                        state<=s_read_ready ? RESPONSE : ISSUE;")
    sources[name] = source

    name = "s128_vocabulary_tile_consumer.sv"
    source = edit(sources[name], "wire bad_response=s_rsp_error||s_rsp_tag!=s_read_tag;",
                  "wire [31:0] rsp_owner;\n    wire bad_response=s_rsp_error||s_rsp_tag!=rsp_owner;")
    sources[name] = edit(source, ".s_read_address,.s_read_tag,.s_rsp_valid",
                         ".s_read_address,.s_read_tag,.s_expected_rsp_tag(rsp_owner),.s_rsp_valid")
    name = "native_vocabulary_product_terminal.sv"
    sources[name] = edit(sources[name], "s_rsp_error||s_rsp_tag!=s_read_tag||s_rsp_tag!=consumed",
                         "s_rsp_error||s_rsp_tag!=consumed")
    for name, source in sources.items():
        (root / name).write_text(source, encoding="utf-8")
    for file, port in (
        ("systemc_benchmark/native_token_embedding_fixture.sv", ".s_read_tag(logit_tag),"),
        ("block_local_native/test_native_projection_live.sv", ".s_read_tag(arg_read_tag),"),
        ("block_local_native/test_s128_vocabulary_retire.sv", ".s_read_address,.s_read_tag,"),
    ):
        path = args.source / "project/experiments" / file
        if path.is_file():
            path.write_text(edit(path.read_text(encoding="utf-8"), port,
                                 port + " .s_expected_rsp_tag(),"), encoding="utf-8")


if __name__ == "__main__":
    main()
