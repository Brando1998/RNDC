from tkinter import Tk, Button, Label, Frame, filedialog
from _core.navegador import crear_driver
from _core.remesas import ejecutar_remesas
from _core.manifiestos import ejecutar_manifiestos
from _utils.archivos import cargar_codigos_txt
from tkinter import messagebox
from _utils.logger import RUTA_LOG_REMESAS


class AppGUI:
    def __init__(self, root):
        self.ventana = root
        self.codigos_remesas = []
        self.codigos_manifiestos = []

        self.frame_inicio = Frame(self.ventana)
        self.frame_remesas = Frame(self.ventana)
        self.frame_manifiestos = Frame(self.ventana)

        self.setup_gui()

    def setup_gui(self):
        self.ventana.title("Automatizador RNDC")
        self.ventana.geometry("500x400")

        # INICIO
        Label(self.frame_inicio, text="Seleccione el tipo de proceso").pack(pady=20)
        Button(self.frame_inicio, text="Remesas", command=self.mostrar_frame_remesas).pack(pady=10)
        Button(self.frame_inicio, text="Manifiestos", command=self.mostrar_frame_manifiestos).pack(pady=10)
        self.frame_inicio.pack()

        # REMESAS
        Label(self.frame_remesas, text="Remesas - Subir archivo TXT").pack(pady=10)
        Button(self.frame_remesas, text="Seleccionar Archivo TXT", command=self.seleccionar_archivo_remesas).pack(pady=5)
        self.etiqueta_archivo_remesas = Label(self.frame_remesas, text="")  # <--- ESTA ETIQUETA
        self.etiqueta_archivo_remesas.pack()

        self.etiqueta_estado_remesas = Label(self.frame_remesas, text="", fg="blue")  # <--- ESTA TAMBIÉN
        self.etiqueta_estado_remesas.pack(pady=5)

        Button(self.frame_remesas, text="Ejecutar llenado automático", command=self.ejecutar_remesas).pack(pady=10)
        Button(self.frame_remesas, text="⬅ Volver al menú", command=self.mostrar_frame_inicio).pack()
        # MANIFIESTOS
        Label(self.frame_manifiestos, text="Manifiestos - Subir archivo TXT").pack(pady=10)
        Button(self.frame_manifiestos, text="Seleccionar Archivo TXT", command=self.seleccionar_archivo_manifiestos).pack(pady=5)
        self.etiqueta_archivo_manifiestos = Label(self.frame_manifiestos, text="")
        self.etiqueta_archivo_manifiestos.pack()

        self.etiqueta_estado_manifiestos = Label(self.frame_manifiestos, text="", fg="blue")
        self.etiqueta_estado_manifiestos.pack(pady=5)

        Button(self.frame_manifiestos, text="Ejecutar llenado automático", command=self.ejecutar_manifiestos).pack(pady=10)
        Button(self.frame_manifiestos, text="⬅ Volver al menú", command=self.mostrar_frame_inicio).pack()


    def mostrar_frame_inicio(self):
        self.frame_remesas.pack_forget()
        self.frame_manifiestos.pack_forget()
        self.frame_inicio.pack()

    def mostrar_frame_remesas(self):
        self.frame_inicio.pack_forget()
        self.frame_remesas.pack()

    def mostrar_frame_manifiestos(self):
        self.frame_inicio.pack_forget()
        self.frame_manifiestos.pack()

    def seleccionar_archivo_remesas(self):
        archivo = filedialog.askopenfilename(filetypes=[("Archivos TXT", "*.txt")])
        if archivo:
            self.codigos_remesas, nombre = cargar_codigos_txt(archivo, 9)
            self.etiqueta_archivo_remesas.config(text=f"📄 {nombre}")
            self.etiqueta_estado_remesas.config(text=f"✅ Se cargaron {len(self.codigos_remesas)} remesas.")

    def ejecutar_remesas(self):
        driver = crear_driver()
        ejecutar_remesas(driver, self.codigos_remesas, self.actualizar_estado_remesas)
        # Mostramos el mensaje con la ruta del CSV generado
        messagebox.showinfo(
            "Proceso completado",
            f"El archivo de errores se guardó en:\n{RUTA_LOG_REMESAS}"
        )


    def actualizar_estado_remesas(self, mensaje):
        self.etiqueta_estado_remesas.config(text=mensaje)
        self.ventana.update()  # Refresca la ventana inmediatamente
        pass


    #Manifiestos
    def seleccionar_archivo_manifiestos(self):
        archivo = filedialog.askopenfilename(filetypes=[("Archivos TXT", "*.txt")])
        if archivo:
            self.codigos_manifiestos, nombre = cargar_codigos_txt(archivo, 8)
            self.etiqueta_archivo_manifiestos.config(text=f"📄 {nombre}")
            self.etiqueta_estado_manifiestos.config(text=f"✅ Se cargaron {len(self.codigos_manifiestos)} manifiestos.")

    def ejecutar_manifiestos(self):
        driver = crear_driver()
        ejecutar_manifiestos(driver, self.codigos_manifiestos, self.actualizar_estado_manifiestos)
        messagebox.showinfo(
            "Proceso completado",
            "Los manifiestos fueron procesados. Revisa el log de errores para más detalles."
        )

    def actualizar_estado_manifiestos(self, mensaje):
        self.etiqueta_estado_manifiestos.config(text=mensaje)
        self.ventana.update()
