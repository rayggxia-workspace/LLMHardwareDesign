"""Compare interval feasibility with exhaustive integer displacement oracles."""
import json,random
from pair_wire_feasibility import family


def main():
    rng=random.Random(162);checks=0
    # Each of two links is individually feasible, but their shared placement
    # cannot satisfy both. A pairwise-per-bit test would miss this failure.
    links=[dict(net='a',a=[10,0],b=[0,0],max_capacitance_ff=1),
           dict(net='b',a=[10,10],b=[0,0],max_capacitance_ff=1)]
    assert all(family([10,10],[10,10],[row],0,0,'E',1)['wire_only_necessary_constraints_feasible']for row in links)
    assert not family([10,10],[10,10],links,0,0,'E',1)['wire_only_necessary_constraints_feasible']
    # Derive rotations and actual Manhattan distances independently of the
    # production transform and interval functions. Integral inputs guarantee
    # any nonempty feasible interval has an integer witness in [-80,80].
    def rotate(p,size,r):
        x,y=p
        for _ in range(r):x,y=size-y,x
        return x,y
    for _ in range(5000):
        a,b=rng.choice([4,8,12]),rng.choice([4,8,12]);ra,rb=rng.randrange(4),rng.randrange(4);direction=rng.choice(['E','W','N','S'])
        rows=[dict(net=str(i),a=[rng.randrange(a+1),rng.randrange(a+1)],
                   b=[rng.randrange(b+1),rng.randrange(b+1)],max_capacitance_ff=rng.randrange(1,31))for i in range(rng.randrange(1,7))]
        oracle=False
        for t in range(-80,81):
            dx,dy={'E':(a,t),'W':(-b,t),'N':(t,a),'S':(t,-b)}[direction]
            distances=[]
            for row in rows:
                ax,ay=rotate(row['a'],a,ra);bx,by=rotate(row['b'],b,rb)
                distances.append(abs(dx+bx-ax)+abs(dy+by-ay)<=row['max_capacitance_ff'])
            if all(distances):oracle=True;break
        actual=family([a,a],[b,b],rows,ra,rb,direction,1)['wire_only_necessary_constraints_feasible']
        assert actual==oracle,(a,b,ra,rb,direction,rows,actual,oracle);checks+=1
    print(json.dumps(dict(passed=True,random_exhaustive_oracle_cases=checks,joint_contradiction_control=True,
                         scope='Mathematical diagnostic only; no EDA or hardware qualification.')))


if __name__=='__main__':main()
