"""Refresh expensive views only when they are opened; keep form text lightweight."""
from functools import wraps


class TextBuffer:
    def __init__(self,text=''):self.text=text
    def get(self,*args):return self.text
    def delete(self,*args):self.text=''
    def insert(self,index,text):self.text=str(text)+self.text if str(index) in ('0','0.0','1.0') else self.text+str(text)
    def configure(self,**kwargs):pass
    def winfo_ismapped(self):return False
    def grid_forget(self):pass


def visible_when(page):
    def decorate(function):
        @wraps(function)
        def refresh(self,*args,**kwargs):
            if not hasattr(self,'_view_pending'):self._view_pending={}
            if self.tabview.get()!=page:
                self._view_pending[function.__name__]=(page,args,kwargs)
                return
            self._view_pending.pop(function.__name__,None)
            return function(self,*args,**kwargs)
        return refresh
    return decorate


class PerformanceTools:
    def iniciar_cubierta_arranque(self):
        import customtkinter as ctk
        self._startup_cover=ctk.CTkFrame(self,fg_color=('#f0f9ff','#102c40'),corner_radius=0)
        self._startup_cover._preserve_theme=True
        self._startup_cover.place(relx=0,rely=0,relwidth=1,relheight=1)
        center=ctk.CTkFrame(self._startup_cover,fg_color='transparent');center.place(relx=.5,rely=.5,anchor='center')
        ctk.CTkLabel(center,text='Registro Docente',font=ctk.CTkFont(size=30,weight='bold'),text_color=('#075985','#bae6fd')).pack(pady=10)
        self._startup_text=ctk.CTkLabel(center,text='Preparando tu espacio de trabajo…',font=ctk.CTkFont(size=15));self._startup_text.pack(pady=8)
        self._startup_progress=ctk.CTkProgressBar(center,width=340,progress_color='#38bdf8');self._startup_progress.pack(pady=14);self._startup_progress.set(.03)
        ctk.CTkLabel(center,text='Las secciones quedarán listas para usarlas.',font=ctk.CTkFont(size=13)).pack()
        self.update_idletasks()

    def avance_arranque(self,text,value):
        self._startup_cover.lift();self._startup_text.configure(text=text+'…');self._startup_progress.set(value)
        self.update_idletasks()

    def al_mostrar_pagina(self,page):
        if getattr(self,'_closing_ui',False):return
        job=getattr(self,'_page_refresh_job',None)
        if job:self.after_cancel(job)
        self._page_refresh_job=self.after(25,self._actualizar_pagina_visible)

    def _actualizar_pagina_visible(self):
        self._page_refresh_job=None
        if getattr(self,'_closing_ui',False):return
        page=self.tabview.get()
        if page=='Ingresar Calificativos' and hasattr(self,'actualizar_herramientas_evaluacion'):
            self.actualizar_herramientas_evaluacion()
        pending=list(getattr(self,'_view_pending',{}).items())
        for name,(target,args,kwargs) in pending:
            if target==page:getattr(self,name)(*args,**kwargs)


def preparar_graficos():
    """Preload plotting while Tk builds all pages; the worker never touches Tk."""
    import threading,logging,time
    def load():
        start=time.perf_counter()
        try:
            import matplotlib.figure
            import matplotlib.backends.backend_tkagg
            from matplotlib import font_manager
            font_manager.findfont('DejaVu Sans')
            logging.getLogger('registro').info('Herramientas de gráficos preparadas en %.2f s',time.perf_counter()-start)
        except Exception:
            logging.getLogger('registro').exception('No se pudo anticipar la carga de gráficos')
    worker=threading.Thread(target=load,name='preparar-graficos',daemon=True);worker.start();return worker
