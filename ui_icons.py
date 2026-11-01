"""Small, consistent line icons drawn locally, with light and dark variants."""
from functools import lru_cache
from PIL import Image, ImageDraw, ImageTk
import customtkinter as ctk


@lru_cache(maxsize=64)
def _draw(name, color):
    image=Image.new('RGBA',(64,64));d=ImageDraw.Draw(image)
    def line(points):d.line(points,fill=color,width=4,joint='curve')
    def box(bounds):d.rounded_rectangle(bounds,radius=4,outline=color,width=4)
    if name=='menu':
        for y in (18,32,46):line([(12,y),(52,y)])
    elif name=='courses':
        line([(32,16),(32,52)]);line([(32,20),(12,14),(10,46),(32,52),(54,46),(52,14),(32,20)])
    elif name=='students':
        d.ellipse((22,9,40,27),outline=color,width=4);d.arc((12,31,52,65),180,360,fill=color,width=4)
        d.arc((39,15,57,33),270,100,fill=color,width=3);d.arc((40,34,64,60),190,340,fill=color,width=3)
    elif name in ('activity','grades','matrix'):
        box((13,9,51,55))
        if name=='activity':line([(22,31),(42,31)]);line([(32,21),(32,41)])
        else:
            for y in (24,38):line([(15,y),(49,y)])
            for x in (26,39):line([(x,11),(x,53)])
    elif name=='search':
        d.ellipse((10,9,43,42),outline=color,width=4);line([(39,39),(55,55)])
    elif name in ('weights','stats'):
        line([(10,10),(10,53),(55,53)])
        if name=='weights':
            for x,y in ((20,35),(33,24),(46,13)):box((x,y,x+7,51))
        else:line([(16,43),(28,28),(39,36),(54,16)])
    elif name=='points':
        line([(32,8),(39,24),(56,26),(43,38),(47,55),(32,46),(17,55),(21,38),(8,26),(25,24),(32,8)])
    elif name=='help':
        d.ellipse((9,9,55,55),outline=color,width=4);d.arc((23,18,41,36),175,450,fill=color,width=4)
        line([(32,34),(32,39)]);d.ellipse((30,45,34,49),fill=color)
    elif name=='save':
        box((11,10,53,54));box((21,11,43,27));box((21,37,43,53))
    elif name=='more':
        for x in (15,32,49):d.ellipse((x-3,29,x+3,35),fill=color)
    elif name in ('lock','unlock'):
        box((14,28,50,54));d.arc((22,8,44,43),180,360,fill=color,width=4)
        if name=='unlock':d.rectangle((38,19,48,28),fill=(0,0,0,0))
        line([(32,37),(32,45)])
    return image


class WorkspaceIcon(ctk.CTkImage):
    def __init__(self,master,**kwargs):
        self.master=master
        super().__init__(**kwargs)
    def _get_scaled_light_photo_image(self,size):
        if size not in self._scaled_light_photo_images:
            self._scaled_light_photo_images[size]=ImageTk.PhotoImage(self._light_image.resize(size),master=self.master)
        return self._scaled_light_photo_images[size]
    def _get_scaled_dark_photo_image(self,size):
        if size not in self._scaled_dark_photo_images:
            self._scaled_dark_photo_images[size]=ImageTk.PhotoImage(self._dark_image.resize(size),master=self.master)
        return self._scaled_dark_photo_images[size]


def icon(name, size=20, active=False, *, master):
    return WorkspaceIcon(master,light_image=_draw(name,'#ffffff' if active else '#475569'),
                          dark_image=_draw(name,'#ffffff' if active else '#cbd5e1'),size=(size,size))
