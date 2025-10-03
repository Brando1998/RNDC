#!/usr/bin/env python3
"""
Script para analizar logs JSON y generar reportes detallados.
Identifica patrones, errores frecuentes y sugiere mejoras.
"""

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime


def cargar_log(ruta_archivo):
    """Carga el archivo JSON del log."""
    with open(ruta_archivo, 'r', encoding='utf-8') as f:
        return json.load(f)


def analizar_errores(eventos):
    """Analiza todos los errores y genera estadísticas."""
    errores_por_tipo = defaultdict(list)
    codigos_con_errores = defaultdict(int)
    errores_por_hora = defaultdict(int)
    
    for evento in eventos:
        tipo = evento['tipo_evento']
        codigo = evento['codigo']
        timestamp = datetime.fromisoformat(evento['timestamp'])
        hora = timestamp.hour
        
        if tipo in ['ERROR', 'EXCEPCION', 'ALERTA']:
            errores_por_tipo[tipo].append(evento)
            codigos_con_errores[codigo] += 1
            errores_por_hora[hora] += 1
    
    return {
        'errores_por_tipo': errores_por_tipo,
        'codigos_con_errores': codigos_con_errores,
        'errores_por_hora': errores_por_hora
    }


def analizar_codigos_error(eventos):
    """Identifica los códigos de error más comunes."""
    codigos_error = []
    
    for evento in eventos:
        if evento['tipo_evento'] in ['ERROR', 'ALERTA']:
            mensaje = evento['mensaje']
            # Extraer códigos de error del mensaje
            if 'CRE' in mensaje or 'CMA' in mensaje:
                palabras = mensaje.split()
                for palabra in palabras:
                    if palabra.startswith('CRE') or palabra.startswith('CMA'):
                        codigo = palabra.rstrip(':,.;')
                        codigos_error.append(codigo)
    
    return Counter(codigos_error)


def analizar_stack_traces(eventos):
    """Analiza los stack traces para encontrar excepciones comunes."""
    excepciones = []
    
    for evento in eventos:
        if evento['tipo_evento'] == 'EXCEPCION' and evento['stack_trace']:
            # Extraer tipo de excepción
            lineas = evento['stack_trace'].split('\n')
            for linea in lineas:
                if 'Error:' in linea or 'Exception:' in linea:
                    excepciones.append(linea.strip())
    
    return Counter(excepciones)


def analizar_reintentos(eventos):
    """Analiza patrones de reintentos."""
    reintentos_por_codigo = defaultdict(list)
    
    for evento in eventos:
        if evento['tipo_evento'] == 'REINTENTO':
            codigo = evento['codigo']
            reintento = evento['reintento']
            reintentos_por_codigo[codigo].append(reintento)
    
    # Calcular estadísticas
    stats = {}
    for codigo, lista_reintentos in reintentos_por_codigo.items():
        stats[codigo] = {
            'total_reintentos': len(lista_reintentos),
            'max_reintento': max(lista_reintentos) if lista_reintentos else 0
        }
    
    return stats


def calcular_tasa_exito(eventos):
    """Calcula la tasa de éxito del proceso."""
    total = 0
    exitosos = 0
    fallidos = 0
    
    # Agrupar por código para contar cada remesa/manifiesto una sola vez
    eventos_por_codigo = defaultdict(list)
    for evento in eventos:
        codigo = evento['codigo']
        eventos_por_codigo[codigo].append(evento['tipo_evento'])
    
    for codigo, tipos in eventos_por_codigo.items():
        total += 1
        if 'EXITO' in tipos:
            exitosos += 1
        elif 'ERROR' in tipos or 'EXCEPCION' in tipos:
            fallidos += 1
    
    tasa_exito = (exitosos / total * 100) if total > 0 else 0
    
    return {
        'total': total,
        'exitosos': exitosos,
        'fallidos': fallidos,
        'tasa_exito': tasa_exito
    }


def generar_reporte(eventos, nombre_archivo):
    """Genera un reporte completo del análisis."""
    print("=" * 80)
    print(f"REPORTE DE ANÁLISIS - {nombre_archivo}")
    print("=" * 80)
    print()
    
    # 1. Estadísticas generales
    print("📊 ESTADÍSTICAS GENERALES")
    print("-" * 80)
    stats_exito = calcular_tasa_exito(eventos)
    print(f"Total de documentos procesados: {stats_exito['total']}")
    print(f"✅ Exitosos: {stats_exito['exitosos']}")
    print(f"❌ Fallidos: {stats_exito['fallidos']}")
    print(f"📈 Tasa de éxito: {stats_exito['tasa_exito']:.1f}%")
    print()
    
    # 2. Códigos de error más comunes
    print("🚨 CÓDIGOS DE ERROR MÁS COMUNES")
    print("-" * 80)
    codigos_error = analizar_codigos_error(eventos)
    for codigo, cantidad in codigos_error.most_common(10):
        print(f"   {codigo}: {cantidad} ocurrencias")
    print()
    
    # 3. Análisis de errores
    print("🔍 ANÁLISIS DE ERRORES")
    print("-" * 80)
    analisis = analizar_errores(eventos)
    for tipo, lista in analisis['errores_por_tipo'].items():
        print(f"   {tipo}: {len(lista)} eventos")
    print()
    
    # 4. Documentos con más errores
    print("📋 DOCUMENTOS CON MÁS PROBLEMAS")
    print("-" * 80)
    codigos_problematicos = analisis['codigos_con_errores'].most_common(10)
    for codigo, cantidad in codigos_problematicos:
        print(f"   {codigo}: {cantidad} errores")
    print()
    
    # 5. Excepciones comunes
    print("💥 EXCEPCIONES MÁS COMUNES")
    print("-" * 80)
    excepciones = analizar_stack_traces(eventos)
    for excepcion, cantidad in excepciones.most_common(5):
        print(f"   [{cantidad}x] {excepcion}")
    print()
    
    # 6. Análisis de reintentos
    print("🔄 ANÁLISIS DE REINTENTOS")
    print("-" * 80)
    reintentos = analizar_reintentos(eventos)
    if reintentos:
        total_con_reintentos = len(reintentos)
        max_reintentos = max([r['max_reintento'] for r in reintentos.values()])
        print(f"   Documentos que requirieron reintentos: {total_con_reintentos}")
        print(f"   Máximo de reintentos en un documento: {max_reintentos}")
    else:
        print("   No se registraron reintentos")
    print()
    
    # 7. Patrones temporales
    print("⏰ PATRONES TEMPORALES")
    print("-" * 80)
    errores_por_hora = analisis['errores_por_hora']
    if errores_por_hora:
        hora_pico = max(errores_por_hora.items(), key=lambda x: x[1])
        print(f"   Hora con más errores: {hora_pico[0]:02d}:00 ({hora_pico[1]} errores)")
    print()
    
    # 8. Recomendaciones
    print("💡 RECOMENDACIONES")
    print("-" * 80)
    
    # Analizar qué errores necesitan nuevos manejadores
    codigos_sin_manejar = []
    for codigo, _ in codigos_error.most_common():
        if codigo not in ['CRE064', 'CRE230', 'CRE250', 'CRE270', 'CRE308', 'CRE309', 'CRE141']:
            codigos_sin_manejar.append(codigo)
    
    if codigos_sin_manejar[:5]:
        print("   Agregar manejadores para estos códigos de error:")
        for codigo in codigos_sin_manejar[:5]:
            print(f"      - {codigo}")
    
    if stats_exito['tasa_exito'] < 70:
        print("   ⚠️  La tasa de éxito es baja. Priorizar:")
        print("      1. Revisar validaciones de datos de entrada")
        print("      2. Mejorar manejo de errores más comunes")
    
    print()
    print("=" * 80)


def main():
    if len(sys.argv) < 2:
        print("Uso: python analizar_logs.py <ruta_archivo_json>")
        print()
        print("Ejemplo:")
        print("  python analizar_logs.py logs/eventos_remesa_2025-01-15_14-30-45.json")
        sys.exit(1)
    
    ruta_archivo = sys.argv[1]
    
    try:
        eventos = cargar_log(ruta_archivo)
        generar_reporte(eventos, ruta_archivo)
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo '{ruta_archivo}'")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ Error: El archivo '{ruta_archivo}' no es un JSON válido")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()