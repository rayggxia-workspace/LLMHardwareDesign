// Select a mutually legal set from fine-maze candidates without dropping any seed net.
#define main adapter_main
#include "transactional-maze.cpp"
#undef main
#include <random>

struct Choice {int net; Route route; vector<int> conflicts;};

class Selection {
    const vector<Choice>& choices;
    const vector<vector<int>>& alternatives;
    vector<int> selected;
    vector<bool> pinned;
    vector<pair<int,int>> trail;
    int maximum, search;

    void change(int net,int new_choice) {
        trail.emplace_back(net,selected[net]);
        selected[net]=new_choice;
    }
    void undo(size_t before) {
        while(trail.size()>before) {
            const auto [n,c]=trail.back();
            selected[n]=c;
            trail.pop_back();
        }
    }

    bool assign(vector<int>& pending,size_t index) {
        if(index==pending.size())return true;
        if(--search<0)return false;
        const int net=pending[index];
        vector<pair<size_t,int>> options;
        for(int candidate:alternatives[net]) {
            size_t impact=0;
            bool clear=true;
            for(int other:choices[candidate].conflicts) {
                const int owner=choices[other].net;
                if(selected[owner]!=other)continue;
                if(pinned[owner]) {clear=false;break;}
                ++impact;
            }
            if(clear&&pending.size()+impact<=size_t(maximum+1))options.emplace_back(impact,candidate);
        }
        stable_sort(options.begin(),options.end(),[](auto a,auto b){return a.first<b.first;});
        for(const auto [_,candidate]:options) {
            const size_t before=trail.size(), old_pending=pending.size();
            for(int other:choices[candidate].conflicts) {
                const int owner=choices[other].net;
                if(selected[owner]!=other)continue;
                change(owner,-1);
                pending.push_back(owner);
            }
            pinned[net]=true;
            change(net,candidate);
            if(assign(pending,index+1)) {pinned[net]=false;return true;}
            pinned[net]=false;
            pending.resize(old_pending);
            undo(before);
        }
        return false;
    }

public:
    Selection(const vector<Choice>& pool,const vector<vector<int>>& available,vector<int> start)
      :choices(pool),alternatives(available),selected(move(start)),pinned(selected.size()) {}
    int get(int id) const {return selected[id];}
    bool add(int net,int cap) {
        if(selected[net]>=0||alternatives[net].empty())return false;
        maximum=cap;
        search=2600;
        vector<int> pending{net};
        const bool ok=assign(pending,0);
        if(!ok&&(!trail.empty()||selected[net]>=0))throw runtime_error("Failed candidate transaction leaked");
        trail.clear();
        return ok;
    }
    int count() const {return count_if(selected.begin(),selected.end(),[](int v){return v>=0;});}
};

int main(int argc,char** argv) {
    if(argc<6)return 2;
    const auto nets=read_nets(argv[1]);
    const auto seed=read_paths(argv[2],nets.size());
    const int depth=stoi(argv[4]);
    if(depth<=0)return 2;
    Board fixed(nets);
    vector<Choice> choices;
    vector<vector<int>> alternatives(nets.size());
    vector<int> start(nets.size(),-1);
    Occupancy index;
    auto load=[&](const vector<Route>& routes,bool starting) {
        for(const auto& n:nets) {
            const auto& r=routes[n.id];
            if(!has_route(r))continue;
            if(!legal_route(n,r,fixed.occupied)) {
                if(starting)throw runtime_error("Starting route failed static geometry");
                continue;
            }
            auto& group=alternatives[n.id];
            if(any_of(group.begin(),group.end(),[&](int c){return same_route(choices[c].route,r);}))continue;
            const int id=choices.size();
            group.push_back(id);
            choices.push_back({n.id,r,{}});
            index.add_route(id,r);
            if(starting)start[n.id]=id;
        }
    };
    load(seed,true);
    for(int file=5;file<argc;++file)load(read_paths(argv[file],nets.size()),false);
    Board fake(vector<Net>{});
    fake.occupied=move(index);
    for(size_t id=0;id<choices.size();++id) {
        auto& c=choices[id];
        c.conflicts=blockers(fake,id,c.route);
        c.conflicts.erase(remove_if(c.conflicts.begin(),c.conflicts.end(),[&](int other){
            return choices[other].net==c.net;
        }),c.conflicts.end());
    }
    for(size_t id=0;id<choices.size();++id)for(int other:choices[id].conflicts)
        if(!binary_search(choices[other].conflicts.begin(),choices[other].conflicts.end(),int(id)))
            throw runtime_error("Asymmetric candidate overlap");
    Selection best(choices,alternatives,start);
    auto ids=order_by_span(nets);
    for(int pass=0;pass<5;++pass) {
        const int before=best.count();
        if(pass==1)stable_sort(ids.begin(),ids.end(),[&](int a,int b){return alternatives[a].size()<alternatives[b].size();});
        if(pass>1) {mt19937 random(271+pass);shuffle(ids.begin(),ids.end(),random);}
        for(int id:ids)best.add(id,depth);
        cerr<<"selection pass="<<pass<<" added="<<best.count()-before<<" total="<<best.count()<<'\n';
        if(best.count()==int(nets.size()))break;
    }
    vector<Route> output(nets.size());
    for(const auto& n:nets) {
        const int c=best.get(n.id);
        if(c<0) {
            if(start[n.id]>=0)throw runtime_error("Lost starting net during selection");
            continue;
        }
        const auto& route=choices[c].route;
        if(!legal_route(n,route,fixed.occupied))throw runtime_error("Candidate set failed exact geometry");
        fixed.install(n.id,route);
        output[n.id]=route;
    }
    cerr<<"selection candidates="<<choices.size()<<" final="<<best.count()<<'\n';
    write_routes(argv[3],output);
}
