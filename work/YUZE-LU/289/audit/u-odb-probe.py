import odb
print('WIRE_API', [x for x in dir(odb) if 'Wire' in x or 'Shape' in x])
