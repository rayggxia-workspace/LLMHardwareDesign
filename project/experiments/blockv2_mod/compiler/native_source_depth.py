"""Depth legality depends on opened source operators, not individual tile identities."""
from functools import lru_cache
class SourceDepth:
 def __init__(self,parent_order,parent_deps,parent_parts,task_parents,depth):
  self.ids={p:i for i,p in enumerate(parent_order)}
  self.deps=[tuple(self.ids[q] for q in parent_deps[p]) for p in parent_order]
  self.parts=[parent_parts[p] for p in parent_order]
  self.task_parents=[self.ids[p] for p in task_parents];self.depth=depth
 def advance(self,opened,done,task):
  parent=self.task_parents[task];parts=self.parts[parent]
  progress=(done | (1<<task)) & parts
  return (opened & ~(1<<parent)) if progress==parts else (opened | (1<<parent))
 @lru_cache(maxsize=256)
 def legal(self,opened):
  longest=[]
  for i,deps in enumerate(self.deps):
   distance=((opened>>i)&1)+max((longest[q] for q in deps),default=0)
   if distance>self.depth:return False
   longest.append(distance)
  return True
