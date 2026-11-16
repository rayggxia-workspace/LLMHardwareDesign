// The same branch scarcity order is available to transactions after the empty pass.
vector<int> group_priority(const vector<Net>& nets,int mode) {
    const char* filename=getenv("GROUP_PROBES");
    if(!filename)throw runtime_error("Group repair requires branch probes");
    ifstream probes(filename);
    string header;
    getline(probes,header);
    vector<int> fewest(nets.size(),4),sum(nets.size()),seen(nets.size()),span(nets.size());
    int i,pin,choices,distance;
    while(probes>>i>>pin>>choices>>distance) {
        if(pin<1||pin>=int(nets.at(i).pins.size())||choices<0||choices>3)
            throw runtime_error("Invalid group probe");
        fewest[i]=min(fewest[i],choices);
        sum[i]+=choices;
        ++seen[i];
        span[i]=max(span[i],distance);
    }
    if(!probes.eof())throw runtime_error("Malformed group probe file");
    for(const auto& n:nets)if(seen[n.id]!=int(n.pins.size())-1)throw runtime_error("Missing group probe data");
    vector<int> ids(nets.size());
    iota(ids.begin(),ids.end(),0);
    auto rank=[&](int id) {
        const int cover=12*sum[id]/seen[id];
        const int tiebreak=mode==0?span[id]:mode==1?-span[id]:id;
        return make_tuple(fewest[id],cover,tiebreak,id);
    };
    stable_sort(ids.begin(),ids.end(),[&](int a,int b){return rank(a)<rank(b);});
    return ids;
}
