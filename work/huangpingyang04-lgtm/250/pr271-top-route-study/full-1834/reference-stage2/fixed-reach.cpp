// Diagnostic only. No route is committed to the fixed-port graph.
#define main reference_maze_main
#include "reference-maze.cpp"
#undef main

vector<int> components(DetailedGraph& g,int size,int& largest) {
    vector<int> labels(size,-1);
    vector<int> queue;
    int next=0;
    for(int root=0;root<size;++root) {
        if(labels[root]>=0) continue;
        queue.clear();
        queue.push_back(root);
        labels[root]=next;
        for(size_t q=0;q<queue.size();++q) {
            for(auto direction:{main_minus,main_plus,vertical_move}) {
                const int u=queue[q];
                if(!g.hasEdge(u,direction)) continue;
                const int v=g.getEdgeEndPoint(u,direction);
                if(labels[v]>=0) continue;
                labels[v]=next;
                queue.push_back(v);
            }
        }
        largest=max(largest,int(queue.size()));
        ++next;
    }
    return labels;
}

unordered_set<int> reachable_labels(const DetailedGraph& g,const vector<int>& labels,int pin) {
    const auto [start]=g.getVertices(pin);
    vector<int> queue{start};
    unordered_set<int> seen{start};
    unordered_set<int> result;
    for(size_t i=0;i<queue.size();++i) {
        const int u=queue[i];
        if(u<int(labels.size())) result.insert(labels[u]);
        for(auto d:{fine_minus,fine_plus,vertical_move}) {
            if(!g.hasEdge(u,d)) continue;
            const int v=g.getEdgeEndPoint(u,d);
            if(seen.insert(v).second) queue.push_back(v);
        }
    }
    return result;
}

int main(int argc,char** argv) {
    if(argc!=3)return 2;
    ifstream input(argv[1]);
    ofstream out(argv[2]);
    int count=0;
    input>>llx>>lly>>urx>>ury>>count;
    if(!input||!out||count<=0||urx-llx<pitch||ury-lly<pitch)return 2;
    vector<Net> nets(count);
    Occupancy occupied;
    TrackGraph tracks;
    for(int i=0;i<count;++i) {
        auto& n=nets[i];
        int pins,windows;
        input>>n.id>>pins>>windows;
        if(!input||n.id!=i||pins<2)return 2;
        n.pins.resize(pins);
        n.windows.resize(windows);
        for(auto& pin:n.pins) {
            input>>pin.x>>pin.y;
            pin.layer=0;
            if(!input||!occupied.fits(pin))return 2;
            occupied.add(i,pin,pin,0);
            tracks.occupy(pin,pin,0);
        }
        for(auto& w:n.windows)input>>w.left>>w.bottom>>w.right>>w.top;
    }
    if(!input)return 2;
    DetailedGraph graph(tracks);
    int largest=0;
    const auto labels=components(graph,2*tracks.points,largest);
    int connected=0;
    for(const auto& net:nets) {
        tracks.use_pads(net);
        graph.load(net,occupied);
        auto labels_shared=reachable_labels(graph,labels,0);
        for(size_t pin=1;pin<net.pins.size()&&!labels_shared.empty();++pin) {
            const auto reached=reachable_labels(graph,labels,int(pin));
            for(auto it=labels_shared.begin();it!=labels_shared.end();) {
                if(!reached.count(*it)) it=labels_shared.erase(it);
                else ++it;
            }
        }
        connected+=!labels_shared.empty();
        out<<net.id<<'\t'<<int(!labels_shared.empty())<<'\n';
    }
    cerr<<"fixed-ports connected "<<connected<<" / "<<count
        <<" largest_component "<<largest<<" track_vertices "<<labels.size()<<'\n';
    return 0;
}
