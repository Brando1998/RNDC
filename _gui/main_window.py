# -*- coding: utf-8 -*-
from tkinter import Tk, Button, Label, Frame, filedialog, Scale, HORIZONTAL, messagebox, Toplevel, Canvas
from tkinter import ttk
from _core.navegador import crear_driver
from _core.remesas import ejecutar_remesas, ProcesadorParalelo
from _core.manifiestos import ejecutar_manifiestos
from _utils.archivos import cargar_codigos_txt
from _utils.logger import obtener_logger, TipoProceso
import threading
import os
import subprocess
import platform


class VentanaMonitoreo(Toplevel):
    def __init__(self, parent, num_sesiones):
        super().__init__(parent)
        self.title("Monitor de Sesiones Paralelas")
        self.geometry("800x600")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        Label(self, text="Procesamiento Paralelo de Remesas", font=("Helvetica", 14, "bold")).pack(pady=10)
        
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
        self.btn_pausar = Button(btn_frame, text="Pausar Todas", command=self.pausar_callback, width=15)
        self.btn_pausar.grid(row=0, column=0, padx=5)
        self.btn_continuar = Button(btn_frame, text="Continuar Todas", command=self.continuar_callback, width=15)
        self.btn_continuar.grid(row=0, column=1, padx=5)
        self.btn_cancelar = Button(btn_frame, text="Cancelar Todas", command=self.cancelar_callback, width=15, bg="red", fg="white")
        self.btn_cancelar.grid(row=0, column=2, padx=5)
        
        self.pausar_callback = None
        self.continuar_callback = None
        self.cancelar_callback = None
    
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
        self.label_global.config(text=f"Total: {procesadas}/{total} remesas | Sesiones: {sesiones_completadas}/{sesiones_totales} completadas")
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
        self.ventana_monitor = None
        self.num_sesiones_seleccionadas = 2
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
        self.frame_inicio.pack()
        
        self._setup_remesas()
        self._setup_manifiestos()
    
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
        self.etiqueta_estado_manifiestos = Label(self.frame_manifiestos, text="", fg="blue")
        self.etiqueta_estado_manifiestos.pack(pady=5)
        Button(self.frame_manifiestos, text="Ejecutar llenado automatico", command=self.ejecutar_manifiestos, bg="#4CAF50", fg="white", width=30).pack(pady=15)
        Button(self.frame_manifiestos, text="Volver al menu", command=self.mostrar_frame_inicio).pack(pady=15)
    
    def mostrar_frame_inicio(self):
        self.frame_remesas.pack_forget()
        self.frame_manifiestos.pack_forget()
        self.frame_inicio.pack()
    
    def mostrar_frame_remesas(self):
        self.frame_inicio.pack_forget()
        self.frame_manifiestos.pack_forget()
        self.frame_remesas.pack()
    
    def mostrar_frame_manifiestos(self):
        self.frame_inicio.pack_forget()
        self.frame_remesas.pack_forget()
        self.frame_manifiestos.pack()
    
    def actualizar_num_sesiones(self, valor):
        self.num_sesiones_seleccionadas = int(valor)
        self.label_sesiones.config(text=f"{valor} sesiones")
    
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
            self.etiqueta_estado_manifiestos.config(text=f"Se cargaron {len(self.codigos_manifiestos)} manifiestos.")
    
    def ejecutar_remesas_paralelo(self):
        if not self.codigos_remesas:
            messagebox.showwarning("Sin datos", "Por favor, cargue un archivo TXT primero.")
            return
        if len(self.codigos_remesas) < self.num_sesiones_seleccionadas:
            messagebox.showwarning("Pocos datos", f"El archivo tiene {len(self.codigos_remesas)} remesas.\nNo se pueden crear {self.num_sesiones_seleccionadas} sesiones.\nReduzca el numero de sesiones.")
            return
        
        self.ventana_monitor = VentanaMonitoreo(self.ventana, self.num_sesiones_seleccionadas)
        self.ventana_monitor.pausar_callback = self.pausar_todas
        self.ventana_monitor.continuar_callback = self.continuar_todas
        self.ventana_monitor.cancelar_callback = self.cancelar_todas
        
        self.procesador = ProcesadorParalelo(self.codigos_remesas, self.num_sesiones_seleccionadas, self.actualizar_sesion_callback)
        self.procesador.iniciar_todas()
        self.monitorear_progreso_global()
    
    def actualizar_sesion_callback(self, sesion_id, mensaje, progreso, total):
        if self.ventana_monitor:
            self.ventana_monitor.actualizar_sesion(sesion_id, mensaje, progreso, total)
    
    def monitorear_progreso_global(self):
        if not self.procesador or not self.ventana_monitor:
            return
        stats = self.procesador.obtener_estadisticas()
        self.ventana_monitor.actualizar_global(stats['procesadas'], stats['total'], stats['sesiones_completadas'], stats['sesiones_totales'])
        if self.procesador.todas_completadas():
            self.mostrar_resumen_final()
            return
        self.ventana.after(1000, self.monitorear_progreso_global)
    
    def mostrar_resumen_final(self):
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
    
    def pausar_todas(self):
        if self.procesador:
            self.procesador.pausar_todas()
    
    def continuar_todas(self):
        if self.procesador:
            self.procesador.continuar_todas()
    
    def cancelar_todas(self):
        if self.procesador:
            self.procesador.cancelar_todas()
    
    def ejecutar_manifiestos(self):
        if not self.codigos_manifiestos:
            messagebox.showwarning("Sin datos", "Por favor, cargue un archivo TXT primero.")
            return
        self.cancelar_flag = False
        self.pausa_event.set()
        def run():
            driver = crear_driver()
            try:
                ejecutar_manifiestos(driver, self.codigos_manifiestos, self.actualizar_estado_manifiestos, self.pausa_event, lambda: self.cancelar_flag)
            finally:
                if not self.cancelar_flag:
                    logger = obtener_logger(TipoProceso.MANIFIESTO)
                    messagebox.showinfo("Completado", logger.generar_reporte())
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
    
    def actualizar_estado_manifiestos(self, mensaje):
        self.etiqueta_estado_manifiestos.config(text=mensaje)
        self.ventana.update()