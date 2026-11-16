// Sparse, undirected arcs in the identified congested rectangles.
class LocalTracks {
    struct IndexEntry {array<int,3> targets{-1,-1,-1};};
    unordered_map<uint64_t,int> by_coordinate;
    vector<Node> nodes;
    vector<IndexEntry> links;
    vector<int> at_main_vertex;
    vector<int> off_entries;
    const int x0=((llx+pitch-1)/pitch)*pitch;
    const int y0=((lly+pitch-1)/pitch)*pitch;
    const int ny=(ury-y0)/pitch+1;
    int main_vertex(Node n)const{return 2*(((n.x-x0)/pitch)*ny+(n.y-y0)/pitch)+n.layer;}
    int record(Node n) {
        const auto found=by_coordinate.emplace(key(n),nodes.size());
        if(!found.second)return found.first->second;
        const int id=nodes.size();
        nodes.push_back(n); links.emplace_back();
        if(on_track(n))at_main_vertex.at(main_vertex(n))=id;
        return id;
    }
public:
    vector<Node> off_points;
    unordered_map<uint64_t,int> off_vertex;
    explicit LocalTracks(const string& filename) {
        if(filename=="-")return;
        const int nx=(urx-x0)/pitch+1;
        at_main_vertex.resize(2*nx*ny,-1);
        ifstream in(filename);
        if(!in)throw runtime_error("Cannot open the local candidate manifest");
        Node a{},b{};
        int wires=0,vias=0;
        while(in>>a.x>>a.y>>a.layer>>b.x>>b.y>>b.layer) {
            const auto fits=[](Node n){return llx<=n.x&&n.x<=urx&&lly<=n.y&&n.y<=ury&&(n.layer==0||n.layer==1);};
            const bool via=a.layer!=b.layer;
            if(!fits(a)||!fits(b)||(on_track(a)&&on_track(b)))throw runtime_error("Candidate does not add a valid position");
            int forward=1,reverse=0;
            if(via) {
                if(a.x!=b.x||a.y!=b.y)throw runtime_error("Candidate via must be vertical");
                forward=2; reverse=2;
                ++vias;
            } else {
                const bool valid=a.layer==0?a.y==b.y&&a.x<b.x:a.x==b.x&&a.y<b.y;
                if(!valid)throw runtime_error("Invalid candidate wire direction");
                ++wires;
            }
            const int p=record(a), q=record(b);
            if(links[p].targets[forward]!=-1||links[q].targets[reverse]!=-1)
                throw runtime_error("Overlapping local track rectangles");
            links[p].targets[forward]=q;
            links[q].targets[reverse]=p;
        }
        if(!in.eof()||wires==0||vias==0)throw runtime_error("Incomplete local candidate manifest");
        for(size_t i=0;i<nodes.size();++i)if(!on_track(nodes[i])) {
            const auto n=nodes[i];
            off_vertex.emplace(key(n),off_points.size());
            off_points.push_back(n);
            off_entries.push_back(i);
        }
        cerr<<"local_candidates wires="<<wires<<" vias="<<vias<<" off_vertices="<<off_points.size()<<'\n';
    }
    bool allows(Node a,Node b)const {
        const auto p=by_coordinate.find(key(a));
        if(p==by_coordinate.end())return false;
        for(int to:links[p->second].targets)if(to>=0&&key(nodes[to])==key(b))return true;
        return false;
    }
    const Node* neighbor(int slot,int index,bool main)const {
        const int id=main?at_main_vertex[index]:off_entries[index];
        if(id<0)return nullptr;
        const int to=links[id].targets[slot];
        return to<0?nullptr:&nodes[to];
    }
};

unique_ptr<LocalTracks> local_tracks;
