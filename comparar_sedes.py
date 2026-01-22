"""
Script auxiliar para comparar sedes del Excel original
con las sedes disponibles extraídas.

Genera sugerencias de corrección automática.

Uso: python comparar_sedes.py
"""

import pandas as pd
import unicodedata
from tkinter import Tk, filedialog


def normalizar_texto(texto):
    """Normaliza texto removiendo tildes y caracteres especiales."""
    texto = texto.upper()
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    texto = ' '.join(texto.replace('-', ' ').replace('.', ' ').split())
    return texto


def buscar_mejor_coincidencia(sede_buscada, sedes_disponibles):
    """
    Busca la mejor coincidencia para una sede en la lista disponible.
    
    Args:
        sede_buscada: Nombre de la sede a buscar
        sedes_disponibles: Lista de nombres de sedes disponibles
    
    Returns:
        tuple: (mejor_coincidencia, score, tipo_match)
    """
    sede_norm = normalizar_texto(sede_buscada)
    palabras_busqueda = sede_norm.split()
    
    mejores = []
    
    for sede_disp in sedes_disponibles:
        sede_disp_norm = normalizar_texto(sede_disp)
        
        # Coincidencia exacta
        if sede_norm == sede_disp_norm:
            return sede_disp, 1.0, "EXACTA"
        
        # Contención
        if sede_norm in sede_disp_norm:
            score = len(sede_norm) / len(sede_disp_norm)
            mejores.append((sede_disp, score, "CONTIENE"))
        elif sede_disp_norm in sede_norm:
            score = len(sede_disp_norm) / len(sede_norm)
            mejores.append((sede_disp, score, "CONTENIDO"))
        
        # Palabras
        else:
            palabras_disp = sede_disp_norm.split()
            palabras_encontradas = sum(1 for p in palabras_busqueda if p in palabras_disp)
            
            if palabras_encontradas == len(palabras_busqueda):
                score = palabras_encontradas / len(palabras_disp)
                mejores.append((sede_disp, score, "PALABRAS"))
    
    if mejores:
        mejores.sort(key=lambda x: x[1], reverse=True)
        return mejores[0]
    
    return None, 0.0, "NO_ENCONTRADA"


def comparar_archivos(archivo_original, archivo_sedes):
    """
    Compara el Excel original con el de sedes disponibles.
    
    Returns:
        DataFrame con sugerencias de corrección
    """
    print("📂 Leyendo archivos...")
    
    # Leer archivo original
    df_original = pd.read_excel(archivo_original)
    
    # Validar columnas
    if 'NUMIDPROPIETARIO' not in df_original.columns or 'REM_ORIG' not in df_original.columns:
        raise ValueError("Archivo original debe tener columnas NUMIDPROPIETARIO y REM_ORIG")
    
    # Leer archivo de sedes disponibles
    df_sedes = pd.read_excel(archivo_sedes)
    
    print("✅ Archivos cargados")
    print(f"   Registros originales: {len(df_original)}")
    print(f"   Sedes disponibles: {len(df_sedes)}")
    print()
    
    # Crear diccionario de sedes por NIT
    sedes_por_nit = {}
    for _, row in df_sedes.iterrows():
        nit = str(int(row['NIT']))
        if nit not in sedes_por_nit:
            sedes_por_nit[nit] = []
        sedes_por_nit[nit].append(row['NOMBRE_SEDE'])
    
    # Analizar cada fila del original
    print("🔍 Analizando coincidencias...")
    resultados = []
    
    for idx, row in df_original.iterrows():
        nit = str(int(row['NUMIDPROPIETARIO']))
        sede_original = str(row['REM_ORIG']).strip()
        fila_excel = idx + 2  # +2 por header y porque Excel empieza en 1
        
        # Verificar si el NIT tiene sedes disponibles
        if nit not in sedes_por_nit:
            resultados.append({
                'FILA': fila_excel,
                'NIT': nit,
                'SEDE_ORIGINAL': sede_original,
                'SEDE_SUGERIDA': 'NIT NO ENCONTRADO',
                'SCORE': 0.0,
                'TIPO': 'ERROR',
                'ESTADO': '❌ NIT sin sedes disponibles'
            })
            continue
        
        # Buscar mejor coincidencia
        mejor, score, tipo = buscar_mejor_coincidencia(sede_original, sedes_por_nit[nit])
        
        if tipo == "EXACTA":
            estado = "✅ CORRECTO"
        elif tipo == "NO_ENCONTRADA":
            estado = "❌ NO ENCONTRADA"
        elif score >= 0.7:
            estado = "⚠️ SUGERENCIA (Alta confianza)"
        else:
            estado = "⚠️ SUGERENCIA (Baja confianza)"
        
        resultados.append({
            'FILA': fila_excel,
            'NIT': nit,
            'SEDE_ORIGINAL': sede_original,
            'SEDE_SUGERIDA': mejor if mejor else 'NO HAY COINCIDENCIA',
            'SCORE': round(score, 2),
            'TIPO': tipo,
            'ESTADO': estado
        })
    
    df_resultados = pd.DataFrame(resultados)
    
    return df_resultados


def main():
    """Función principal."""
    print("=" * 70)
    print("🔄 COMPARADOR DE SEDES - SUGERENCIAS DE CORRECCIÓN")
    print("=" * 70)
    print()
    
    root = Tk()
    root.withdraw()
    
    # 1. Seleccionar archivo original
    print("📂 Paso 1: Seleccione su archivo Excel ORIGINAL...")
    archivo_original = filedialog.askopenfilename(
        title="Seleccionar Excel Original (con NUMIDPROPIETARIO y REM_ORIG)",
        filetypes=[("Archivos Excel", "*.xlsx"), ("Archivos Excel", "*.xls")]
    )
    
    if not archivo_original:
        print("❌ No se seleccionó archivo original")
        return
    
    print(f"✅ Original: {archivo_original}")
    print()
    
    # 2. Seleccionar archivo de sedes disponibles
    print("📂 Paso 2: Seleccione el archivo de SEDES DISPONIBLES...")
    print("   (El que generó con extraer_sedes_por_nit.py)")
    archivo_sedes = filedialog.askopenfilename(
        title="Seleccionar Excel de Sedes Disponibles",
        filetypes=[("Archivos Excel", "*.xlsx"), ("Archivos Excel", "*.xls")]
    )
    
    if not archivo_sedes:
        print("❌ No se seleccionó archivo de sedes")
        return
    
    print(f"✅ Sedes: {archivo_sedes}")
    print()
    
    try:
        # 3. Comparar
        df_sugerencias = comparar_archivos(archivo_original, archivo_sedes)
        
        # 4. Generar archivo de salida
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo_salida = f"sugerencias_correccion_{timestamp}.xlsx"
        
        df_sugerencias.to_excel(archivo_salida, index=False, sheet_name='Sugerencias')
        
        # 5. Mostrar resumen
        print("\n" + "=" * 70)
        print("📊 RESUMEN DE ANÁLISIS")
        print("=" * 70)
        
        total = len(df_sugerencias)
        correctos = len(df_sugerencias[df_sugerencias['TIPO'] == 'EXACTA'])
        no_encontrados = len(df_sugerencias[df_sugerencias['TIPO'] == 'NO_ENCONTRADA'])
        con_sugerencia = total - correctos - no_encontrados
        
        print(f"\nTotal de registros: {total}")
        print(f"✅ Correctos (no requieren cambio): {correctos}")
        print(f"⚠️  Con sugerencia de corrección: {con_sugerencia}")
        print(f"❌ Sin coincidencia encontrada: {no_encontrados}")
        print()
        
        # Mostrar algunos ejemplos de correcciones
        if con_sugerencia > 0:
            print("🔧 EJEMPLOS DE CORRECCIONES SUGERIDAS:")
            print("-" * 70)
            sugerencias = df_sugerencias[df_sugerencias['TIPO'].isin(['CONTIENE', 'CONTENIDO', 'PALABRAS'])].head(10)
            for _, row in sugerencias.iterrows():
                print(f"Fila {row['FILA']}:")
                print(f"  Original:  {row['SEDE_ORIGINAL']}")
                print(f"  Sugerida:  {row['SEDE_SUGERIDA']} (score: {row['SCORE']})")
                print()
        
        print("=" * 70)
        print(f"✅ Archivo de sugerencias generado: {archivo_salida}")
        print()
        print("💡 PRÓXIMOS PASOS:")
        print("   1. Abre el archivo de sugerencias")
        print("   2. Revisa las columnas SEDE_ORIGINAL y SEDE_SUGERIDA")
        print("   3. Actualiza tu Excel original con las correcciones")
        print("   4. Vuelve a ejecutar el cambio de sede")
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
    
    input("\nPresiona ENTER para salir...")


if __name__ == "__main__":
    main()