"""Admission gate for measured active-prefix reads of the unchanged feeder."""


def validate(contract,row_timing):
    if contract is None:return False
    m=contract.get('operand_mask',{});proof=contract.get('proof',{})
    if (contract.get('kind')!='native-resident-services-active-prefix-v1' or
        m.get('kind')!='native-M-active-prefix-v1' or m.get('padding_writes') is not False or
        m.get('initializations')!=['zero','ones','mixed','unknown'] or m.get('rows')!=[1,8] or
        m.get('k')!=[1,2] or m.get('columns')!=1 or
        contract.get('rtl_sha256')!=row_timing['rtl_sha256'] or contract.get('profile')!=row_timing['profile']):
        raise ValueError('qualified unchanged-RTL active-prefix contract required')
    shas=[proof.get('manifest_sha256',''),*proof.get('logs_sha256',[])]
    if (len(shas)!=5 or len(set(shas[1:]))!=4 or
        any(not isinstance(s,str) or len(s)!=64 or any(c not in '0123456789abcdef' for c in s) for s in shas) or
        len(proof.get('cases_per_initialization',[]))!=4 or
        any(type(n)!=int or n<1 for n in proof['cases_per_initialization'])):
        raise ValueError('four recorded SRAM initialization proofs required')
    return True
