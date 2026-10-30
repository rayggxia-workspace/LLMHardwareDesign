"""Actual extracted leaf margins with identical sizing costs; no system benefit claim."""
from pathlib import Path
import expand_candidates as expand


def plot(result,out):
    controls={r['case']:r for r in result['optimized_boundary_same_ECO_controls']}
    current={r['case']:r for r in result['blocks']}
    if set(controls)!={'gemm','mxu'}:return
    plt=expand.legacy.plt
    fig,axes=plt.subplots(1,2,figsize=(13.6,7.3))
    fig.subplots_adjust(left=.075,right=.975,bottom=.27,top=.76,wspace=.23)
    fig.text(.055,.94,'GEMM / MXU | 相同驱动换型成本下的叶块实测',fontsize=19,weight='bold',color='#17283c')
    fig.text(.055,.875,'原SDC、外框、资源与原pin金属层保持；Aopt为优化周边，C为内部二维。两侧fresh native DRC均为0。',fontsize=10,color='#56677d')
    for ax,kind,title in zip(axes,['setup','hold'],['Setup 余量','Hold 余量']):
        for shift,source,color,label in [(-.19,controls,'#657eac','Aopt 优化周边'),(.19,current,'#19a7a0','C 内部二维')]:
            values=[source[c][kind+'_ns'] for c in ['gemm','mxu']]
            bars=ax.bar([i+shift for i in range(2)],values,width=.34,color=color,label=label)
            for bar,v in zip(bars,values):ax.annotate(format(v,'.6f'),(bar.get_x()+bar.get_width()/2,v),xytext=(0,6),textcoords='offset points',ha='center',fontsize=9)
        ax.set_xticks([0,1],['GEMM','MXU']);ax.set_ylabel('实际提取 / 原约束余量 (ns)')
        ax.set_title(title,loc='left',weight='bold',fontsize=13);ax.set_ylim(bottom=0,top=ax.get_ylim()[1]*1.16)
        ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True);ax.spines[['top','right']].set_visible(False)
        ax.legend(loc='upper right',fontsize=8,frameon=False)
    fig.text(.055,.14,'相同换型：GEMM 3处 / +1.596 μm²；MXU 1处 / +0.266 μm²（标准单元master面积，非block面积）。\n仅为叶块现有约束与研究RC结果，缺最小时钟周期等完整覆盖；GEMM GDS仍有1460项天线，MXU缺SRAM GDS。\n尚无共同底座或系统对照；不能据此声称系统时序、RC、面积或适配层收益。',fontsize=10,color='#56677d',linespacing=1.7)
    assets=Path(out)/'assets';fig.savefig(assets/'equal_cost_leaf_margins.png',dpi=180)
    target=assets/'equal_cost_leaf_margins.svg'
    with plt.rc_context({'svg.hashsalt':'issue126-equal-cost'}):fig.savefig(target,metadata={'Date':None})
    target.write_text('\n'.join(s.rstrip() for s in target.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n')
    plt.close(fig)
