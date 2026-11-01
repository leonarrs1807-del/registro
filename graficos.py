"""Responsive, separate charts with complete labels and explicit units."""
from textwrap import fill
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator


def category_figure(weights,width=800):
    width=max(420,width)
    fig=Figure(figsize=(width/100,3.4),layout='constrained');ax=fig.add_subplot()
    labels=list(weights);values=list(weights.values())
    if abs(sum(values)-100)>1e-6 or any(v<0 for v in values):
        ax.text(.5,.5,'Revise los porcentajes: deben sumar 100%.',ha='center');ax.axis('off');return fig
    chars=max(16,int(min(220,width*.4)/6.5))
    bars=ax.barh([fill(t,chars) for t in labels],values,color=['#2563eb','#059669','#d97706','#7c3aed'])
    ax.bar_label(bars,labels=[f'{v:g} %' for v in values],padding=5)
    ax.set_xlim(0,110);ax.set_xlabel('Porcentaje del promedio (%)');ax.set_title('Ponderación por categoría')
    ax.invert_yaxis();return fig


def frequency_figure(items,title,width=900):
    width=max(420,width);chars=max(16,int(min(290,width*.43)/6.5))
    labels=[fill(name,chars) for name,count in items]
    height=max(330,sum(max(62,16*(text.count('\n')+1)+20) for text in labels)+100)
    fig=Figure(figsize=(width/100,height/100),layout='constrained');ax=fig.add_subplot()
    if not items:
        ax.text(.5,.5,'No hay información para este curso y salón.',ha='center');ax.axis('off');return fig
    values=[count for name,count in items]
    bars=ax.barh(range(len(items)),values,color=['#2563eb' if v else '#9ca3af' for v in values])
    ax.set_yticks(range(len(items)),labels,fontsize=10);ax.invert_yaxis()
    ax.bar_label(bars,labels=[str(v) if v else 'Sin evaluar' for v in values],padding=5)
    ax.set_xlim(0,max(values+[1])*1.25+1);ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlabel('Número de actividades');ax.set_title(title);return fig
