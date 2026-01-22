"""
Script para extraer todas las sedes disponibles por NIT desde RNDC.
Genera un Excel con el listado completo para verificar y corregir sedes.

Uso: python extraer_sedes_por_nit.py
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import pandas as pd
import time
from datetime import datetime
from _core.navegador import crear_driver
from _core.common import hacer_login


# ============================================================================
# CONSTANTES
# ============================================================================
URL_CAMBIO_SEDE = "https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CambioMasivoRemesas/mid/396/procesoid/4/default.aspx"


def extraer_nits_unicos(ruta_excel):
    """
    Extrae todos los NITs únicos del Excel.
    
    Args:
        ruta_excel: Ruta del archivo Excel
    
    Returns:
        list: Lista de NITs únicos (como strings)
    """
    print("📂 Leyendo archivo Excel...")
    df = pd.read_excel(ruta_excel)
    
    if 'NUMIDPROPIETARIO' not in df.columns:
        raise ValueError("Columna 'NUMIDPROPIETARIO' no encontrada en el Excel")
    
    nits_unicos = df['NUMIDPROPIETARIO'].dropna().unique()
    nits_unicos = [str(int(nit)) for nit in nits_unicos]
    
    print(f"✅ Se encontraron {len(nits_unicos)} NITs únicos")
    for nit in nits_unicos:
        print(f"   • {nit}")
    
    return nits_unicos


def extraer_sedes_para_nit(driver, nit):
    """
    Extrae todas las sedes disponibles para un NIT específico.
    
    Args:
        driver: WebDriver de Selenium
        nit: NIT a consultar
    
    Returns:
        list: Lista de diccionarios con {codigo, nombre} de cada sede
    """
    try:
        print(f"\n🔍 Consultando sedes para NIT: {nit}")
        
        # Navegar al formulario
        driver.get(URL_CAMBIO_SEDE)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "dnn_ctr396_CambioMasivoRemesas_TIPOIDPROPIETARIO_ANT"))
        )
        
        # Seleccionar tipo NIT
        select_tipo = Select(driver.find_element(By.ID, "dnn_ctr396_CambioMasivoRemesas_TIPOIDPROPIETARIO_ANT"))
        select_tipo.select_by_value("N")
        driver.find_element(By.ID, "dnn_ctr396_CambioMasivoRemesas_TIPOIDPROPIETARIO_ANT").send_keys(Keys.TAB)
        time.sleep(0.5)
        
        # Ingresar NIT
        input_nit = driver.find_element(By.ID, "dnn_ctr396_CambioMasivoRemesas_NUMIDPROPIETARIO_ANT")
        input_nit.clear()
        input_nit.send_keys(nit)
        input_nit.send_keys(Keys.TAB)
        
        # Esperar a que carguen las sedes
        time.sleep(4)
        
        # Extraer todas las opciones del select
        select_sedes = driver.find_element(By.ID, "dnn_ctr396_CambioMasivoRemesas_SEDEPROPIETARIO_ANT")
        opciones = select_sedes.find_elements(By.TAG_NAME, "option")
        
        sedes = []
        for opcion in opciones:
            codigo = opcion.get_attribute('value')
            nombre = opcion.text.strip()
            
            # Saltar opción por defecto (vacía o "Seleccione...")
            if codigo and codigo != '0' and nombre:
                sedes.append({
                    'codigo': codigo,
                    'nombre': nombre
                })
        
        print(f"   ✅ Se encontraron {len(sedes)} sedes disponibles")
        
        return sedes
    
    except Exception as e:
        print(f"   ❌ Error consultando NIT {nit}: {str(e)}")
        return []


def generar_excel_sedes(nits_con_sedes, archivo_salida):
    """
    Genera un Excel con todas las sedes disponibles por NIT.
    
    Args:
        nits_con_sedes: Diccionario {nit: [lista_sedes]}
        archivo_salida: Nombre del archivo Excel de salida
    """
    print(f"\n📊 Generando Excel de sedes...")
    
    # Crear lista de filas
    filas = []
    for nit, sedes in nits_con_sedes.items():
        for sede in sedes:
            filas.append({
                'NIT': nit,
                'CODIGO_SEDE': sede['codigo'],
                'NOMBRE_SEDE': sede['nombre']
            })
    
    # Crear DataFrame
    df = pd.DataFrame(filas)
    
    # Guardar a Excel
    df.to_excel(archivo_salida, index=False, sheet_name='Sedes por NIT')
    
    print(f"✅ Excel generado: {archivo_salida}")
    print(f"   Total de registros: {len(filas)}")


def main():
    """Función principal."""
    print("=" * 70)
    print("🏢 EXTRACTOR DE SEDES DISPONIBLES POR NIT")
    print("=" * 70)
    print()
    
    # 1. Pedir archivo de entrada
    from tkinter import Tk, filedialog
    root = Tk()
    root.withdraw()
    
    print("📂 Seleccione el archivo Excel con los NITs...")
    archivo_entrada = filedialog.askopenfilename(
        title="Seleccionar archivo Excel",
        filetypes=[("Archivos Excel", "*.xlsx"), ("Archivos Excel", "*.xls")]
    )
    
    if not archivo_entrada:
        print("❌ No se seleccionó ningún archivo")
        return
    
    print(f"✅ Archivo seleccionado: {archivo_entrada}")
    print()
    
    try:
        # 2. Extraer NITs únicos
        nits = extraer_nits_unicos(archivo_entrada)
        
        # 3. Crear driver y hacer login
        print("\n🌐 Iniciando navegador...")
        driver = crear_driver()
        
        print("🔐 Iniciando sesión en RNDC...")
        hacer_login(driver)
        
        # 4. Consultar sedes para cada NIT
        nits_con_sedes = {}
        
        for idx, nit in enumerate(nits, 1):
            print(f"\n[{idx}/{len(nits)}] Procesando NIT: {nit}")
            sedes = extraer_sedes_para_nit(driver, nit)
            nits_con_sedes[nit] = sedes
            
            # Pequeña pausa entre consultas
            time.sleep(2)
        
        # 5. Generar archivo de salida
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo_salida = f"sedes_disponibles_{timestamp}.xlsx"
        
        generar_excel_sedes(nits_con_sedes, archivo_salida)
        
        # 6. Generar reporte de resumen
        print("\n" + "=" * 70)
        print("📋 RESUMEN")
        print("=" * 70)
        for nit, sedes in nits_con_sedes.items():
            print(f"NIT {nit}: {len(sedes)} sedes disponibles")
        print()
        print(f"✅ Proceso completado exitosamente")
        print(f"📄 Archivo generado: {archivo_salida}")
        print()
        print("💡 PRÓXIMOS PASOS:")
        print("   1. Abre el archivo generado")
        print("   2. Busca los NITs de tu archivo original")
        print("   3. Compara las sedes disponibles con las que tienes en tu Excel")
        print("   4. Corrige los nombres de las sedes en tu archivo original")
        print()
        
    except Exception as e:
        print(f"\n❌ Error general: {str(e)}")
    
    finally:
        # Cerrar navegador
        try:
            driver.quit()
        except:
            pass
        
        input("\nPresiona ENTER para salir...")


if __name__ == "__main__":
    main()