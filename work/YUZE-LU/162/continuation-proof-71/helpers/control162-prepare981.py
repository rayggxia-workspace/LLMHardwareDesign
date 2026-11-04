from pathlib import Path
h=Path(__file__).parent
s=(h/'control162-queue949-remote.py').read_text(encoding='utf-8').replace('source-947','source-972').replace('sready948-pin-release-fullchains','sready981-native-warm-fullchains').replace('r256-pin-release-regression-948','r256-native-warm-regression-973').replace('r256-pin-release-source-audit-950','r256-native-warm-source-audit-980').replace('sready948','sready981')
s=s.replace("[(9490,0,'dynamic-03/node5'),(9491,8,'dynamic-08/node6')]","[(9810,0,'dynamic-03/node5'),(9811,10,'dynamic-08/node6')]")
s=s.replace("for seed,weight,folder in", "for seed,weight,folder in")
old="'--route-native-prefix-first','--route-pin-access','ordinary-first','--route-native-batch-ripup','--route-native-refresh',str(weight),'--route-release-pin-reservations'"
new="'--route-native-prefix-first','--route-pin-access','none','--route-native-prefix-flexible','--route-native-prefix-input',str(seed_manifest)"
assert old in s;s=s.replace(old,new)
needle=" config=root/('acceptance-'+str(seed)+'.json');"
assert needle in s;s=s.replace(needle," native=root/'upper-candidates/9060/route'/('trial-'+str(weight));prefix=Path(str(native/'output.txt')+'.native-prefix-paths.txt');original=native/'input.txt';assert prefix.exists()and original.exists();seed_manifest=root/('warm-seed-'+str(seed)+'.json');assert not seed_manifest.exists();seed_manifest.write_text(json.dumps(dict(prefix=str(prefix),prefix_sha256=sha(prefix),input=str(original),input_sha256=sha(original))))\n"+needle)
s=s.replace("spec['requires']+=[str(reg/'receipt.json'),str(b/'r256-native-warm-source-audit-980/receipt.json')]", "spec['requires']+=[str(reg/'receipt.json'),str(b/'r256-native-warm-source-audit-980/receipt.json')]")
a=s.index("scope='");z=s.index("'),indent=2)",a)
s=s[:a]+"scope='Current453/S5380/R256 complete seven-stage chains9810/9811. Import independently verified actual9060 trial0/trial10 native-zero upper paths as flexible search seeds, not fixed wires. Original finite resource/wire budgets and actualM11landings always retained; M1-M10 macro interiors unchanged. Source972 frozen1010 manifest and actual973 old71-byte replays plus2warm full-route positives/strict seed rejects,980 exact3productionbackouts/21invariants required. All strict6keys geometry/PG/current453functions/events/3RC300MHz/final gates unchanged, no acceptance inferred.16active64dynamic attempts per slot, c64 4x16/c96 6x16,8ownparents; only guarded own9490/reg973 and own9491 slots replaced, every original raw/source/spec/partial preserved.'"+s[z+1:]
s=s.replace('candidates=[9490,9491]','candidates=[9810,9811]')
compile(s,'queue981','exec');(h/'control162-queue981-remote.py').write_text(s,encoding='utf-8')
s=(h/'control162-config956-remote.py').read_text(encoding='utf-8').replace('r256-final-chain-binding-audit-956','r256-final-chain-binding-audit-982').replace("[('sready948-pin-release-fullchains',[9490,9491])]","[('sready981-native-warm-fullchains',[9810,9811])]").replace('source-947','source-972').replace('r256-pin-release-regression-948','r256-native-warm-regression-973').replace('r256-pin-release-source-audit-950','r256-native-warm-source-audit-980')
s=s.replace("assert '--route-native-batch-ripup'in route['args']and '--route-release-pin-reservations'in route['args']and '--route-native-zero-maze'not in route['args']and route['forecast_gib']==64", "assert '--route-native-prefix-flexible'in route['args']and '--route-native-prefix-input'in route['args']and '--route-native-zero-maze'not in route['args']and '--route-release-pin-reservations'not in route['args']and route['forecast_gib']==64;assert route['args'][route['args'].index('--route-pin-access')+1]=='none'")
s=s.replace('candidates9490/9491','candidates9810/9811').replace('native-first/pin-reservation','flexible native warm-seed')
compile(s,'audit982','exec');(h/'control162-audit982-remote.py').write_text(s,encoding='utf-8')
print('prepared981 14 strict-chain specs and982 audit')
