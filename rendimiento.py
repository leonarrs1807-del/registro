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
