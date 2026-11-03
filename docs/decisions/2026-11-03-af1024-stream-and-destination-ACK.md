# AF1024：使用A_T保活与公开入口ACK观察

Issue151/PR152，Melodydt，源b3e14e27e1c38afc697d383e33f5d8d90be62267/95849。实例原AFULL+baseline F，计M2/N2/E2/G1/S2/T2；父2KiB gamma FFbank，无4KiB Y array。每Y先Fcapture进真实输入holding，pending1阻重复，再等公开in_ready在真实非末帧SACK后重开才A_Ttake。失帧/metadata错误门不能将清帧ready误当ACK；TB独立观测真实SACK，首/末Y背压已测。

父独立任务终态、两个版本/不同provider、两次F编号预算mirror、当前子sat拥有权和实际T释放均显式控制。固定接口证明不泛化为L5 peer storedACK或任意late隔离。选同Fin10 baseline，Fin12/W9不可裸接。用户要求每步覆盖现有本地交流PDF属于本研究交付门，路径/QA见报告与交接；不改其他成员交付制度。
