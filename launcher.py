"""Desktop entry point, including opening a .registro document by double click."""
from pathlib import Path
import os,sys,time


def launch():
    if len(sys.argv)>1 and Path(sys.argv[1]).suffix.lower()=='.registro':
        import documento,app_storage
        try:
            target=app_storage.data_dir()/f'documento-{time.time_ns()}.db'
            documento.open_document(Path(sys.argv[1]).resolve(),target)
            app_storage.activate_period(target)
            os.environ['REGISTRO_DB_PATH']=str(target)
        except Exception as exc:
            import tkinter as tk
            from tkinter import messagebox
            root=tk.Tk();root.withdraw();messagebox.showerror('Documento de Registro',str(exc));root.destroy();return
    import main
    main.main()


if __name__=='__main__':launch()
