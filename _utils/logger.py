# utils/logger.py
import csv
import os
from datetime import datetime

# Generar ruta con nombre dinámico por fecha-hora
def obtener_ruta_log(nombre_base="log_"):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    carpeta = "logs"
    os.makedirs(carpeta, exist_ok=True)
    return os.path.join(carpeta, f"{nombre_base}_{timestamp}.csv")

# Variable global para mantener la misma ruta en toda la ejecución
RUTA_LOG_REMESAS = obtener_ruta_log()

def registrar_log_remesa(codigo, mensaje, campos):
    ruta = RUTA_LOG_REMESAS
    existe = os.path.exists(ruta)

    with open(ruta, mode='a', newline='', encoding='utf-8') as archivo:
        writer = csv.writer(archivo)
        if not existe:
            encabezado = ["Codigo", "Mensaje"] + [id_suffix for id_suffix, _ in campos]
            writer.writerow(encabezado)

        fila = [codigo, mensaje] + [valor for _, valor in campos]
        writer.writerow(fila)
