from tkinter import Tk
from _gui.main_window import AppGUI
from _utils.actualizaciones import verificar_al_iniciar, VERSION_ACTUAL

if __name__ == "__main__":
    root = Tk()
    root.title(f"AutoRNDC - v{VERSION_ACTUAL}")
    root.after(2000, lambda: verificar_al_iniciar())
    app = AppGUI(root)
    root.mainloop()
