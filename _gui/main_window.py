# -*- coding: utf-8 -*-
from tkinter import Tk, Button, Label, Frame, filedialog, Scale, HORIZONTAL, messagebox, Toplevel, Canvas
from tkinter import ttk
from _core.navegador import crear_driver
from _core.remesas import ejecutar_remesas, ProcesadorParalelo
from _core.manifiestos import ejecutar_manifiestos, ProcesadorParaleloManifiestos
from _core.cambio_sede import ejecutar_cambio_sede
from _utils.archivos import cargar_codigos_txt
from _utils.logger import obtener_logger, TipoProceso
import threading
import os
import subprocess
import platform


class VentanaMonitoreo(Toplevel):
    def __init__(self, parent, num_sesiones, tipo_proceso="Remesas"):
        super().__init__(parent)
        self.title(f"Monitor de Sesiones Paralelas - {tipo_proceso}")
        self.geometry("800x600")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        Label(self, text=f"Procesamiento Paralelo de {tipo_proceso}", font=("Helvetica", 14, "bold")).pack(pady=10)
        
        main_frame = Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        canvas = Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = Frame(canvas)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.sesiones_widgets = {}
        for i in range(1, num_sesiones + 1):
            self._crear_widget_sesion(scrollable_frame, i)
        
        stats_frame = Frame(self, relief="solid", borderwidth=2, bg="#f0f0f0")
        stats_frame.pack(fill="x", padx=10, pady=10)
        Label(stats_frame, text="Progreso Global", font=("Helvetica", 12, "bold"), bg="#f0f0f0").pack(pady=5)
        self.label_global = Label(stats_frame, text="Iniciando...", font=("Helvetica", 10), bg="#f0f0f0")
        self.label_global.pack(pady=5)
        self.progress_global = ttk.Progressbar(stats_frame, mode='determinate', length=700)
        self.progress_global.pack(pady=5)
        
        btn_frame = Frame(self)
        btn_frame.pack(pady=10)
        
        # Definir callbacks como None primero
        self.pausar_callback = None
        self.continuar_callback = None
        self.cancelar_callback = None
        
        self.btn_pausar = Button(btn_frame, text="Pausar Todas", command=lambda: self.pausar_callback() if self.pausar_callback else None, width=15)
        self.btn_pausar.grid(row=0, column=0, padx=5)
        self.btn_continuar = Button(btn_frame, text="Continuar Todas", command=lambda: self.continuar_callback() if self.continuar_callback else None, width=15)
        self.btn_continuar.grid(row=0, column=1, padx=5)
        self.btn_cancelar = Button(btn_frame, text="Cancelar Todas", command=lambda: self.cancelar_callback() if self.cancelar_callback else None, width=15, bg="red", fg="white")
        self.btn_cancelar.grid(row=0, column=2, padx=5)
    
    def _crear_widget_sesion(self, parent, sesion_id):
        frame = Frame(parent, relief="solid", borderwidth=1, bg="white")
        frame.pack(fill="x", padx=5, pady=5)
        titulo = Label(frame, text=f"Sesion {sesion_id}", font=("Helvetica", 11, "bold"), bg="white")
        titulo.pack(anchor="w", padx=10, pady=5)
        estado = Label(frame, text="Esperando...", fg="gray", bg="white")
        estado.pack(anchor="w", padx=20)
        progress = ttk.Progressbar(frame, mode='determinate', length=700)
        progress.pack(padx=20, pady=5)
        label_progreso = Label(frame, text="0 / 0", fg="blue", bg="white")
        label_progreso.pack(anchor="w", padx=20, pady=5)
        self.sesiones_widgets[sesion_id] = {'frame': frame, 'estado': estado, 'progress': progress, 'label_progreso': label_progreso}
    
    def actualizar_sesion(self, sesion_id, mensaje, progreso, total):
        if sesion_id not in self.sesiones_widgets:
            return
        widgets = self.sesiones_widgets[sesion_id]
        widgets['estado'].config(text=mensaje)
        widgets['label_progreso'].config(text=f"{progreso} / {total}")
        if total > 0:
            porcentaje = (progreso / total) * 100
            widgets['progress']['value'] = porcentaje
    
    def actualizar_global(self, procesadas, total, sesiones_completadas, sesiones_totales):
        porcentaje = (procesadas / total * 100) if total > 0 else 0
        tipo = "remesas" if "Remesas" in self.title() else "manifiestos"
        self.label_global.config(text=f"Total: {procesadas}/{total} {tipo} | Sesiones: {sesiones_completadas}/{sesiones_totales} completadas")
        self.progress_global['value'] = porcentaje
    
    def on_closing(self):
        if messagebox.askokcancel("Cerrar", "Desea cancelar todas las sesiones y cerrar?"):
            if self.cancelar_callback:
                self.cancelar_callback()
            self.destroy()


class AppGUI:
    def __init__(self, root):
        self.ventana = root
        self.codigos_remesas = []
        self.codigos_manifiestos = []
        self.pausa_event = threading.Event()
        self.pausa_event.set()
        self.cancelar_flag = False
        self.procesador = None
        self.procesador_manifiestos = None
        self.ventana_monitor = None
        self.num_sesiones_seleccionadas = 2
        self.num_sesiones_manifiestos = 2
        self.ruta_excel_cambio_sede = None
        self.frame_cambio_sede = Frame(self.ventana)
        self.frame_inicio = Frame(self.ventana)
        self.frame_remesas = Frame(self.ventana)
        self.frame_manifiestos = Frame(self.ventana)
        self.setup_gui()
    
    def setup_gui(self):
        self.ventana.title("Automatizador RNDC")
        self.ventana.geometry("580x500")
        
        Label(self.frame_inicio, text="Seleccione el tipo de proceso", font=("Helvetica", 14, "bold")).pack(pady=20)
        Button(self.frame_inicio, text="Remesas", width=20, command=self.mostrar_frame_remesas).pack(pady=10)
        Button(self.frame_inicio, text="Manifiestos", width=20, command=self.mostrar_frame_manifiestos).pack(pady=10)
        Button(self.frame_inicio, text="Cambio de Sede", width=20, command=self.mostrar_frame_cambio_sede, bg="#FF9800", fg="white").pack(pady=10)
        self.frame_inicio.pack()
        
        self._setup_remesas()
        self._setup_manifiestos()
        self._setup_cambio_sede()
    
    def _setup_remesas(self):
        titulo = Label(self.frame_remesas, text="Procesamiento de Remesas", font=("Helvetica", 13, "bold"))
        titulo.pack(pady=(10, 15))
        
        frame_archivo = Frame(self.frame_remesas)
        frame_archivo.pack(pady=10)
        Button(frame_archivo, text="Seleccionar Archivo TXT", command=self.seleccionar_archivo_remesas).pack()
        self.etiqueta_archivo_remesas = Label(frame_archivo, text="", fg="gray")
        self.etiqueta_archivo_remesas.pack()
        
        frame_config = Frame(self.frame_remesas, relief="solid", borderwidth=1)
        frame_config.pack(pady=15, padx=20, fill="x")
        Label(frame_config, text="Configuracion de Procesamiento Paralelo", font=("Helvetica", 10, "bold")).pack(pady=5)
        
        frame_sesiones = Frame(frame_config)
        frame_sesiones.pack(pady=10)
        Label(frame_sesiones, text="Numero de sesiones paralelas:").grid(row=0, column=0, padx=5)
        self.scale_sesiones = Scale(frame_sesiones, from_=1, to=5, orient=HORIZONTAL, length=200, command=self.actualizar_num_sesiones)
        self.scale_sesiones.set(2)
        self.scale_sesiones.grid(row=0, column=1, padx=5)
        self.label_sesiones = Label(frame_sesiones, text="2 sesiones", fg="blue", font=("Helvetica", 10, "bold"))
        self.label_sesiones.grid(row=0, column=2, padx=5)
        Label(frame_config, text="Cada sesion procesara una parte del archivo en paralelo", fg="gray", font=("Helvetica", 8)).pack(pady=5)
        
        Button(self.frame_remesas, text="Ejecutar Procesamiento Paralelo", command=self.ejecutar_remesas_paralelo, bg="#4CAF50", fg="white", width=35, font=("Helvetica", 10, "bold")).pack(pady=15)
        self.etiqueta_estado_remesas = Label(self.frame_remesas, text="", fg="blue")
        self.etiqueta_estado_remesas.pack(pady=5)
        Button(self.frame_remesas, text="Volver al menu", command=self.mostrar_frame_inicio).pack(pady=15)
    
    def _setup_manifiestos(self):
        titulo = Label(self.frame_manifiestos, text="Procesamiento de Manifiestos", font=("Helvetica", 13, "bold"))
        titulo.pack(pady=(10, 15))
        
        frame_archivo = Frame(self.frame_manifiestos)
        frame_archivo.pack(pady=10)
        Button(frame_archivo, text="Seleccionar Archivo TXT", command=self.seleccionar_archivo_manifiestos).pack()
        self.etiqueta_archivo_manifiestos = Label(frame_archivo, text="", fg="gray")
        self.etiqueta_archivo_manifiestos.pack()
        
        frame_config = Frame(self.frame_manifiestos, relief="solid", borderwidth=1)
        frame_config.pack(pady=15, padx=20, fill="x")
        Label(frame_config, text="Configuracion de Procesamiento Paralelo", font=("Helvetica", 10, "bold")).pack(pady=5)
        
        frame_sesiones_man = Frame(frame_config)
        frame_sesiones_man.pack(pady=10)
        Label(frame_sesiones_man, text="Numero de sesiones paralelas:").grid(row=0, column=0, padx=5)
        self.scale_sesiones_man = Scale(frame_sesiones_man, from_=1, to=5, orient=HORIZONTAL, length=200, command=self.actualizar_num_sesiones_man)
        self.scale_sesiones_man.set(2)
        self.scale_sesiones_man.grid(row=0, column=1, padx=5)
        self.label_sesiones_man = Label(frame_sesiones_man, text="2 sesiones", fg="blue", font=("Helvetica", 10, "bold"))
        self.label_sesiones_man.grid(row=0, column=2, padx=5)
        Label(frame_config, text="Cada sesion procesara una parte del archivo en paralelo", fg="gray", font=("Helvetica", 8)).pack(pady=5)
        
        Button(self.frame_manifiestos, text="Ejecutar Procesamiento Paralelo", command=self.ejecutar_manifiestos_paralelo, bg="#4CAF50", fg="white", width=35, font=("Helvetica", 10, "bold")).pack(pady=15)
        self.etiqueta_estado_manifiestos = Label(self.frame_manifiestos, text="", fg="blue")
        self.etiqueta_estado_manifiestos.pack(pady=5)
        Button(self.frame_manifiestos, text="Volver al menu", command=self.mostrar_frame_inicio).pack(pady=15)
    
    def _setup_cambio_sede(self):
        """Configura la interfaz para cambio de sede."""
        titulo = Label(self.frame_cambio_sede, text="Cambio Masivo de Sede", font=("Helvetica", 13, "bold"))
        titulo.pack(pady=(10, 15))
        
        # Información del proceso
        info_frame = Frame(self.frame_cambio_sede, relief="solid", borderwidth=1, bg="#FFF3E0")
        info_frame.pack(pady=10, padx=20, fill="x")
        
        Label(info_frame, text="ℹ️ Información del Proceso", font=("Helvetica", 10, "bold"), bg="#FFF3E0").pack(pady=5)
        Label(info_frame, text="Este proceso cambia la sede del generador de carga en las remesas.", bg="#FFF3E0", font=("Helvetica", 9)).pack(pady=2)
        Label(info_frame, text="• Lee datos desde un archivo Excel", bg="#FFF3E0", font=("Helvetica", 9), anchor="w").pack(fill="x", padx=10)
        Label(info_frame, text="• Columnas requeridas: NUMIDPROPIETARIO (NIT) y REM_ORIG (Sede Origen)", bg="#FFF3E0", font=("Helvetica", 9), anchor="w").pack(fill="x", padx=10)
        Label(info_frame, text="• Sede destino: BOGOTA (Fija)", bg="#FFF3E0", font=("Helvetica", 9), anchor="w").pack(fill="x", padx=10)
        Label(info_frame, text="• Observaciones: 'error de digitacion' (Fijo)", bg="#FFF3E0", font=("Helvetica", 9), anchor="w").pack(fill="x", padx=10)
        
        # Selección de archivo
        frame_archivo = Frame(self.frame_cambio_sede)
        frame_archivo.pack(pady=15)
        Button(frame_archivo, text="📂 Seleccionar Archivo Excel", command=self.seleccionar_excel_cambio_sede, bg="#4CAF50", fg="white", width=25).pack()
        self.etiqueta_archivo_cambio_sede = Label(frame_archivo, text="", fg="gray")
        self.etiqueta_archivo_cambio_sede.pack(pady=5)
        
        # Estado
        self.etiqueta_estado_cambio_sede = Label(self.frame_cambio_sede, text="", fg="blue", wraplength=500)
        self.etiqueta_estado_cambio_sede.pack(pady=10)
        
        # Botones de acción
        btn_frame = Frame(self.frame_cambio_sede)
        btn_frame.pack(pady=15)
        
        self.boton_ejecutar_cambio_sede = Button(
            btn_frame, 
            text="▶ Ejecutar Cambio de Sede", 
            command=self.ejecutar_cambio_sede,
            bg="#FF9800", 
            fg="white", 
            width=25,
            font=("Helvetica", 10, "bold"),
            state="disabled"
        )
        self.boton_ejecutar_cambio_sede.pack(pady=5)
        
        Button(btn_frame, text="⬅ Volver al menú", command=self.mostrar_frame_inicio, width=25).pack(pady=5)

    def mostrar_frame_inicio(self):
        self.frame_remesas.pack_forget()
        self.frame_manifiestos.pack_forget()
        self.frame_cambio_sede.pack_forget()
        self.frame_inicio.pack()
    
    def mostrar_frame_remesas(self):
        self.frame_inicio.pack_forget()
        self.frame_manifiestos.pack_forget()
        self.frame_cambio_sede.pack_forget()
        self.frame_remesas.pack()
    
    def mostrar_frame_manifiestos(self):
        self.frame_inicio.pack_forget()
        self.frame_remesas.pack_forget()
        self.frame_cambio_sede.pack_forget()
        self.frame_manifiestos.pack()
    
    def mostrar_frame_cambio_sede(self):
        """Muestra el frame de cambio de sede."""
        self.frame_inicio.pack_forget()
        self.frame_remesas.pack_forget()
        self.frame_manifiestos.pack_forget()
        self.frame_cambio_sede.pack()
    
    def actualizar_num_sesiones(self, valor):
        self.num_sesiones_seleccionadas = int(valor)
        self.label_sesiones.config(text=f"{valor} sesiones")
    
    def actualizar_num_sesiones_man(self, valor):
        self.num_sesiones_manifiestos = int(valor)
        self.label_sesiones_man.config(text=f"{valor} sesiones")
    
    def seleccionar_archivo_remesas(self):
        archivo = filedialog.askopenfilename(filetypes=[("Archivos TXT", "*.txt")])
        if archivo:
            self.codigos_remesas, nombre = cargar_codigos_txt(archivo, 9)
            self.etiqueta_archivo_remesas.config(text=f"{nombre}")
            total = len(self.codigos_remesas)
            por_sesion = total // self.num_sesiones_seleccionadas
            self.etiqueta_estado_remesas.config(text=f"{total} remesas cargadas | ~{por_sesion} por sesion ({self.num_sesiones_seleccionadas} sesiones)")
    
    def seleccionar_archivo_manifiestos(self):
        archivo = filedialog.askopenfilename(filetypes=[("Archivos TXT", "*.txt")])
        if archivo:
            self.codigos_manifiestos, nombre = cargar_codigos_txt(archivo, 8)
            self.etiqueta_archivo_manifiestos.config(text=f"{nombre}")
            total = len(self.codigos_manifiestos)
            por_sesion = total // self.num_sesiones_manifiestos
            self.etiqueta_estado_manifiestos.config(text=f"{total} manifiestos cargados | ~{por_sesion} por sesion ({self.num_sesiones_manifiestos} sesiones)")
    
    def seleccionar_excel_cambio_sede(self):
        """Selecciona el archivo Excel para cambio de sede."""
        archivo = filedialog.askopenfilename(
            title="Seleccionar archivo Excel",
            filetypes=[
                ("Archivos Excel", "*.xlsx"),
                ("Archivos Excel", "*.xls"),
                ("Todos los archivos", "*.*")
            ]
        )
        
        if archivo:
            try:
                # Validar que el archivo tenga las columnas requeridas
                import pandas as pd
                df = pd.read_excel(archivo)
                
                columnas_requeridas = ['NUMIDPROPIETARIO', 'REM_ORIG']
                columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
                
                if columnas_faltantes:
                    messagebox.showerror(
                        "Columnas faltantes",
                        f"El archivo no tiene las columnas requeridas:\n{', '.join(columnas_faltantes)}"
                    )
                    return
                
                self.ruta_excel_cambio_sede = archivo
                nombre_archivo = os.path.basename(archivo)
                total_filas = len(df)
                
                self.etiqueta_archivo_cambio_sede.config(text=f"📄 {nombre_archivo}")
                self.etiqueta_estado_cambio_sede.config(
                    text=f"✅ {total_filas} registros cargados\nListo para procesar"
                )
                self.boton_ejecutar_cambio_sede["state"] = "normal"
                
            except Exception as e:
                messagebox.showerror("Error", f"Error leyendo el archivo:\n{str(e)}")
                self.etiqueta_estado_cambio_sede.config(text=f"❌ Error: {str(e)}")

    def ejecutar_cambio_sede(self):
        """Ejecuta el proceso de cambio de sede."""
        if not self.ruta_excel_cambio_sede:
            messagebox.showwarning("Sin archivo", "Por favor, seleccione un archivo Excel primero.")
            return
        
        # Confirmar ejecución
        respuesta = messagebox.askyesno(
            "Confirmar Ejecución",
            "¿Está seguro de ejecutar el cambio de sede?\n\n"
            "Este proceso modificará las remesas según los datos del Excel.\n\n"
            "Información fija:\n"
            "• NIT destino: 8600537463\n"
            "• Sede destino: BOGOTA\n"
            "• Observación: error de digitacion"
        )
        
        if not respuesta:
            return
        
        # Deshabilitar botones
        self.boton_ejecutar_cambio_sede["state"] = "disabled"
        
        # Resetear flags
        self.cancelar_flag = False
        self.pausa_event.set()
        
        def run():
            from _core.navegador import crear_driver
            driver = crear_driver()
            try:
                ejecutar_cambio_sede(
                    driver,
                    self.ruta_excel_cambio_sede,
                    self.actualizar_estado_cambio_sede,
                    self.pausa_event,
                    lambda: self.cancelar_flag
                )
            finally:
                # Reactivar botón
                self.boton_ejecutar_cambio_sede["state"] = "normal"
                if not self.cancelar_flag:
                    messagebox.showinfo(
                        "Proceso Completado",
                        "El proceso de cambio de sede ha finalizado.\n\n"
                        "Revise los logs en la carpeta 'logs' para más detalles."
                    )
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def actualizar_estado_cambio_sede(self, mensaje):
        """Actualiza el estado del cambio de sede en la GUI."""
        self.etiqueta_estado_cambio_sede.config(text=mensaje)
        self.ventana.update()
    
    def ejecutar_remesas_paralelo(self):
        if not self.codigos_remesas:
            messagebox.showwarning("Sin datos", "Por favor, cargue un archivo TXT primero.")
            return
        if len(self.codigos_remesas) < self.num_sesiones_seleccionadas:
            messagebox.showwarning("Pocos datos", f"El archivo tiene {len(self.codigos_remesas)} remesas.\nNo se pueden crear {self.num_sesiones_seleccionadas} sesiones.\nReduzca el numero de sesiones.")
            return
        
        self.ventana_monitor = VentanaMonitoreo(self.ventana, self.num_sesiones_seleccionadas, "Remesas")
        self.ventana_monitor.pausar_callback = self.pausar_todas_remesas
        self.ventana_monitor.continuar_callback = self.continuar_todas_remesas
        self.ventana_monitor.cancelar_callback = self.cancelar_todas_remesas
        
        self.procesador = ProcesadorParalelo(self.codigos_remesas, self.num_sesiones_seleccionadas, self.actualizar_sesion_callback_remesas)
        self.procesador.iniciar_todas()
        self.monitorear_progreso_global_remesas()
    
    def ejecutar_manifiestos_paralelo(self):
        if not self.codigos_manifiestos:
            messagebox.showwarning("Sin datos", "Por favor, cargue un archivo TXT primero.")
            return
        if len(self.codigos_manifiestos) < self.num_sesiones_manifiestos:
            messagebox.showwarning("Pocos datos", f"El archivo tiene {len(self.codigos_manifiestos)} manifiestos.\nNo se pueden crear {self.num_sesiones_manifiestos} sesiones.\nReduzca el numero de sesiones.")
            return
        
        self.ventana_monitor = VentanaMonitoreo(self.ventana, self.num_sesiones_manifiestos, "Manifiestos")
        self.ventana_monitor.pausar_callback = self.pausar_todas_manifiestos
        self.ventana_monitor.continuar_callback = self.continuar_todas_manifiestos
        self.ventana_monitor.cancelar_callback = self.cancelar_todas_manifiestos
        
        self.procesador_manifiestos = ProcesadorParaleloManifiestos(self.codigos_manifiestos, self.num_sesiones_manifiestos, self.actualizar_sesion_callback_manifiestos)
        self.procesador_manifiestos.iniciar_todas()
        self.monitorear_progreso_global_manifiestos()
    
    def actualizar_sesion_callback_remesas(self, sesion_id, mensaje, progreso, total):
        if self.ventana_monitor:
            self.ventana_monitor.actualizar_sesion(sesion_id, mensaje, progreso, total)
    
    def actualizar_sesion_callback_manifiestos(self, sesion_id, mensaje, progreso, total):
        if self.ventana_monitor:
            self.ventana_monitor.actualizar_sesion(sesion_id, mensaje, progreso, total)
    
    def monitorear_progreso_global_remesas(self):
        if not self.procesador or not self.ventana_monitor:
            return
        stats = self.procesador.obtener_estadisticas()
        self.ventana_monitor.actualizar_global(stats['procesadas'], stats['total'], stats['sesiones_completadas'], stats['sesiones_totales'])
        if self.procesador.todas_completadas():
            self.mostrar_resumen_final_remesas()
            return
        self.ventana.after(1000, self.monitorear_progreso_global_remesas)
    
    def monitorear_progreso_global_manifiestos(self):
        if not self.procesador_manifiestos or not self.ventana_monitor:
            return
        stats = self.procesador_manifiestos.obtener_estadisticas()
        self.ventana_monitor.actualizar_global(stats['procesadas'], stats['total'], stats['sesiones_completadas'], stats['sesiones_totales'])
        if self.procesador_manifiestos.todas_completadas():
            self.mostrar_resumen_final_manifiestos()
            return
        self.ventana.after(1000, self.monitorear_progreso_global_manifiestos)
    
    def mostrar_resumen_final_remesas(self):
        if not self.procesador:
            return
        stats = self.procesador.obtener_estadisticas()
        mensaje = f"""
===============================
   PROCESAMIENTO COMPLETADO
===============================

Total Procesadas: {stats['procesadas']} / {stats['total']}
Porcentaje: {stats['porcentaje']:.1f}%
Sesiones: {stats['sesiones_completadas']} / {stats['sesiones_totales']}

===============================

Los logs detallados estan en _logs/

Desea cerrar el monitor?
"""
        if messagebox.askyesno("Proceso Completado", mensaje):
            if self.ventana_monitor:
                self.ventana_monitor.destroy()
                self.ventana_monitor = None
    
    def mostrar_resumen_final_manifiestos(self):
        if not self.procesador_manifiestos:
            return
        stats = self.procesador_manifiestos.obtener_estadisticas()
        mensaje = f"""
===============================
   PROCESAMIENTO COMPLETADO
===============================

Total Procesados: {stats['procesadas']} / {stats['total']}
Porcentaje: {stats['porcentaje']:.1f}%
Sesiones: {stats['sesiones_completadas']} / {stats['sesiones_totales']}

===============================

Los logs detallados estan en _logs/

Desea cerrar el monitor?
"""
        if messagebox.askyesno("Proceso Completado", mensaje):
            if self.ventana_monitor:
                self.ventana_monitor.destroy()
                self.ventana_monitor = None
    
    def pausar_todas_remesas(self):
        if self.procesador:
            self.procesador.pausar_todas()
    
    def continuar_todas_remesas(self):
        if self.procesador:
            self.procesador.continuar_todas()
    
    def cancelar_todas_remesas(self):
        if self.procesador:
            self.procesador.cancelar_todas()
    
    def pausar_todas_manifiestos(self):
        if self.procesador_manifiestos:
            self.procesador_manifiestos.pausar_todas()
    
    def continuar_todas_manifiestos(self):
        if self.procesador_manifiestos:
            self.procesador_manifiestos.continuar_todas()
    
    def cancelar_todas_manifiestos(self):
        if self.procesador_manifiestos:
            self.procesador_manifiestos.cancelar_todas()
    
    def actualizar_estado_manifiestos(self, mensaje):
        self.etiqueta_estado_manifiestos.config(text=mensaje)
        self.ventana.update()