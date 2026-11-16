// Make an alternate legal V11 arrangement locally at each terminal, then use CUGR between their exits.
struct EntryAlternative {Node exit;Route wires;};

Route try_legal_entries(const Net& original,Board& board,Router& coarse) {
    vector<vector<EntryAlternative>> alternatives(original.pins.size());
    vector<int> order(original.pins.size());
    iota(order.begin(),order.end(),0);
    for(int j:order) {
        auto& options=alternatives[j];
        const auto p=original.pins[j];
        if(on_track(p))options.push_back({p,{}});
        auto alone=original;
        alone.pins={p};
        for(const auto& stem:portals(p,original,board.occupied,{},180)) {
            const auto point=stem.back();
            if(point.layer!=0||key(point)==key(p))continue;
            Route route;
            append_path(route,original,stem);
            if(legal_route(alone,route,board.occupied))options.push_back({point,move(route)});
        }
        if(options.empty())return {};
    }
    stable_sort(order.begin(),order.end(),[&](int a,int b){return alternatives[a].size()<alternatives[b].size();});
    board.tracks.use_pads(original);
    for(int change=0;change<10;++change) {
        auto synthetic=original;
        Route stems;
        unordered_set<uint64_t> used;
        bool assigned=true;
        for(int j:order) {
            const auto& options=alternatives[j];
            bool found=false;
            size_t advance=(j%2?change:change/2)%options.size();
            for(size_t k=0;k<options.size();++k) {
                const auto& option=options[(advance+k)%options.size()];
                if(used.count(key(option.exit)))continue;
                bool conflict=false;
                for(auto v:option.wires.vias)for(auto w:stems.vias)if(via_conflict(v,w))conflict=true;
                if(conflict)continue;
                synthetic.pins[j]=option.exit;
                used.insert(key(option.exit));
                stems=attach_entry(move(stems),option.wires);
                found=true;break;
            }
            if(!found){assigned=false;break;}
        }
        if(!assigned)continue;
        auto testing=coarse.run(synthetic,board.occupied);
        if(testing.status!=connected)continue;
        auto combined=attach_entry(move(testing.route),stems);
        if(legal_route(original,combined,board.occupied))return combined;
    }
    return {};
}
