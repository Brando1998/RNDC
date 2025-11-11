from tkinter import Tk
from _gui.main_window import AppGUI

# Intentar importar sistema de actualizaciones
try:
    from _utils.actualizaciones import verificar_al_iniciar, VERSION_ACTUAL
    TIENE_ACTUALIZACIONES = True
except ImportError:
    VERSION_ACTUAL = "1.0.0"
    TIENE_ACTUALIZACIONES = False

if __name__ == "__main__":
    root = Tk()
    root.title(f"AutoRNDC - v{VERSION_ACTUAL}")
    
    # Verificar actualizaciones si el módulo existe
    if TIENE_ACTUALIZACIONES:
        root.after(2000, lambda: verificar_al_iniciar())
    
    app = AppGUI(root)
    root.mainloop()