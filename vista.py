"""Readable, persistent layouts and explicit file destinations."""
from pathlib import Path
from datetime import datetime
import json,re
import tkinter as tk
from tkinter import filedialog,messagebox
import tkinter.font as tkfont
import customtkinter as ctk
import app_storage as storage


class ViewTools:
    def ajustar_pantalla(self,reset=False):
        scale=self._get_window_scaling()
        width=max(320,int(self.winfo_screenwidth()/scale*.95))
        height=max(240,int(self.winfo_screenheight()/scale*.88))
        self.minsize(min(800,width),min(520,height))
        if reset or not getattr(self,'_geometry_restored',False):self.geometry(f'{min(1420,width)}x{min(850,height)}+0+0')

    def restaurar_vista(self):
        self.tamano_letra_actual='Personalizado (16)'
        import db
        db.guardar_tamano_letra_preferido(self.tamano_letra_actual)
        self.cambiar_zoom(1)
        self.tabview.set_expanded(False)
        self.ajustar_pantalla(reset=True)
        for name,pane in getattr(self,'_split_panes',{}).items():
            if pane.winfo_exists():
                size=pane.winfo_width() if str(pane.cget('orient'))=='horizontal' else pane.winfo_height()
                self.after(100,lambda p=pane,n=name,s=size:self._colocar_divisor(p,s*(.23 if n=='navegacion' else .4)))
        self._guardar_ventana()

    def _colocar_divisor(self,pane,position):
        if not pane.winfo_exists() or len(pane.panes())<2:return
        vertical=str(pane.cget('orient'))=='vertical'
        size=pane.winfo_height() if vertical else pane.winfo_width()
        position=max(100,min(int(position),max(100,size-180)))
        pane.sash_place(0,0 if vertical else position,position if vertical else 0)

    def restaurar_divisor(self,name):
        pane=getattr(self,'_split_panes',{}).get(name)
        if pane is None:return
        saved=self._preferencias().get('panes',{}).get(name)
        if isinstance(saved,(int,float)) and 0<saved<1:
            def apply():
                if pane.winfo_exists():
                    size=pane.winfo_height() if str(pane.cget('orient'))=='vertical' else pane.winfo_width()
                    self._colocar_divisor(pane,size*saved)
            self.after(150,apply)
        pane.bind('<ButtonRelease-1>',lambda e:self._guardar_ventana(),add='+')

    def fuentes_menu(self,menu):
        from interfaz import pixel_scale
        font=tkfont.nametofont('TkMenuFont',root=self)
        font.configure(family='Segoe UI',size=-round(14*pixel_scale(self)))
        menu.configure(font=font)
        end=menu.index('end')
        if end is not None:
            for index in range(end+1):
                if menu.type(index)=='cascade':
                    child=self.nametowidget(menu.entrycget(index,'menu'))
                    self.fuentes_menu(child)

    def elegir_destino(self,**kwargs):
        prefs=self._preferencias()
        default=Path(prefs.get('save_dir',''))
        if not prefs.get('save_dir') or not default.is_dir():
            default=Path.home()/'Documents'
            if not default.is_dir():default=Path.home()
        kwargs.setdefault('initialdir',str(default))
        kwargs.setdefault('title','Elija la carpeta y el nombre del archivo')
        path=filedialog.asksaveasfilename(**kwargs)
        if path:
            self._save_dir=str(Path(path).resolve().parent)
            self._guardar_ventana()
        return path

    def archivo_guardado(self,path,detail='Archivo guardado correctamente.'):
        path=Path(path).resolve()
        if hasattr(self,'lbl_estado'):self.lbl_estado.configure(text='Archivo guardado')
        messagebox.showinfo('Archivo guardado',detail+'\n\nUbicación:\n'+str(path))

    def abrir_instrucciones(self,topic='Empezar y guardar'):
        self.tabview.set('Instrucciones');self.tutorial.open(topic)

    def barra_acciones(self):
        self.fuentes_nativas()
        self.after(100,self._ajustar_cabecera)

    def fuentes_nativas(self):
        from interfaz import pixel_scale
        for name in ('TkDefaultFont','TkTextFont','TkMenuFont','TkHeadingFont','TkCaptionFont'):
            tkfont.nametofont(name,root=self).configure(family='Segoe UI',size=-round(14*pixel_scale(self)))
        if hasattr(self,'tutorial'):
            self.tutorial.listing.configure(font=('Segoe UI',-round(14*pixel_scale(self))))
            self.tutorial.text.configure(font=('Segoe UI',-round(16*pixel_scale(self))))

    def actualizar_lista_practicas(self):
        panel=getattr(self,'puntos_panel',None)
        if panel and panel.winfo_exists():panel.listing.configure(font=('Segoe UI',getattr(self,'_native_table_font_size',-16)))
