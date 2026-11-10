"""Compile a probe of the actual generated shared_pool.hpp; compare independently.

Run only inside an allocated server job. No performance estimate is produced.
"""
import argparse
import json
from pathlib import Path
import subprocess
import traceback

from numeric_reference import cases, compare, digest, evidence, write_input


PROBE = r'''
#define SC_INCLUDE_DYNAMIC_PROCESSES
#include <systemc>
#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
using namespace sc_core;
using U=uint64_t;
constexpr U C=1000;
U now(){return sc_time_stamp().value();}
U ceildiv(U a,U b){return (a+b-1)/b;}
void pause_until(U t){if(t>now()){wait(sc_time::from_value(t-now()));}}
void require(bool v,const char* s){if(!v){throw std::runtime_error(s);}}
struct Calendar {
 std::vector<std::pair<U,U>> slots;U busy=0,queue_wait=0,calls=0;
 U reserve(U at,U duration){
  auto z=std::remove_if(slots.begin(),slots.end(),[](auto p){return p.second<=now();});slots.erase(z,slots.end());
  U start=at;size_t i=0;
  for(;i<slots.size();++i){if(start+duration<=slots[i].first){break;}start=std::max(start,slots[i].second);}
  slots.insert(slots.begin()+static_cast<long>(i),{start,start+duration});
  busy+=duration;queue_wait+=start-at;++calls;return start+duration;
 }
};
#include "shared_pool.hpp"
struct Case {
 int id,rows,k,cols,bits,cap,fifo,contexts,shift,tile_k;
 std::vector<std::vector<int64_t>> A,B;
};
int64_t rne(__int128 x,int shift){
 bool neg=x<0;unsigned __int128 v=neg?-x:x;
 unsigned __int128 q=v>>shift,rem=v-(q<<shift),half=(static_cast<unsigned __int128>(1)<<shift);
 if(rem*2>half||(rem*2==half&&(q&1))){++q;}
 __int128 value=neg?-static_cast<__int128>(q):static_cast<__int128>(q);
 return value>2147483647?2147483647:value<(-static_cast<__int128>(2147483647)-1)?-2147483648:static_cast<int64_t>(value);
}
struct Tile {
 U id;int worker,start,count,col,lanes;
 std::vector<std::vector<int64_t>> values;
 std::vector<std::vector<bool>> seen;
};
struct Probe:sc_module {
 std::vector<Case> inputs;std::ofstream events,results;std::map<std::pair<int,int>,std::unique_ptr<shared_pool::Pool>> pools;bool passed=false;
 SC_HAS_PROCESS(Probe);
 Probe(sc_module_name n,const char* input,const char* event_path,const char* result_path):sc_module(n),events(event_path),results(result_path){
  std::ifstream f(input);int count;f>>count;
  for(int i=0;i<count;++i){Case c;f>>c.id>>c.rows>>c.k>>c.cols>>c.bits>>c.cap>>c.fifo>>c.contexts>>c.shift>>c.tile_k;
   c.A.resize(c.rows,std::vector<int64_t>(c.k));c.B.resize(c.cols,std::vector<int64_t>(c.k));
   for(auto& row:c.A){for(auto& v:row){f>>v;}}
   for(auto& row:c.B){for(auto& v:row){f>>v;}}
   inputs.push_back(std::move(c));}
  require(bool(f)&&bool(events)&&bool(results),"probe input/output");SC_THREAD(run);
 }
 void run(){
  std::vector<std::string> rejected;
  auto reject=[&](const char* name,const std::function<void()>& test){bool caught=false;try{test();}catch(const std::runtime_error&){caught=true;}require(caught,"negative pool control escaped");rejected.push_back(name);};
  shared_pool::Pool bad;bad.configure(32768,1,2,1);bad.begin(4096,1,7,4,256);
  reject("missing_fill",[&]{bad.filled();});
  reject("read_before_fill",[&]{bad.feed(0,0,1,0,7);});
  reject("padding_write",[&]{bad.write(now(),28,4);});
  U ack=bad.write(now()+10000,0,28);
  reject("duplicate_fill_byte",[&]{bad.write(now(),0,4);});
  reject("early_fill_ack",[&]{bad.filled();});pause_until(ack);bad.filled();
  reject("out_of_range_read",[&]{bad.feed(0,0,1,0,8);});
  bool first=true;bad.on_issue=[&](const shared_pool::Issued&){if(first){first=false;
   reject("early_epoch_release",[&]{bad.end();});
   reject("overwrite_live_epoch",[&]{bad.begin(4096,1,7,4,256);});
   reject("reconfigure_live_epoch",[&]{bad.configure(49152,1,2,1);});
   reject("reuse_live_consumer_fifo",[&]{bad.feed(0,0,1,0,7);});
  }};bad.feed(0,0,1,0,7);bad.on_issue=nullptr;bad.end();
  U sequence=0;const U base=4096;
  results<<"{\"cases\":[";bool comma=false;
  for(const auto& c:inputs){
   auto key=std::make_pair(c.cap,c.fifo);if(!pools.count(key)){pools[key].reset(new shared_pool::Pool);}auto& pool=*pools[key];
   pool.configure(c.cap,c.fifo,2,1);require(pool.begin(base,c.rows,c.k,4,256),"probe pool disabled");
   U epoch=pool.epoch,last=now();
   for(U r=0;r<pool.rows;++r){for(U at=0;at<pool.prefix_k*4;at+=64){last=pool.write(last,r*pool.stride+at,std::min<U>(64,pool.prefix_k*4-at));}}
   pause_until(last);pool.filled();
   events<<"{\"kind\":\"begin\",\"case\":"<<c.id<<",\"epoch\":"<<epoch<<",\"prefix_k\":"<<pool.cached_k()<<",\"stride\":"<<pool.stride<<",\"time\":"<<now()<<"}\n";
   std::array<Tile*,2> active{{nullptr,nullptr}};
   std::vector<std::vector<__int128>> partial(c.rows,std::vector<__int128>(c.cols));
   pool.consumer_ready_at=[&](const shared_pool::Consumed& e){
    U offset=(e.source_address-base-e.row*c.k*4)/4;
    U stall=offset==0?5:offset+e.bytes/4==static_cast<U>(c.k)?7:(offset/8)%11==0?3:0;
    return e.consumed_at+stall*C;
   };
   pool.on_issue=[&](const shared_pool::Issued& e){
    events<<"{\"kind\":\"issue\",\"case\":"<<c.id<<",\"worker\":"<<e.worker<<",\"tile\":"<<e.tile_id<<",\"epoch\":"<<e.epoch
     <<",\"pool\":"<<e.pool_address<<",\"bytes\":"<<e.bytes<<",\"issued\":"<<e.issued_at<<",\"ready\":"<<e.ready_at
     <<",\"release\":"<<e.credit_release_at<<",\"outstanding\":"<<e.outstanding<<"}\n";
   };
   pool.on_consume=[&](const shared_pool::Consumed& e){
    require(e.worker>=0&&e.worker<2&&active[e.worker],"consume without active tile");auto& t=*active[e.worker];
    require(e.epoch==epoch&&e.tile_id==t.id&&e.row<static_cast<U>(c.rows),"consume epoch/tile/row mismatch");
    require(e.bytes&&e.bytes<=32&&e.bytes%4==0&&e.source_address%4==0,"consume element mask");
    const U rowbase=base+e.row*c.k*4;
    require(e.source_address>=rowbase+U(t.start)*4&&e.source_address+e.bytes<=rowbase+U(t.start+t.count)*4,"consume range");
    U ki=(e.source_address-rowbase)/4;
    for(U v=0;v<e.bytes/4;++v){U local=ki+v-t.start;require(!t.seen[e.row][local],"duplicate consumed element");
     t.seen[e.row][local]=true;t.values[e.row][local]=c.A[e.row][ki+v];}
    events<<"{\"kind\":\"consume\",\"case\":"<<c.id<<",\"worker\":"<<e.worker<<",\"tile\":"<<e.tile_id<<",\"epoch\":"<<e.epoch
     <<",\"row\":"<<e.row<<",\"source\":"<<e.source_address<<",\"pool\":"<<e.pool_address<<",\"bytes\":"<<e.bytes
     <<",\"ready\":"<<e.ready_at<<",\"consumed\":"<<e.consumed_at<<"}\n";
   };
   std::vector<sc_process_handle> jobs;
   for(int w=0;w<2;++w){jobs.push_back(sc_spawn([&,w]{
    std::vector<int> selected;for(int col=0;col<c.cols;col+=8){if((col/16)%2==w){selected.push_back(col);}}
    for(size_t group=0;group<selected.size();group+=c.contexts){
     const size_t stop=std::min(selected.size(),group+static_cast<size_t>(c.contexts));
     for(int ki=0;ki<c.k;ki+=c.tile_k){for(size_t slot=group;slot<stop;++slot){
      const int count=std::min(c.tile_k,c.k-ki),col=selected[slot],lanes=std::min(8,c.cols-col);
      // Unequal pre-tile stalls exercise consumer skew and independent epochs.
      pause_until(now()+U((c.id+ki/256+col/8+w*3)%7)*C);
      Tile tile{++sequence,w,ki,count,col,lanes,
       std::vector<std::vector<int64_t>>(c.rows,std::vector<int64_t>(count)),
       std::vector<std::vector<bool>>(c.rows,std::vector<bool>(count,false))};active[w]=&tile;
      U shared=ki<static_cast<int>(pool.cached_k())?std::min<U>(count,pool.cached_k()-ki):0;
      U local_ready=shared&&shared<static_cast<U>(count)?now()+600*C:0;
      events<<"{\"kind\":\"tile\",\"case\":"<<c.id<<",\"worker\":"<<w<<",\"tile\":"<<tile.id<<",\"start\":"<<ki<<",\"count\":"<<count<<",\"col\":"<<col<<",\"local_ready\":"<<local_ready<<"}\n";
      U got=pool.feed(w,0,c.rows,ki,count,tile.id,local_ready),seen=0;
      for(int row=0;row<c.rows;++row){for(int j=0;j<count;++j){
       U address=base+(U(row)*c.k+ki+j)*4;
       if(tile.seen[row][j]){require(pool.covered(address,4)==4,"delivered outside pool");seen+=4;}
       else{require(pool.covered(address,4)==0,"pool skipped an element");tile.values[row][j]=c.A[row][ki+j];}
      }}
      require(got==seen,"feed byte receipt differs from actual consumer events");
      for(int row=0;row<c.rows;++row){for(int lane=0;lane<lanes;++lane){for(int j=0;j<count;++j){
       partial[row][col+lane]+=static_cast<__int128>(tile.values[row][j])*c.B[col+lane][ki+j];
      }}}
      events<<"{\"kind\":\"endtile\",\"case\":"<<c.id<<",\"worker\":"<<w<<",\"tile\":"<<tile.id<<",\"bytes\":"<<got<<",\"time\":"<<now()<<"}\n";active[w]=nullptr;
     }}
    }
   }));}
   for(auto& job:jobs){if(!job.terminated()){wait(job.terminated_event());}}
   require(!active[0]&&!active[1],"probe active after join");pool.on_consume=nullptr;pool.on_issue=nullptr;pool.consumer_ready_at=nullptr;pool.end();
   events<<"{\"kind\":\"end\",\"case\":"<<c.id<<",\"epoch\":"<<epoch<<",\"time\":"<<now()<<"}\n";
   if(comma){results<<",";}comma=true;results<<"{\"id\":"<<c.id<<",\"output\":[";
   for(int row=0;row<c.rows;++row){if(row){results<<",";}results<<"[";for(int col=0;col<c.cols;++col){if(col){results<<",";}results<<rne(partial[row][col],c.shift);}results<<"]";}results<<"]}";
  }
  results<<"],\"negative_controls\":[";for(size_t i=0;i<rejected.size();++i){if(i){results<<",";}results<<"\""<<rejected[i]<<"\"";}results<<"]}\n";
  results.flush();events.flush();passed=true;sc_stop();
 }
};
int sc_main(int argc,char** argv){
 try{require(argc==4,"probe arguments");sc_set_time_resolution(1,SC_PS);Probe p("probe",argv[1],argv[2],argv[3]);sc_start();require(p.passed,"probe incomplete");return 0;}
 catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
'''


def check_events(path, values):
    by_id = {v['id']: v for v in values}
    active, epochs, covered, last_consume, next_k = {}, {}, {}, {}, {}
    pool_epochs, outstanding, last_issue, service = {}, {}, {}, []
    counts = dict(events=0, tiles=0, consumed_bytes=0, epochs=0, issued_reads=0, credit_peak=0)
    for line in Path(path).open(encoding='utf8'):
        e = json.loads(line)
        counts['events'] += 1
        c = by_id[e['case']]
        whole_stride = ((c['k'] * 4 + 63) // 64) * 64
        expected_k = (c['k'] if whole_stride * c['rows'] <= c['capacity_bytes'] else
                      (c['capacity_bytes'] // c['rows'] // 4 // 256) * 256)
        stride = ((expected_k * 4 + 63) // 64) * 64
        kind = e['kind']
        if kind == 'begin':
            assert not active and e['prefix_k'] == expected_k and e['stride'] == stride
            pool_key = (c['capacity_bytes'], c['fifo_beats'])
            assert e['epoch'] == pool_epochs.get(pool_key, 0) + 1, 'epoch not advanced on reused DDR address'
            pool_epochs[pool_key] = e['epoch']
            epochs[e['case']] = e['epoch']
            counts['epochs'] += 1
        elif kind == 'tile':
            key = (e['case'], e['worker'])
            assert key not in active
            assert (e['col'] // 16) % 2 == e['worker'], 'wrong column ownership'
            assert e['start'] == next_k.get((e['case'], e['col']), 0), 'K discontinuity'
            active[key] = e
            covered[e['tile']] = set()
            counts['tiles'] += 1
        elif kind == 'issue':
            key = (e['case'], e['worker'])
            t = active[key]
            assert e['tile'] == t['tile'] and e['epoch'] == epochs[e['case']]
            assert 0 < e['bytes'] <= 64 and e['pool'] % 64 + e['bytes'] <= 64
            assert e['issued'] >= last_issue.get(key, -1000) + 1000, 'more than one issue per P per cycle'
            last_issue[key] = e['issued']
            live = [time for time in outstanding.get(key, []) if time > e['issued']]
            assert e['release'] >= e['ready'] + 1000
            live.append(e['release'])
            assert len(live) == e['outstanding'] and len(live) <= c['fifo_beats'], 'in-flight plus returned credit overflow'
            outstanding[key] = live
            counts['credit_peak'] = max(counts['credit_peak'], len(live))
            counts['issued_reads'] += 1
            # Fixed two-cycle read response and one-cycle 64B/4-bank service.
            service.append((e['ready'] - 3000, e['ready'] - 2000))
            assert service[-1][0] >= e['issued'], 'response before physical bank service'
        elif kind == 'consume':
            key = (e['case'], e['worker'])
            t = active[key]
            assert e['tile'] == t['tile'] and e['epoch'] == epochs[e['case']]
            assert 0 < e['bytes'] <= 32 and e['bytes'] % 4 == 0
            assert 0 <= e['row'] < c['rows']
            offset = e['source'] - (4096 + e['row'] * c['k'] * 4)
            assert offset >= 0 and offset % 4 == 0
            ki = offset // 4
            assert t['start'] <= ki and ki + e['bytes'] // 4 <= min(t['start'] + t['count'], expected_k)
            assert e['pool'] == e['row'] * stride + ki * 4
            assert e['consumed'] >= e['ready'] + 1000, 'read response not ready'
            assert e['consumed'] >= last_consume.get(key, 0) + 1000, 'A feeder exceeds 32B/cycle'
            last_consume[key] = e['consumed']
            for k in range(ki, ki + e['bytes'] // 4):
                item = (e['row'], k)
                assert item not in covered[e['tile']], 'duplicate delivered element'
                covered[e['tile']].add(item)
            counts['consumed_bytes'] += e['bytes']
        elif kind == 'endtile':
            key = (e['case'], e['worker'])
            t = active.pop(key)
            assert t['tile'] == e['tile']
            wanted = {(row, k) for row in range(c['rows'])
                      for k in range(t['start'], min(t['start'] + t['count'], expected_k))}
            assert covered.pop(e['tile']) == wanted, 'missing or excess shared prefix elements'
            assert e['bytes'] == len(wanted) * 4
            assert e['time'] >= last_consume.get(key, 0), 'retired before last consumer'
            if t['local_ready']:
                shared_k = max(0, min(t['start'] + t['count'], expected_k) - t['start'])
                local_cycles = ((t['count'] - shared_k) * 4 + 31) // 32
                assert e['time'] >= t['local_ready'] + c['rows'] * local_cycles * 1000, 'mixed tile consumed local tail before local S response'
            next_k[(e['case'], t['col'])] = t['start'] + t['count']
        elif kind == 'end':
            assert not active and not covered and e['epoch'] == epochs[e['case']]
            assert all(next_k.get((e['case'], col)) == c['k'] for col in range(0, c['columns'], 8))
        else:
            raise AssertionError('unknown probe event ' + kind)
    assert len(epochs) == len(values) and not active and not covered
    ordered = sorted(service)
    assert all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])), 'two consumers received free simultaneous 1RW-bank service'
    assert counts['credit_peak'] == 4, 'depth-four credit occupancy not exercised'
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--cxx', default='g++')
    parser.add_argument('--systemc-prefix', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    report = dict(passed=False, scope='Actual conditional shared_pool.hpp consumer-address path with synthetic S32/W8/W16 data; independent whole-K Fraction RNE reference; no RTL/full-model numeric proof')
    try:
        values = cases()
        write_input(out / 'input.txt', values)
        (out / 'probe.cpp').write_text(PROBE, encoding='utf8')
        command = [args.cxx, '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', '-pthread', str(out / 'probe.cpp'),
                   '-I' + str(args.model.resolve()), '-I' + str(args.systemc_prefix / 'include'),
                   '-L' + str(args.systemc_prefix / 'lib'),
                   '-Wl,-rpath,' + str(args.systemc_prefix / 'lib'),
                   '-lsystemc', '-o', str(out / 'probe')]
        with (out / 'compile.log').open('w', encoding='utf8') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        with (out / 'run.log').open('w', encoding='utf8') as log:
            subprocess.run([str(out / 'probe'), str(out / 'input.txt'), str(out / 'events.jsonl'),
                            str(out / 'actual.json')], stdout=log, stderr=subprocess.STDOUT, check=True)
        actual = json.loads((out / 'actual.json').read_text())
        report['output_comparisons'] = compare(actual['cases'], values)
        expected_negative = {'missing_fill', 'read_before_fill', 'padding_write', 'duplicate_fill_byte',
                             'early_fill_ack', 'out_of_range_read', 'early_epoch_release',
                             'overwrite_live_epoch', 'reconfigure_live_epoch', 'reuse_live_consumer_fifo'}
        assert set(actual['negative_controls']) == expected_negative
        report['negative_controls'] = actual['negative_controls']
        report['events'] = check_events(out / 'events.jsonl', values)
        report.update(passed=True, cases=evidence(values), compile_command=command,
                      model_header_sha256=digest(args.model / 'shared_pool.hpp'),
                      source_sha256={p.name: digest(p) for p in (Path(__file__), Path(__file__).with_name('numeric_reference.py'))},
                      artifact_sha256={p.name: digest(p) for p in out.iterdir() if p.is_file() and p.name != 'result.json'},
                      limitations=['Pool probe supplies synthetic payload by the actual reported consumer source address; original scheduler is timing-only.',
                                   'Deterministic pre-tile skew and in-feed first/middle/tail stalls are exercised through the actual consumer_ready_at hook.',
                                   'No DDR timing is modeled by this probe; main SystemC workload tests separately validate fill routing and DDR ledgers.'])
    except Exception as exc:
        report.update(error=str(exc), traceback=traceback.format_exc())
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(passed=report['passed'], result=str(out / 'result.json'))))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
