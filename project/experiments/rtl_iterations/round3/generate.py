"""Prepare the finite R3 service and original PR241 K16 leaf; no EDA here."""
import argparse
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
LEAF_SHA='20169790ef33176da607adfcb9f1c5847b457eec6aeaec8800ff212f7cab47d4'
LEAF_GIT_BLOB='071485d7040abe07a9bf3ad7791db02dc62197f8'
UPSTREAM_COMMIT='189e43c77a6277955c1be54281b0d6b0b0d55c1f'
STORE_PATH='project/rtl/s_sram/block_feed_s16k_sram.sv'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def generate(repo,out):
    repo,out=Path(repo).resolve(),Path(out).resolve()
    if sha(HERE/'m_s32_stream_candidate.sv')!=LEAF_SHA:
        raise ValueError('original PR241 leaf drift')
    text=(HERE/'r3_m_finite.sv').read_text(encoding='utf-8')
    if text.count('m_s32_stream_candidate #(.K(16),.N(8),.ROWS(8)) leaf(')!=1:
        raise ValueError('exactly one original K16 leaf required')
    if not (repo/STORE_PATH).is_file():raise ValueError('actual four-bank SRAM controller missing')
    out.mkdir(parents=True,exist_ok=False)
    for name in ('r3_m_finite.sv','m_s32_stream_candidate.sv'):
        (out/name).write_bytes((HERE/name).read_bytes())
    report=dict(schema_version=1,upstream_commit=UPSTREAM_COMMIT,leaf_git_blob=LEAF_GIT_BLOB,
        candidate_sha256={name:sha(out/name) for name in ('r3_m_finite.sv','m_s32_stream_candidate.sv')},
        dependency_sha256={STORE_PATH:sha(repo/STORE_PATH)},
        P_S_bytes=16384,S_bank_count=4,S_bank_mode='1RW',S_max_operation_bytes=64,
        source_packet_bytes=256,packet_buffer_choices=[1,2],completion_reservations=8,
        S_read_response_metadata_slots=2,final_write_words=2,final_write_word_bytes=16,
        full_P_DMA_integration=False,physical_qualified=False,
        scope='Optional finite S32/W8/S96 local service; actual SRAM is externally connected; no DDR source, native P16 replacement or physical claim')
    (out/'generation.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(generate(args.repo,args.out)))
