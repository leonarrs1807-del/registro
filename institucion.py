"""Institutional identity shared by portable documents and exports."""
import io
from db_safety import connection

FIELDS={'nombre':'Nombre de la IE','codigo':'Código modular','ugel':'UGEL / DRE',
        'direccion':'Dirección','director':'Director/a','docente':'Docente'}


def profile(path):
    import db
    cfg=db.obtener_docente_config(path)
    result={key:'' for key in FIELDS}
    result.update(nombre=cfg.get('institucion',''),docente=cfg.get('nombres_docente',''))
    with connection(path) as conn:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name='Colegio_Datos'").fetchone():
            result.update(dict(conn.execute('SELECT campo,valor FROM Colegio_Datos')))
    result.update(nombre=cfg.get('institucion',''),docente=cfg.get('nombres_docente',''))
    return result


def save(path,values):
    values={key:str(values.get(key,'')).strip() for key in FIELDS}
    if not values['nombre']:raise ValueError('Escriba el nombre de la institución educativa.')
    if any(len(v)>300 for v in values.values()):raise ValueError('Utilice hasta 300 caracteres por campo.')
    with connection(path) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS Colegio_Datos(campo TEXT PRIMARY KEY,valor TEXT NOT NULL)')
        conn.executemany('INSERT OR REPLACE INTO Colegio_Datos VALUES(?,?)',values.items())
        conn.execute('UPDATE Docente_Config SET institucion=?,nombres_docente=? WHERE id=1',(values['nombre'],values['docente']))


def decorate(wb,path):
    """Keep import coordinates intact; brand print headers and a readable cover."""
    import reportes,periodos
    from openpyxl.styles import Font,Alignment,PatternFill
    data=profile(path);period=periodos.info(path)['label'];logo=reportes.logo_bytes(path)
    with connection(path) as conn:
        configured=bool(conn.execute("SELECT 1 FROM sqlite_master WHERE name='Colegio_Datos'").fetchone())
    if not configured and not logo:return
    ws=wb['Institución'] if 'Institución' in wb.sheetnames else wb.create_sheet('Institución')
    ws.sheet_view.showGridLines=False;ws.column_dimensions['A'].width=4
    ws.column_dimensions['B'].width=26;ws.column_dimensions['C'].width=65
    ws.merge_cells('B2:E2');ws['B2']='INSTITUCIÓN EDUCATIVA';ws['B2'].font=Font(name='Calibri',size=17,bold=True,color='075985')
    ws.row_dimensions[2].height=38
    for n,(key,title) in enumerate(FIELDS.items(),5):
        ws.cell(n,2,title).font=Font(name='Calibri',size=12,bold=True,color='075985')
        cell=ws.cell(n,3,data.get(key,''));cell.data_type='s';cell.font=Font(name='Calibri',size=12)
        cell.alignment=Alignment(wrap_text=True,vertical='center');ws.row_dimensions[n].height=max(30,min(100,14*((len(data.get(key,''))+57)//58)+8))
    ws.cell(12,2,'Periodo');ws.cell(12,3,period)
    ws._images=[]
    if logo:
        from openpyxl.drawing.image import Image
        picture=Image(io.BytesIO(logo));factor=min(82/picture.width,82/picture.height);picture.width*=factor;picture.height*=factor;ws.add_image(picture,'E5')
    for sheet in wb:
        if sheet.sheet_state!='visible':continue
        # Excel header text treats ampersands as formatting commands.
        sheet.oddHeader.center.text=(data['nombre'] or 'Institución educativa').replace('&','&&')
        sheet.oddHeader.center.size=12;sheet.oddHeader.center.font='Calibri,Bold'
        sheet.oddFooter.left.text=period.replace('&','&&');sheet.oddFooter.right.text='Página &P de &N'
        sheet.page_margins.top=.75;sheet.page_margins.bottom=.6
    for sheet in wb:
        if sheet.title not in ('Registro','Instrumento','Matriz final'):continue
        original=str(sheet['A1'].value or '')
        branded=(data['nombre'] or 'Institución educativa')+'\n'+original
        sheet['A1']=branded;sheet['A1'].data_type='s';sheet['A1'].font=Font(name='Calibri',size=13,bold=True,color='075985')
        sheet['A1'].alignment=Alignment(horizontal='left',vertical='center',wrap_text=True,indent=6 if logo else 1)
        sheet.row_dimensions[1].height=58 if logo else 44
        if logo:
            from openpyxl.drawing.image import Image
            pic=Image(io.BytesIO(logo));factor=min(62/pic.width,62/pic.height);pic.width*=factor;pic.height*=factor;sheet.add_image(pic,'A1')
        if sheet.title=='Registro' and 'Registro_Meta' in wb:
            wb['Registro_Meta'].append(['source_title',original]);wb['Registro_Meta'].append(['branded_title',branded])
    wb.properties.creator=data['docente'] or 'Registro Docente' 


def export_pdf(destination,rows,config,logo=None):
    """The same renderer creates real PDF reports and their PNG preview."""
    from datetime import datetime,timezone,timedelta
    from pathlib import Path
    from textwrap import fill
    from matplotlib.figure import Figure
    from matplotlib.patches import FancyBboxPatch,Rectangle
    from matplotlib.backends.backend_pdf import PdfPages
    names={};pages=[];page=[];used=0
    for row in rows:
        key=(row.get('estudiante_id'),row.get('apellidos'),row.get('nombres'))
        names.setdefault(key,len(names)+1)
        from presentacion import format_grade
        note=format_grade(row.get('nota'),config.get('presentacion','numero'),limits=config.get('limites'))
        cells=[f'{names[key]:02}',fill(f"{row.get('apellidos','')}, {row.get('nombres','')}",25),
            fill(str(row.get('actividad','')),25),fill(str(row.get('capacidad','')),36),
            note,str(row.get('asistencia',''))]
        lines=max(c.count('\n')+1 for c in cells)
        if page and used+lines+1>24:pages.append(page);page=[];used=0
        page.append((cells,lines));used+=lines+1
    if page or not pages:pages.append(page)
    figures=[]
    for number,items in enumerate(pages,1):
        fig=Figure(figsize=(11.7,8.3),facecolor='white')
        fig.add_artist(Rectangle((0,.975),1,.025,transform=fig.transFigure,facecolor='#7dd3fc',edgecolor='none'))
        fig.add_artist(FancyBboxPatch((.035,.785),.93,.17,boxstyle='round,pad=0.009',transform=fig.transFigure,facecolor='#eff9ff',edgecolor='#bae6fd'))
        if logo:
            import matplotlib.image as mpimg
            ax=fig.add_axes([.05,.82,.075,.1]);ax.set_zorder(2);ax.imshow(mpimg.imread(io.BytesIO(logo)));ax.axis('off')
        left=.145 if logo else .055
        name=config.get('nombre') or config.get('institucion') or 'Institución educativa'
        fig.text(left,.935,fill(name,100),fontsize=14 if len(name)>80 else 17,weight='bold',color='#075985',va='top')
        details=' · '.join(v for v in [config.get('codigo','') and 'Cód. modular: '+config['codigo'],config.get('ugel','')] if v)
        fig.text(left,.855,details,fontsize=10,color='#475569')
        fig.text(left,.824,config.get('direccion',''),fontsize=10,color='#475569')
        fig.text(.045,.74,'REGISTRO DE EVALUACIÓN',fontsize=16,weight='bold',color='#0c4a6e')
        period=config.get('periodo','Periodo por asignar')
        course=rows[0].get('curso','') if rows else ''
        classroom=' '.join(str(rows[0].get(k,'')) for k in ('grado','seccion')) if rows else ''
        fig.text(.045,.704,' · '.join(v for v in [period,course,classroom] if v),fontsize=11,color='#334155')
        fig.text(.045,.674,'Docente: '+(config.get('docente') or config.get('nombres_docente') or '________________________'),fontsize=10,color='#475569')
        ax=fig.add_axes([.045,.15,.91,.49]);ax.axis('off')
        if items:
            table=ax.table(cellText=[r for r,_ in items],colLabels=['N°','Apellidos y nombres','Actividad / tema','Capacidad evaluada','Nota','Asistencia'],
                colWidths=[.045,.235,.225,.31,.075,.11],loc='upper center',cellLoc='left')
            table.auto_set_font_size(False);table.set_fontsize(9)
            for (i,j),cell in table.get_celld().items():
                cell.set_edgecolor('#dbe5ee');cell.set_linewidth(.6)
                cell.set_height(.09 if i==0 else .034*(items[i-1][1]+1))
                if i==0:cell.set_facecolor('#dff3ff');cell.set_text_props(weight='bold',color='#075985')
                else:
                    cell.set_facecolor('#ffffff' if i%2 else '#f5faff')
                    if j==4:cell.set_text_props(weight='bold',ha='center',color='#075985')
        else:ax.text(.5,.8,'Sin calificativos para el filtro elegido.',ha='center',color='#64748b')
        fig.text(.045,.092,'________________________________',fontsize=10,color='#94a3b8')
        fig.text(.045,.068,config.get('docente') or config.get('nombres_docente') or 'Firma del docente',fontsize=9,color='#475569')
        fig.text(.68,.092,'________________________________',fontsize=10,color='#94a3b8')
        fig.text(.68,.068,config.get('director') or 'Dirección / coordinación',fontsize=9,color='#475569')
        stamp=datetime.now(timezone(timedelta(hours=-5))).strftime('%d/%m/%Y')
        fig.text(.045,.028,'Registro Docente · '+stamp,fontsize=8,color='#64748b')
        fig.text(.95,.028,f'{number} / {len(pages)}',ha='right',fontsize=8,color='#64748b');figures.append(fig)
    if Path(destination).suffix.lower()=='.png':figures[0].savefig(destination,dpi=140)
    else:
        with PdfPages(destination) as pdf:
            for fig in figures:pdf.savefig(fig)
