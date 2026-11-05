from pathlib import Path
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control\project\experiments\control_v1')
p=r/'resource_search.h';s=p.read_text();s=s.replace(' uint64_t calls=0,maximum_labels=0;',' uint64_t calls=0,maximum_labels=0;size_t label_limit=4000000;');s=s.replace('labels.size()>=4000000','labels.size()>=label_limit');s=s.replace('ResourceSearch search;auto path=','ResourceSearch search;search.label_limit=trial%2?8000000:4000000;auto path=');p.write_bytes(s.encode())
p=r/'tree_router.cpp';s=p.read_text();needle=' if(argc!=3)throw runtime_error("input/output arguments required");';assert needle in s;s=s.replace(needle,''' if(argc!=3&&argc!=4)throw runtime_error("input/output arguments required");
 size_t resource_label_limit=4000000;
 if(argc==4){string option=argv[3];if(option=="--resource-labels=8000000")resource_label_limit=8000000;
  else if(option!="--resource-labels=4000000")throw runtime_error("invalid finite-resource label memory envelope");}''');s=s.replace('uint64_t bidirectional_branches=0;ResourceSearch resource_search;','uint64_t bidirectional_branches=0;ResourceSearch resource_search;resource_search.label_limit=resource_label_limit;');p.write_bytes(s.encode())
p=r/'tree_router_cpp.py';s=p.read_text();s=s.replace('trial_attempts=0):','trial_attempts=0,resource_label_limit=4000000):');needle='    assert trial_attempts==0';s=s.replace(needle,"    assert resource_label_limit in (4000000,8000000)and(resource_label_limit==4000000 or pareto_wire_budget)\n    extra_cli=['--resource-labels='+str(resource_label_limit)]if resource_label_limit!=4000000 else[]\n"+needle,1);s=s.replace('[str(binary),str(inp),str(result)],stdout=log','[str(binary),str(inp),str(result)]+extra_cli,stdout=log');s=s.replace("[str(binary),str(folder/'input.txt'),str(folder/'output.txt')],folder/'router.log'","[str(binary),str(folder/'input.txt'),str(folder/'output.txt')]+extra_cli,folder/'router.log'");s=s.replace("command=[str(binary),str(folder/'input.txt'),str(folder/'output.txt')]","command=[str(binary),str(folder/'input.txt'),str(folder/'output.txt')]+extra_cli");s=s.replace('nonpreferred_search_cost=nonpreferred_cost,pareto_wire_budget=bool(pareto_wire_budget),','nonpreferred_search_cost=nonpreferred_cost,pareto_wire_budget=bool(pareto_wire_budget),\n        finite_resource_label_memory_envelope=resource_label_limit,');p.write_bytes(s.encode())
p=r/'system_upper.py';s=p.read_text();needle="    p.add_argument('--route-trial-attempts'";assert needle in s;s=s.replace(needle,"    p.add_argument('--route-resource-labels',type=int,choices=[4000000,8000000],default=4000000,help='Search memory only: optional8million labels; final physical/electrical/timing gates unchanged')\n"+needle,1);needle='    assert a.route_trial_attempts==0';s=s.replace(needle,"    assert a.route_resource_labels==4000000 or(a.router=='cpp'and a.route_residual_budget)\n"+needle,1);s=s.replace('trial_attempts=a.route_trial_attempts)','trial_attempts=a.route_trial_attempts,resource_label_limit=a.route_resource_labels)');p.write_bytes(s.encode())
p=r/'directional_router_regression.py';s=p.read_text();needle='    return dict(passed=True, cases=rows';assert needle in s;s=s.replace(needle,'''    memory_cases=[]
    for limit in (4000000,8000000):
        folder=out/('resource-memory-'+str(limit));folder.mkdir()
        _,proof=route({'a':[(8,8),(32,32)]},48,48,162,10,folder,
            trials=2,trial_attempts=4,locked_names=['a'],wire_limits={'a':80},
            negotiated_priority=True,defer_access_vias=True,pareto_wire_budget=True,resource_label_limit=limit)
        assert proof['final_conflicts']==0 and proof['finite_resource_label_memory_envelope']==limit
        commands=proof['trial_search']['records'].values()
        assert all(('--resource-labels=8000000'in row['command'])==(limit==8000000)for row in commands)
        memory_cases.append(proof)
    for option in ('--resource-labels=0','--resource-labels=7999999','--other-option'):
        result=subprocess.run([str(executable),str(out/'mode0-cost8/router-input.txt'),str(out/'invalid-memory-output'),option],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert result.returncode!=0 and not(out/'invalid-memory-output').exists()
        negatives.append(dict(kind='memory-envelope-cli',option=option,rejected=True))
'''+needle,1);s=s.replace('dynamic_pool_cases=pool_cases,','dynamic_pool_cases=pool_cases,resource_memory_cases=memory_cases,');p.write_bytes(s.encode())
