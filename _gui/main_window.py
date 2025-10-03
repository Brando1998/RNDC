from tkinter import Tk, Button, Label, Frame, filedialog
from _core.navegador import crear_driver
from _core.remesas import ejecutar_remesas
from _core.manifiestos import ejecutar_manifiestos
from _utils.archivos import cargar_codigos_txt
from tkinter import messagebox
from _utils.logger import obtener_logger, TipoProceso
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
        self.pausa_event.set()
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

        seccion_archivo = Frame(frame_remesas_contenido)
        seccion_archivo.pack(pady=5)
        Button(seccion_archivo, text="📂 Seleccionar Archivo TXT", command=self.seleccionar_archivo_remesas).pack()
        self.etiqueta_archivo_remesas = Label(seccion_archivo, text="", fg="gray")
        self.etiqueta_archivo_remesas.pack()

        self.etiqueta_estado_remesas = Label(frame_remesas_contenido, text="", fg="blue")
        self.etiqueta_estado_remesas.pack(pady=5)

        self.etiqueta_archivo_manifiestos = None
        self.etiqueta_estado_manifiestos = None

        Button(frame_remesas_contenido, text="▶ Ejecutar llenado automático", command=self.ejecutar_remesas, bg="#4CAF50", fg="white", width=30).pack(pady=10)

        frame_botones_control = Frame(frame_remesas_contenido)
        frame_botones_control.pack(pady=10)

        self.boton_pausar = Button(frame_botones_control, text="⏸ Pausar", command=self.pausar_remesas, width=10)
        self.boton_pausar.grid(row=0, column=0, padx=5)

        self.boton_continuar = Button(frame_botones_control, text="▶ Continuar", command=self.continuar_remesas, width=10)
        self.boton_continuar.grid(row=0, column=1, padx=5)

        self.boton_cancelar = Button(frame_botones_control, text="⛔ Cancelar", command=self.cancelar_remesas, width=10)
        self.boton_cancelar.grid(row=0, column=2, padx=5)

        Button(self.frame_remesas, text="⬅ Volver al menú", command=self.mostrar_frame_inicio).pack(pady=15)

        # MANIFIESTOS
        titulo_manifiestos = Label(self.frame_manifiestos, text="🚛 Procesamiento de Manifiestos", font=("Helvetica", 13, "bold"))
        titulo_manifiestos.pack(pady=(10, 15))

        frame_manifiestos_contenido = Frame(self.frame_manifiestos)
        frame_manifiestos_contenido.pack(pady=5)

        seccion_archivo_manifiestos = Frame(frame_manifiestos_contenido)
        seccion_archivo_manifiestos.pack(pady=5)
        Button(seccion_archivo_manifiestos, text="📂 Seleccionar Archivo TXT", command=self.seleccionar_archivo_manifiestos).pack()
        self.etiqueta_archivo_manifiestos = Label(seccion_archivo_manifiestos, text="", fg="gray")
        self.etiqueta_archivo_manifiestos.pack()

        self.etiqueta_estado_manifiestos = Label(frame_manifiestos_contenido, text="", fg="blue")
        self.etiqueta_estado_manifiestos.pack(pady=5)

        Button(frame_manifiestos_contenido, text="▶ Ejecutar llenado automático", command=self.ejecutar_manifiestos, bg="#4CAF50", fg="white", width=30).pack(pady=10)
        frame_botones_control_manifiestos = Frame(frame_manifiestos_contenido)
        frame_botones_control_manifiestos.pack(pady=10)

        self.boton_pausar_manifiestos = Button(frame_botones_control_manifiestos, text="⏸ Pausar", command=self.pausar_manifiestos, width=10)
        self.boton_pausar_manifiestos.grid(row=0, column=0, padx=5)

        self.boton_continuar_manifiestos = Button(frame_botones_control_manifiestos, text="▶ Continuar", command=self.continuar_manifiestos, width=10)
        self.boton_continuar_manifiestos.grid(row=0, column=1, padx=5)

        self.boton_cancelar_manifiestos = Button(frame_botones_control_manifiestos, text="⛔ Cancelar", command=self.cancelar_manifiestos, width=10)
        self.boton_cancelar_manifiestos.grid(row=0, column=2, padx=5)

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
        else:
            self.boton_pausar.config(relief="raised", bg="lightgray", fg="black")
            self.boton_continuar.config(relief="raised", bg="lightgray", fg="black")
            self.boton_cancelar.config(bg="lightgray", fg="black")

    def pausar_manifiestos(self):
        self.pausa_event.clear()
        self.etiqueta_estado_manifiestos.config(text="⏸ Proceso pausado.")
        self.actualizar_estilo_botones_manifiestos(estado="pausado")

    def continuar_manifiestos(self):
        self.pausa_event.set()
        self.etiqueta_estado_manifiestos.config(text="▶ Continuando proceso...")
        self.actualizar_estilo_botones_manifiestos(estado="ejecutando")

    def cancelar_manifiestos(self):
        self.cancelar_flag = True
        self.pausa_event.set()
        self.etiqueta_estado_manifiestos.config(text="❌ Cancelando proceso...")
        self.actualizar_estilo_botones_manifiestos(estado="cancelado")

    def actualizar_estilo_botones_manifiestos(self, estado):
        if estado == "pausado":
            self.boton_pausar_manifiestos.config(relief="sunken", bg="orange", fg="white")
            self.boton_continuar_manifiestos.config(relief="raised", bg="lightgray", fg="black")
            self.boton_cancelar_manifiestos.config(bg="lightgray", fg="black")
        elif estado == "ejecutando":
            self.boton_pausar_manifiestos.config(relief="raised", bg="lightgray", fg="black")
            self.boton_continuar_manifiestos.config(relief="sunken", bg="green", fg="white")
            self.boton_cancelar_manifiestos.config(bg="lightgray", fg="black")
        elif estado == "cancelado":
            self.boton_pausar_manifiestos.config(relief="raised", bg="lightgray", fg="black")
            self.boton_continuar_manifiestos.config(relief="raised", bg="lightgray", fg="black")
            self.boton_cancelar_manifiestos.config(bg="red", fg="white")
        else:
            self.boton_pausar_manifiestos.config(relief="raised", bg="lightgray", fg="black")
            self.boton_continuar_manifiestos.config(relief="raised", bg="lightgray", fg="black")
            self.boton_cancelar_manifiestos.config(bg="lightgray", fg="black")

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
        self.pausa_event.set()
        driver = crear_driver()

        def run_with_stats():
            try:
                ejecutar_remesas(driver, self.codigos_remesas, self.actualizar_estado_remesas, self.pausa_event, lambda: self.cancelar_flag)
            finally:
                if not self.cancelar_flag:
                    self.mostrar_estadisticas(TipoProceso.REMESA)

        self.thread_remesas = threading.Thread(target=run_with_stats)
        self.thread_remesas.start()

    def actualizar_estado_remesas(self, mensaje):
        self.etiqueta_estado_remesas.config(text=mensaje)
        self.ventana.update()

    def seleccionar_archivo_manifiestos(self):
        archivo = filedialog.askopenfilename(filetypes=[("Archivos TXT", "*.txt")])
        if archivo:
            self.codigos_manifiestos, nombre = cargar_codigos_txt(archivo, 8)
            self.etiqueta_archivo_manifiestos.config(text=f"📄 {nombre}")
            self.etiqueta_estado_manifiestos.config(text=f"✅ Se cargaron {len(self.codigos_manifiestos)} manifiestos.")

    def ejecutar_manifiestos(self):
        self.cancelar_flag = False
        self.pausa_event.set()
        
        def run_with_stats():
            driver = crear_driver()
            try:
                ejecutar_manifiestos(driver, self.codigos_manifiestos, self.actualizar_estado_manifiestos, self.pausa_event, lambda: self.cancelar_flag)
            finally:
                if not self.cancelar_flag:
                    self.mostrar_estadisticas(TipoProceso.MANIFIESTO)

        self.thread_manifiestos = threading.Thread(target=run_with_stats)
        self.thread_manifiestos.start()

    def actualizar_estado_manifiestos(self, mensaje):
        self.etiqueta_estado_manifiestos.config(text=mensaje)
        self.ventana.update()

    def mostrar_estadisticas(self, tipo_proceso):
        """Muestra estadísticas mejoradas al finalizar"""
        logger = obtener_logger(tipo_proceso)
        reporte = logger.generar_reporte()
        
        # Parsear estadísticas
        stats = self.parsear_reporte(reporte)
        
        # Crear mensaje formateado
        tipo_nombre = "Remesas" if tipo_proceso == TipoProceso.REMESA else "Manifiestos"
        
        mensaje = f"""
═══════════════════════════════════
    📊 RESULTADOS - {tipo_nombre.upper()}
═══════════════════════════════════

📋 Total Procesados: {stats['total']}

✅ Exitosos: {stats['exitosos']} ({stats['tasa_exito']:.1f}%)
⚠️  Con Alertas: {stats['alertas']}
❌ Fallidos: {stats['fallidos']}

⏱️  Tiempo Total: {stats['tiempo_total']}

═══════════════════════════════════

Los logs detallados están en la carpeta _logs/

¿Desea abrir la carpeta de logs?
"""
        
        result = messagebox.askyesno("Proceso Completado", mensaje)
        
        if result:
            import os
            import subprocess
            import platform
            
            logs_path = os.path.abspath("_logs")
            
            try:
                if platform.system() == 'Windows':
                    os.startfile(logs_path)
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.Popen(['open', logs_path])
                else:  # Linux
                    subprocess.Popen(['xdg-open', logs_path])
            except Exception as e:
                messagebox.showinfo("Ruta de Logs", f"Logs guardados en:\n{logs_path}")

    def parsear_reporte(self, reporte):
        """Extrae estadísticas del reporte"""
        stats = {
            'total': 0,
            'exitosos': 0,
            'alertas': 0,
            'fallidos': 0,
            'tasa_exito': 0.0,
            'tiempo_total': 'N/A'
        }
        
        try:
            lines = reporte.split('\n')
            for line in lines:
                if 'Total procesados:' in line:
                    stats['total'] = int(line.split(':')[1].strip())
                elif 'Exitosos:' in line or '✅' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        num = parts[1].split('(')[0].strip()
                        stats['exitosos'] = int(num)
                elif 'Con alertas:' in line or '⚠️' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        num = parts[1].split('(')[0].strip()
                        stats['alertas'] = int(num)
                elif 'Fallidos:' in line or '❌' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        num = parts[1].split('(')[0].strip()
                        stats['fallidos'] = int(num)
                elif 'Tiempo total:' in line or '⏱️' in line:
                    stats['tiempo_total'] = line.split(':')[1].strip()
            
            if stats['total'] > 0:
                stats['tasa_exito'] = (stats['exitosos'] / stats['total']) * 100
        
        except Exception as e:
            print(f"Error parseando reporte: {e}")
        
        return stats