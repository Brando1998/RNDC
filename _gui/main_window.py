from tkinter import Tk, Button, Label, Frame, filedialog
from _core.navegador import crear_driver
from _core.remesas import ejecutar_remesas
from _core.manifiestos import ejecutar_manifiestos
from _utils.archivos import cargar_codigos_txt
from tkinter import messagebox
from _utils.logger import RUTA_LOG_REMESAS
import threading



class AppGUI:
    def __init__(self, root):
        self.ventana = root
        self.codigos_remesas = []
        self.codigos_manifiestos = []

        self.frame_inicio = Frame(self.ventana)
        self.frame_remesas = Frame(self.ventana)
        self.frame_manifiestos = Frame(self.ventana)

        self.pausa_event = threading.Event()
        self.pausa_event.set()  # El proceso inicia sin pausa
        self.cancelar_flag = False
        self.thread_remesas = None
        self.setup_gui()

        self.actualizar_estilo_botones("default")

    def setup_gui(self):
        self.ventana.title("Automatizador RNDC")
        self.ventana.geometry("520x420")

        # INICIO
        Label(self.frame_inicio, text="Seleccione el tipo de proceso", font=("Helvetica", 14, "bold")).pack(pady=20)
        Button(self.frame_inicio, text="Remesas", width=20, command=self.mostrar_frame_remesas).pack(pady=10)
        Button(self.frame_inicio, text="Manifiestos", width=20, command=self.mostrar_frame_manifiestos).pack(pady=10)
        self.frame_inicio.pack()

        # REMESAS
        titulo = Label(self.frame_remesas, text="📦 Procesamiento de Remesas", font=("Helvetica", 13, "bold"))
        titulo.pack(pady=(10, 15))

        frame_remesas_contenido = Frame(self.frame_remesas)
        frame_remesas_contenido.pack(pady=5)

        # Cargar archivo
        seccion_archivo = Frame(frame_remesas_contenido)
        seccion_archivo.pack(pady=5)
        Button(seccion_archivo, text="📂 Seleccionar Archivo TXT", command=self.seleccionar_archivo_remesas).pack()
        self.etiqueta_archivo_remesas = Label(seccion_archivo, text="", fg="gray")
        self.etiqueta_archivo_remesas.pack()

        # Estado
        self.etiqueta_estado_remesas = Label(frame_remesas_contenido, text="", fg="blue")
        self.etiqueta_estado_remesas.pack(pady=5)

        self.etiqueta_archivo_manifiestos = None
        self.etiqueta_estado_manifiestos = None

        # Ejecutar
        Button(frame_remesas_contenido, text="▶ Ejecutar llenado automático", command=self.ejecutar_remesas, bg="#4CAF50", fg="white", width=30).pack(pady=10)

        # Control
        frame_botones_control = Frame(frame_remesas_contenido)
        frame_botones_control.pack(pady=10)

        self.boton_pausar = Button(frame_botones_control, text="⏸ Pausar", command=self.pausar_remesas, width=10)
        self.boton_pausar.grid(row=0, column=0, padx=5)

        self.boton_continuar = Button(frame_botones_control, text="▶ Continuar", command=self.continuar_remesas, width=10)
        self.boton_continuar.grid(row=0, column=1, padx=5)

        self.boton_cancelar = Button(frame_botones_control, text="⛔ Cancelar", command=self.cancelar_remesas, width=10)
        self.boton_cancelar.grid(row=0, column=2, padx=5)

        # Volver
        Button(self.frame_remesas, text="⬅ Volver al menú", command=self.mostrar_frame_inicio).pack(pady=15)

        # MANIFIESTOS
        titulo_manifiestos = Label(self.frame_manifiestos, text="🚛 Procesamiento de Manifiestos", font=("Helvetica", 13, "bold"))
        titulo_manifiestos.pack(pady=(10, 15))

        frame_manifiestos_contenido = Frame(self.frame_manifiestos)
        frame_manifiestos_contenido.pack(pady=5)

        # Cargar archivo
        seccion_archivo_manifiestos = Frame(frame_manifiestos_contenido)
        seccion_archivo_manifiestos.pack(pady=5)
        Button(seccion_archivo_manifiestos, text="📂 Seleccionar Archivo TXT", command=self.seleccionar_archivo_manifiestos).pack()
        self.etiqueta_archivo_manifiestos = Label(seccion_archivo_manifiestos, text="", fg="gray")
        self.etiqueta_archivo_manifiestos.pack()

        # Estado
        self.etiqueta_estado_manifiestos = Label(frame_manifiestos_contenido, text="", fg="blue")
        self.etiqueta_estado_manifiestos.pack(pady=5)

        # Ejecutar
        Button(frame_manifiestos_contenido, text="▶ Ejecutar llenado automático", command=self.ejecutar_manifiestos, bg="#4CAF50", fg="white", width=30).pack(pady=10)

        # Volver
        Button(self.frame_manifiestos, text="⬅ Volver al menú", command=self.mostrar_frame_inicio).pack(pady=15)




    def pausar_remesas(self):
        self.pausa_event.clear()
        self.etiqueta_estado_remesas.config(text="⏸ Proceso pausado.")
        self.actualizar_estilo_botones(estado="pausado")

    def continuar_remesas(self):
        self.pausa_event.set()
        self.etiqueta_estado_remesas.config(text="▶ Continuando proceso...")
        self.actualizar_estilo_botones(estado="ejecutando")

    def cancelar_remesas(self):
        self.cancelar_flag = True
        self.pausa_event.set()
        self.etiqueta_estado_remesas.config(text="❌ Cancelando proceso...")
        self.actualizar_estilo_botones(estado="cancelado")
    
    def actualizar_estilo_botones(self, estado):
        if estado == "pausado":
            self.boton_pausar.config(relief="sunken", bg="orange", fg="white")
            self.boton_continuar.config(relief="raised", bg="lightgray", fg="black")
            self.boton_cancelar.config(bg="lightgray", fg="black")

        elif estado == "ejecutando":
            self.boton_pausar.config(relief="raised", bg="lightgray", fg="black")
            self.boton_continuar.config(relief="sunken", bg="green", fg="white")
            self.boton_cancelar.config(bg="lightgray", fg="black")

        elif estado == "cancelado":
            self.boton_pausar.config(relief="raised", bg="lightgray", fg="black")
            self.boton_continuar.config(relief="raised", bg="lightgray", fg="black")
            self.boton_cancelar.config(bg="red", fg="white")

        else:  # estado por defecto
            self.boton_pausar.config(relief="raised", bg="lightgray", fg="black")
            self.boton_continuar.config(relief="raised", bg="lightgray", fg="black")
            self.boton_cancelar.config(bg="lightgray", fg="black")



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
        self.cancelar_flag = False
        self.pausa_event.set()  # Asegura que el proceso no está pausado
        driver = crear_driver()

        self.thread_remesas = threading.Thread(
            target=ejecutar_remesas,
            args=(driver, self.codigos_remesas, self.actualizar_estado_remesas, self.pausa_event, lambda: self.cancelar_flag)
        )
        self.thread_remesas.start()



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
