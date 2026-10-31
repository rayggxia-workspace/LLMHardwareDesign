import pya
view=pya.LayoutView()
view.load_layout('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-805/tasks/revision300-drc-v/gds-flow/results/nangate45/bv1_block_v1_v/base/6_final.gds',0)
view.max_hier()
view.add_missing_layers()
view.zoom_fit()
view.save_image('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261031-805/tasks/revision300-delivery-v/block_v1_v.png',1600,1600)
