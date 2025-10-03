"""
Sistema de logging mejorado para RNDC.
Captura alertas, errores y eventos para análisis y mejora continua.
"""

import csv
import os
import json
import traceback
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMERACIONES
# ============================================================================
class TipoEvento(Enum):
    """Tipos de eventos a registrar."""
    EXITO = "EXITO"
    ALERTA = "ALERTA"
    ERROR = "ERROR"
    REINTENTO = "REINTENTO"
    EXCEPCION = "EXCEPCION"
    INFO = "INFO"


class TipoProceso(Enum):
    """Tipos de procesos."""
    REMESA = "REMESA"
    MANIFIESTO = "MANIFIESTO"


# ============================================================================
# RUTAS DE ARCHIVOS
# ============================================================================
def obtener_ruta_log(nombre_base="log", tipo_proceso=None):
    """
    Genera una ruta de archivo de log con nombre dinámico por fecha-hora.
    
    Args:
        nombre_base: Prefijo del nombre del archivo
        tipo_proceso: Tipo de proceso (REMESA o MANIFIESTO)
    
    Returns:
        str: Ruta completa del archivo de log
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    carpeta = "logs"
    os.makedirs(carpeta, exist_ok=True)
    
    if tipo_proceso:
        nombre_archivo = f"{nombre_base}_{tipo_proceso.value.lower()}_{timestamp}.csv"
    else:
        nombre_archivo = f"{nombre_base}_{timestamp}.csv"
    
    return os.path.join(carpeta, nombre_archivo)


# Variables globales para mantener las rutas durante la ejecución
RUTA_LOG_REMESAS = obtener_ruta_log("log", TipoProceso.REMESA)
RUTA_LOG_MANIFIESTOS = obtener_ruta_log("log", TipoProceso.MANIFIESTO)
RUTA_LOG_ALERTAS = obtener_ruta_log("alertas")
RUTA_LOG_JSON = obtener_ruta_log("eventos").replace('.csv', '.json')


# ============================================================================
# FUNCIONES DE LOGGING CSV (Compatibilidad con código existente)
# ============================================================================
def registrar_log_remesa(codigo, mensaje, campos):
    """
    Registra un evento en el log CSV (función legacy para compatibilidad).
    
    Args:
        codigo: Código de la remesa/manifiesto
        mensaje: Mensaje descriptivo del evento
        campos: Lista de tuplas (id_campo, valor)
    """
    ruta = RUTA_LOG_REMESAS
    existe = os.path.exists(ruta)
    
    with open(ruta, mode='a', newline='', encoding='utf-8') as archivo:
        writer = csv.writer(archivo)
        
        if not existe:
            encabezado = ["Timestamp", "Codigo", "Mensaje"] + [id_suffix for id_suffix, _ in campos]
            writer.writerow(encabezado)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fila = [timestamp, codigo, mensaje] + [valor for _, valor in campos]
        writer.writerow(fila)


# ============================================================================
# SISTEMA DE LOGGING AVANZADO
# ============================================================================
class LoggerRNDC:
    """
    Sistema de logging avanzado con múltiples formatos y categorización.
    """
    
    def __init__(self, tipo_proceso):
        """
        Inicializa el logger para un tipo de proceso específico.
        
        Args:
            tipo_proceso: TipoProceso.REMESA o TipoProceso.MANIFIESTO
        """
        self.tipo_proceso = tipo_proceso
        self.ruta_csv = obtener_ruta_log("eventos", tipo_proceso)
        self.ruta_json = self.ruta_csv.replace('.csv', '.json')
        self.eventos = []
        self._inicializar_csv()
    
    def _inicializar_csv(self):
        """Crea el archivo CSV con encabezados si no existe."""
        if not os.path.exists(self.ruta_csv):
            with open(self.ruta_csv, mode='w', newline='', encoding='utf-8') as archivo:
                writer = csv.writer(archivo)
                writer.writerow([
                    "Timestamp",
                    "TipoProceso",
                    "TipoEvento",
                    "Codigo",
                    "Mensaje",
                    "CodigoError",
                    "Reintento",
                    "ValorFlete",
                    "CamposModificados",
                    "StackTrace"
                ])
    
    def registrar_evento(self, tipo_evento, codigo, mensaje, **kwargs):
        """
        Registra un evento completo con todos los detalles.
        
        Args:
            tipo_evento: TipoEvento (EXITO, ALERTA, ERROR, etc.)
            codigo: Código del documento procesado
            mensaje: Mensaje descriptivo
            **kwargs: Argumentos adicionales como:
                - codigo_error: Código específico del error (CRE064, CMA045, etc.)
                - reintento: Número de reintento
                - valor_flete: Valor del flete en caso de manifiestos
                - campos_modificados: Lista de campos modificados
                - excepcion: Excepción capturada
                - datos_adicionales: Diccionario con datos extra
        """
        timestamp = datetime.now()
        
        # Preparar datos del evento
        evento = {
            "timestamp": timestamp.isoformat(),
            "tipo_proceso": self.tipo_proceso.value,
            "tipo_evento": tipo_evento.value,
            "codigo": codigo,
            "mensaje": mensaje,
            "codigo_error": kwargs.get('codigo_error', ''),
            "reintento": kwargs.get('reintento', 0),
            "valor_flete": kwargs.get('valor_flete', 0),
            "campos_modificados": kwargs.get('campos_modificados', []),
            "datos_adicionales": kwargs.get('datos_adicionales', {}),
            "stack_trace": ""
        }
        
        # Capturar stack trace si hay excepción
        if 'excepcion' in kwargs:
            evento['stack_trace'] = ''.join(
                traceback.format_exception(
                    type(kwargs['excepcion']),
                    kwargs['excepcion'],
                    kwargs['excepcion'].__traceback__
                )
            )
        
        # Guardar evento en memoria
        self.eventos.append(evento)
        
        # Escribir en CSV
        self._escribir_csv(evento)
        
        # Escribir en JSON (acumulativo)
        self._escribir_json()
    
    def _escribir_csv(self, evento):
        """Escribe un evento en el archivo CSV."""
        with open(self.ruta_csv, mode='a', newline='', encoding='utf-8') as archivo:
            writer = csv.writer(archivo)
            writer.writerow([
                evento['timestamp'],
                evento['tipo_proceso'],
                evento['tipo_evento'],
                evento['codigo'],
                evento['mensaje'],
                evento['codigo_error'],
                evento['reintento'],
                evento['valor_flete'],
                json.dumps(evento['campos_modificados'], ensure_ascii=False),
                evento['stack_trace'][:500] if evento['stack_trace'] else ''  # Limitar tamaño
            ])
    
    def _escribir_json(self):
        """Escribe todos los eventos en formato JSON."""
        with open(self.ruta_json, mode='w', encoding='utf-8') as archivo:
            json.dump(self.eventos, archivo, indent=2, ensure_ascii=False)
    
    def registrar_exito(self, codigo, mensaje="Completado correctamente", **kwargs):
        """Registra un evento exitoso."""
        self.registrar_evento(TipoEvento.EXITO, codigo, mensaje, **kwargs)
    
    def registrar_alerta(self, codigo, codigo_alerta, mensaje, **kwargs):
        """Registra una alerta del sistema."""
        self.registrar_evento(
            TipoEvento.ALERTA,
            codigo,
            mensaje,
            codigo_error=codigo_alerta,
            **kwargs
        )
    
    def registrar_error(self, codigo, mensaje, **kwargs):
        """Registra un error."""
        self.registrar_evento(TipoEvento.ERROR, codigo, mensaje, **kwargs)
    
    def registrar_reintento(self, codigo, numero_reintento, mensaje, **kwargs):
        """Registra un intento de reintento."""
        self.registrar_evento(
            TipoEvento.REINTENTO,
            codigo,
            mensaje,
            reintento=numero_reintento,
            **kwargs
        )
    
    def registrar_excepcion(self, codigo, excepcion, mensaje="Excepción capturada", **kwargs):
        """Registra una excepción con stack trace completo."""
        self.registrar_evento(
            TipoEvento.EXCEPCION,
            codigo,
            f"{mensaje}: {str(excepcion)}",
            excepcion=excepcion,
            **kwargs
        )
    
    def obtener_estadisticas(self):
        """
        Genera estadísticas de los eventos registrados.
        
        Returns:
            dict: Estadísticas por tipo de evento
        """
        stats = {
            "total_eventos": len(self.eventos),
            "por_tipo": {},
            "codigos_error": {},
            "exitosos": 0,
            "fallidos": 0
        }
        
        for evento in self.eventos:
            tipo = evento['tipo_evento']
            stats['por_tipo'][tipo] = stats['por_tipo'].get(tipo, 0) + 1
            
            if tipo == "EXITO":
                stats['exitosos'] += 1
            elif tipo in ["ERROR", "EXCEPCION"]:
                stats['fallidos'] += 1
            
            if evento['codigo_error']:
                codigo_error = evento['codigo_error']
                stats['codigos_error'][codigo_error] = stats['codigos_error'].get(codigo_error, 0) + 1
        
        return stats
    
    def generar_reporte(self):
        """
        Genera un reporte legible de las estadísticas.
        
        Returns:
            str: Reporte formateado
        """
        stats = self.obtener_estadisticas()
        
        reporte = f"""
═══════════════════════════════════════════════════════════
 REPORTE DE PROCESAMIENTO - {self.tipo_proceso.value}
═══════════════════════════════════════════════════════════

📊 RESUMEN GENERAL
   Total de eventos: {stats['total_eventos']}
   ✅ Exitosos: {stats['exitosos']}
   ❌ Fallidos: {stats['fallidos']}

📋 EVENTOS POR TIPO
"""
        for tipo, cantidad in stats['por_tipo'].items():
            reporte += f"   {tipo}: {cantidad}\n"
        
        if stats['codigos_error']:
            reporte += "\n🚨 CÓDIGOS DE ERROR MÁS COMUNES\n"
            for codigo, cantidad in sorted(stats['codigos_error'].items(), key=lambda x: x[1], reverse=True):
                reporte += f"   {codigo}: {cantidad} ocurrencias\n"
        
        reporte += f"""
═══════════════════════════════════════════════════════════
Logs guardados en:
  📄 CSV: {self.ruta_csv}
  📄 JSON: {self.ruta_json}
═══════════════════════════════════════════════════════════
"""
        return reporte


# ============================================================================
# INSTANCIAS GLOBALES
# ============================================================================
logger_remesas = LoggerRNDC(TipoProceso.REMESA)
logger_manifiestos = LoggerRNDC(TipoProceso.MANIFIESTO)


# ============================================================================
# FUNCIONES DE CONVENIENCIA
# ============================================================================
def obtener_logger(tipo_proceso):
    """
    Obtiene el logger correspondiente al tipo de proceso.
    
    Args:
        tipo_proceso: TipoProceso.REMESA o TipoProceso.MANIFIESTO
    
    Returns:
        LoggerRNDC: Logger correspondiente
    """
    if tipo_proceso == TipoProceso.REMESA:
        return logger_remesas
    elif tipo_proceso == TipoProceso.MANIFIESTO:
        return logger_manifiestos
    else:
        raise ValueError(f"Tipo de proceso desconocido: {tipo_proceso}")