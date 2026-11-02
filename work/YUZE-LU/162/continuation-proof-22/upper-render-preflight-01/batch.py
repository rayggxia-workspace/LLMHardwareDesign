import pya
v=pya.LayoutView()
v.load_layout('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/pg-strong-delivery-01/control_status/6_final.gds',0)
v.max_hier()
v.add_missing_layers()
v.zoom_fit()
v.save_image('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/upper-render-preflight-01/batch.png',600,600)
