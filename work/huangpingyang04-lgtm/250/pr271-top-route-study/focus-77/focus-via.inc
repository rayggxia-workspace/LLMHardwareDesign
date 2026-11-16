// Reuse the CUGR fine maze while testing alternate V11 cut positions.
struct ViaTrial {
    Route route;
    vector<Node> bans;
    array<int,4> first_pair{-1,-1,-1,-1};
    int attempts=0;
    bool other_geometry=false;
};

ViaTrial fix_v11(const Net& n,Board& board,FastMaze& maze,int cap=28,const Route* stem=nullptr) {
    ViaTrial answer;
    board.tracks.use_pads(n);
    vector<vector<Node>> queue(1);
    unordered_set<string> seen;
    for(size_t i=0;i<queue.size()&&answer.attempts<cap;++i) {
        const auto banned=queue[i];
        maze.graph.load(n,board.occupied);
        for(auto v:banned)maze.graph.forbid_via(v);
        ++answer.attempts;
        if(!maze.route(n.pins.size()))continue;
        auto path=maze.extract(n);
        if(stem) {
            path.wires.insert(path.wires.end(),stem->wires.begin(),stem->wires.end());
            for(auto v:stem->vias)if(none_of(path.vias.begin(),path.vias.end(),[&](auto p){return p.x==v.x&&p.y==v.y;}))
                path.vias.push_back(v);
        }
        if(legal_route(n,path,board.occupied)) {answer.route=move(path);answer.bans=banned;return answer;}
        bool found=false;
        for(size_t a=0;a<path.vias.size()&&!found;++a)for(size_t b=0;b<a&&!found;++b) {
            auto u=path.vias[a],v=path.vias[b];
            if(!via_conflict(u,v))continue;
            found=true;
            if(answer.first_pair[0]<0)answer.first_pair={u.x,u.y,v.x,v.y};
            if(banned.size()>=5)continue;
            auto push=[&](vector<Node> next) {
                sort(next.begin(),next.end(),[](auto x,auto y){return key(x)<key(y);});
                next.erase(unique(next.begin(),next.end(),[](auto x,auto y){return key(x)==key(y);}),next.end());
                string identity;
                for(auto bit:next)identity+=to_string(key(bit))+',';
                if(seen.insert(identity).second)queue.push_back(move(next));
            };
            if(banned.empty()&&!stem) {
                // Preserve one usable cut and discourage near-identical V11 moves on the same track.
                for(auto keep:{u,v}) {
                    vector<Node> region;
                    const bool vertical=abs(u.y-v.y)>=abs(u.x-v.x);
                    for(int d=1-via_spacing;d<via_spacing;++d)if(d) {
                        Node k{keep.x+(vertical?0:d),keep.y+(vertical?d:0),0};
                        if(board.occupied.fits(k))region.push_back(k);
                    }
                    push(move(region));
                }
                vector<Node> replace_both;
                const bool vertical=abs(u.y-v.y)>=abs(u.x-v.x);
                for(int d=1-via_spacing;d<via_spacing;++d) {
                    Node k{u.x+(vertical?0:d),u.y+(vertical?d:0),0};
                    if(board.occupied.fits(k))replace_both.push_back(k);
                }
                push(move(replace_both));
            }
            for(auto point:{u,v}) {
                if(stem&&any_of(stem->vias.begin(),stem->vias.end(),[&](auto k){return k.x==point.x&&k.y==point.y;}))continue;
                vector<Node> next=banned;
                point.layer=0;next.push_back(point);
                push(move(next));
            }
        }
        if(!found)answer.other_geometry=true;
    }
    return answer;
}
