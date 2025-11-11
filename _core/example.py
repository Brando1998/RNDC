import pandas as pd
from tkinter import Tk, filedialog, Button, Label, Frame
import os
import platform
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException


codigos_remesas = []
codigos_manifiestos = []

def crear_driver():
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)
    if platform.system() == "Windows":
        driver_path = os.path.join(".", "drivers", "chromedriver.exe")
    else:
        driver_path = os.path.join(".", "drivers", "chromedriver")
    service = Service(driver_path)
    return webdriver.Chrome(service=service, options=chrome_options)

# ----------------- PROCESO REMESAS -----------------
def seleccionar_txt_remesas():
    global codigos_remesas
    boton_remesas_cargar["state"] = "disabled"
    boton_remesas_ejecutar["state"] = "disabled"
    etiqueta_cargando_remesas.config(text="⏳ Cargando archivo...")
    ventana.update()

    try:
        archivo = filedialog.askopenfilename(filetypes=[("Archivos TXT", "*.txt")])
        if archivo:
            df = pd.read_csv(archivo, sep="\t", header=None, encoding='latin1', dtype={9: str})
            codigos_remesas = df.iloc[:, 9].dropna().astype(str).tolist()
            etiqueta_archivo_remesas.config(text=os.path.basename(archivo))
            etiqueta_estado_remesas.config(text=f"✅ Se cargaron {len(codigos_remesas)} remesas.")
            boton_remesas_ejecutar["state"] = "normal"
        else:
            etiqueta_estado_remesas.config(text="⚠ No se seleccionó archivo.")

    except Exception as e:
        etiqueta_estado_remesas.config(text=f"❌ Error: {e}")

    boton_remesas_cargar["state"] = "normal"
    etiqueta_cargando_remesas.config(text="")
    ventana.update()


def ejecutar_remesas():
    global codigos_remesas
    boton_remesas_cargar["state"] = "disabled"
    boton_remesas_ejecutar["state"] = "disabled"
    etiqueta_cargando_remesas.config(text="⚙️ Procesando remesas...")
    ventana.update()

    try:
        driver = crear_driver()
        driver.get("https://rndc.mintransporte.gov.co/MenuPrincipal/tabid/204/language/es-MX/Default.aspx?returnurl=%2fMenuPrincipal%2ftabid%2f204%2flanguage%2fes-MX%2fDefault.aspx")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "dnn_ctr580_FormLogIn_edUsername"))
        )
        usuario = "Sotranscolombianos1@0341"
        contrasena = "053EPA746**"
        driver.find_element(By.ID, "dnn_ctr580_FormLogIn_edUsername").send_keys(usuario)
        driver.find_element(By.ID, "dnn_ctr580_FormLogIn_edPassword").send_keys(contrasena)
        driver.find_element(By.ID, "dnn_ctr580_FormLogIn_btIngresar").click()
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "tddnn_dnnSOLPARTMENU_ctldnnSOLPARTMENU120"))
        )

        driver.get("https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CumplirRemesa/mid/396/procesoid/5/default.aspx")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesa_CONSECUTIVOREMESA"))
        )

        for codigo in codigos_remesas:
            print(f"Procesando remesa: {codigo}")
            driver.get("https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CumplirRemesa/mid/396/procesoid/5/default.aspx")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesa_CONSECUTIVOREMESA"))
            )
            try:
                print("Primer try")
                # Ingresar número de remesa              
                input_remesa = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_CONSECUTIVOREMESA")
                input_remesa.clear()
                input_remesa.send_keys(codigo)
                input_remesa.send_keys("\t")
                time.sleep(1)
                print("llenado okey")
                # Seleccionar opción "Cumplido Normal"
                select_cumplido = Select(driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_NOMTIPOCUMPLIDOREMESA"))
                select_cumplido.select_by_visible_text("Cumplido Normal")
                print("Seleccionado normal")
                # Copiar valor de CANTIDADINFORMACIONCARGA a CANTIDADENTREGADA
                cantidad_informacion = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_CANTIDADCARGADA").get_attribute("value")
                input_cantidad_entregada = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_CANTIDADENTREGADA")
                input_cantidad_entregada.clear()
                input_cantidad_entregada.send_keys(cantidad_informacion)
                print("Seleccionda carga")
                # Guardar la primera fecha y hora pactada de cargue
                fecha_cargue = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHACITAPACTADACARGUE").get_attribute("value")
                hora_cargue = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORACITAPACTADACARGUE").get_attribute("value")
                hora_salida = (datetime.strptime(hora_cargue, "%H:%M") + timedelta(minutes=59)).strftime("%H:%M")
                print("Seleccioda fecha y hora pactada cargue")
                # Guardar la segunda fecha y segunda hora pactadas de descargue
                fecha_descargue = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHACITAPACTADADESCARGUE").get_attribute("value")
                hora_descargue = driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORACITAPACTADADESCARGUEREMESA").get_attribute("value")
                hora_llegada = (datetime.strptime(hora_descargue, "%H:%M") + timedelta(minutes=59)).strftime("%H:%M")
                print("Seleccioda fecha y hora pactada descargue")
                # Limpiar y colocar la primera fecha en los 3 campos de cargue
                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHALLEGADACARGUE").clear()
                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHALLEGADACARGUE").send_keys(fecha_cargue)

                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHAENTRADACARGUE").clear()
                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHAENTRADACARGUE").send_keys(fecha_cargue)

                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHASALIDACARGUE").clear()
                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHASALIDACARGUE").send_keys(fecha_cargue)

                print("Selecciodos 3 campos")

                # Limpiar y colocar horas de cargue
                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORALLEGADACARGUEREMESA").clear()
                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORALLEGADACARGUEREMESA").send_keys(hora_cargue)

                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORAENTRADACARGUEREMESA").clear()
                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORAENTRADACARGUEREMESA").send_keys(hora_cargue)

                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORASALIDACARGUEREMESA").clear()
                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORASALIDACARGUEREMESA").send_keys(hora_salida)

                print("Seleccioda limpiar 1")
                # Limpiar y colocar fechas de descargue
                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHALLEGADADESCARGUE").clear()
                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHALLEGADADESCARGUE").send_keys(fecha_descargue)

                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHAENTRADADESCARGUE").clear()
                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHAENTRADADESCARGUE").send_keys(fecha_descargue)

                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHASALIDADESCARGUE").clear()
                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_FECHASALIDADESCARGUE").send_keys(fecha_descargue)
                print("Seleccioda limpiar 2")
                # Limpiar y colocar horas de descargue
                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORALLEGADADESCARGUECUMPLIDO").clear()
                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORALLEGADADESCARGUECUMPLIDO").send_keys(hora_cargue)

                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORAENTRADADESCARGUECUMPLIDO").clear()
                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORAENTRADADESCARGUECUMPLIDO").send_keys(hora_cargue)

                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORASALIDADESCARGUECUMPLIDO").clear()
                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_HORASALIDADESCARGUECUMPLIDO").send_keys(hora_salida)
                print("Seleccioda limpiar 3")

                # Guardar
                driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_btGuardar").click()

                # Esperar un instante para ver si hay alerta
                time.sleep(1)
                try:
                    WebDriverWait(driver, 3).until(EC.alert_is_present())
                    alerta = driver.switch_to.alert
                    texto_alerta = alerta.text
                    alerta.accept()
                    print(f"Alerta detectada: {texto_alerta}")

                    if "CRE250" in texto_alerta:
                        # ... aquí pones tu lógica de fecha nueva como ya la tienes ...
                        pass
                    elif "CRE064" in texto_alerta:
                        print(f"✅ Remesa {codigo} ya había sido completada anteriormente.")
                    else:
                        print(f"❌ Remesa {codigo} falló por otra alerta: {texto_alerta}")

                except TimeoutException:
                    # No hubo alerta, todo está bien, continuar
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesaNew_btNuevo"))
                    )
                    
                    print(f"✅ Remesa {codigo} completada correctamente.")
                    pass

                # Ahora sí puedes esperar la nueva página tranquilamente

                driver.get("https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CumplirRemesa/mid/396/procesoid/5/default.aspx")
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesa_CONSECUTIVOREMESA"))
                )

            except UnexpectedAlertPresentException:
                alerta = driver.switch_to.alert
                texto_alerta = alerta.text
                alerta.accept()
                print("Exception")
                if "CRE250" in texto_alerta:
                    print("if 1")
                    print(f"⚠ Remesa {codigo} con error de fechas, intentando con +5 días en descargue...")

                    fecha_descargue_nueva = (datetime.strptime(fecha_descargue, "%d/%m/%Y") + timedelta(days=5)).strftime("%d/%m/%Y")

                    for campo_id in [
                        "dnn_ctr396_CumplirRemesa_FECHALLEGADADESCARGUE",
                        "dnn_ctr396_CumplirRemesa_FECHAENTRADADESCARGUE",
                        "dnn_ctr396_CumplirRemesa_FECHASALIDADESCARGUE",
                    ]:
                        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, campo_id)))
                        driver.find_element(By.ID, campo_id).clear()
                        driver.find_element(By.ID, campo_id).send_keys(fecha_descargue_nueva)

                    # 🔴 Debes volver a dar clic en guardar después de corregir
                    driver.find_element(By.ID, "dnn_ctr396_CumplirRemesa_btGuardar").click()

                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesaNew_btNuevo"))
                    )

                    driver.get("https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CumplirRemesa/mid/396/procesoid/5/default.aspx")
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesa_CONSECUTIVOREMESA"))
                    )
                    print(f"✅ Remesa {codigo} completada correctamente tras corrección de fechas.")

                elif "CRE064" in texto_alerta:
                    print(f"✅ Remesa {codigo} ya había sido completada anteriormente.")
                    driver.get("https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CumplirRemesa/mid/396/procesoid/5/default.aspx")
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesa_CONSECUTIVOREMESA"))
                    )
                else:
                    print(f"❌ Remesa {codigo} falló por otra alerta: {texto_alerta}")
                    driver.get("https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CumplirRemesa/mid/396/procesoid/5/default.aspx")
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesa_CONSECUTIVOREMESA"))
                    )
                continue

            except Exception as e:
                print("segunda exepcion")
                print(f"❌ Error procesando remesa {codigo}: {e}")
                driver.get("https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CumplirRemesa/mid/396/procesoid/5/default.aspx")
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirRemesa_CONSECUTIVOREMESA"))
                )
                continue



        etiqueta_estado_remesas.config(text="✅ Remesas completadas.")
    except Exception as e:
        etiqueta_estado_remesas.config(text=f"❌ Error llenando remesas: {e}")

    boton_remesas_cargar["state"] = "normal"
    boton_remesas_ejecutar["state"] = "normal"
    etiqueta_cargando_remesas.config(text="")
    ventana.update()


# ----------------- PROCESO MANIFIESTOS -----------------
def seleccionar_txt_manifiestos():
    global codigos_manifiestos
    boton_manifiestos_cargar["state"] = "disabled"
    boton_manifiestos_ejecutar["state"] = "disabled"
    etiqueta_cargando_manifiestos.config(text="⏳ Cargando archivo...")
    ventana.update()

    try:
        archivo = filedialog.askopenfilename(filetypes=[("Archivos TXT", "*.txt")])
        if archivo:
            df = pd.read_csv(archivo, sep="\t", header=None, encoding='latin1')
            codigos_manifiestos = df.iloc[:, 8].dropna().astype(str).tolist()
            etiqueta_archivo_manifiestos.config(text=os.path.basename(archivo))
            etiqueta_estado_manifiestos.config(text=f"✅ Se cargaron {len(codigos_manifiestos)} manifiestos.")
            boton_manifiestos_ejecutar["state"] = "normal"
        else:
            etiqueta_estado_manifiestos.config(text="⚠ No se seleccionó archivo.")

    except Exception as e:
        etiqueta_estado_manifiestos.config(text=f"❌ Error: {e}")

    boton_manifiestos_cargar["state"] = "normal"
    etiqueta_cargando_manifiestos.config(text="")
    ventana.update()

def ejecutar_manifiestos():
    global codigos_manifiestos
    boton_manifiestos_cargar["state"] = "disabled"
    boton_manifiestos_ejecutar["state"] = "disabled"
    etiqueta_cargando_manifiestos.config(text="⚙️ Procesando manifiestos...")
    ventana.update()

    try:
        driver = crear_driver()
        driver.get("https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CumplirManifiesto/mid/396/procesoid/6/default.aspx")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "dnn_ctr580_FormLogIn_edUsername"))
        )
        usuario = "Sotranscolombianos1@0341"
        contrasena = "053EPA746**"
        driver.find_element(By.ID, "dnn_ctr580_FormLogIn_edUsername").send_keys(usuario)
        driver.find_element(By.ID, "dnn_ctr580_FormLogIn_edPassword").send_keys(contrasena)
        driver.find_element(By.ID, "dnn_ctr580_FormLogIn_btIngresar").click()
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "dnn_dnnUSER_cmdEdit"))
        )

        driver.get("https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CumplirManifiesto/mid/396/procesoid/6/default.aspx")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirManifiesto_NUMMANIFIESTOCARGA"))
        )

        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        observacion_texto = """NO SE ASUME NINGUNA RESPONSABILIDAD SOBRE LA MERCANCIA TRANSPORTADA, POLIZA, PESO VALORES DE FLETES E IMPUESTOS LOS ASUME DIRECTAMENTE EL CONDUCTOR, EL VEHICULO LLEVA EL PESO PERMITIDO Y LA MERCANCIA ES LICITA"""

        for codigo in codigos_manifiestos:
            print(f"Procesando manifiesto: {codigo}")
            try:
                # Ingresar número de manifiesto
                input_manifiesto = driver.find_element(By.ID, "dnn_ctr396_CumplirManifiesto_NUMMANIFIESTOCARGA")
                input_manifiesto.clear()
                input_manifiesto.send_keys(codigo)
                input_manifiesto.send_keys("\t")
                time.sleep(3)

                # Seleccionar opción "Cumplido Normal"
                select_cumplido = Select(driver.find_element(By.ID, "dnn_ctr396_CumplirManifiesto_NOMTIPOCUMPLIDOMANIFIESTO"))
                select_cumplido.select_by_visible_text("Cumplido Normal")

                # Escribir cero en los campos
                campos_cero = [
                    "dnn_ctr396_CumplirManifiesto_VALORADICIONALHORASCARGUE",
                    "dnn_ctr396_CumplirManifiesto_VALORADICIONALHORASDESCARGUE",
                    "dnn_ctr396_CumplirManifiesto_VALORADICIONALFLETE",
                    "dnn_ctr396_CumplirManifiesto_VALORDESCUENTOFLETE",
                ]

                for campo in campos_cero:
                    input_campo = driver.find_element(By.ID, campo)
                    input_campo.clear()
                    input_campo.send_keys("0")

                # Fecha actual en campo de entrega documentos
                input_fecha = driver.find_element(By.ID, "dnn_ctr396_CumplirManifiesto_FECHAENTREGADOCUMENTOS")
                input_fecha.clear()
                input_fecha.send_keys(fecha_actual)

                # Observaciones
                input_obs = driver.find_element(By.ID, "dnn_ctr396_CumplirManifiesto_OBSERVACIONES")
                input_obs.clear()
                input_obs.send_keys(observacion_texto)

                # Guardar
                driver.find_element(By.ID, "dnn_ctr396_CumplirManifiesto_btGuardar").click()

                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirManifiestoNew_btNuevo"))
                )

                print(f"✅ Manifiesto {codigo} completado correctamente.")

                # Redirigir para siguiente manifiesto
                driver.get("https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CumplirManifiesto/mid/396/procesoid/6/default.aspx")
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirManifiesto_NUMMANIFIESTOCARGA"))
                )

            except Exception as e:
                print(f"❌ Error procesando manifiesto {codigo}: {e}")

        etiqueta_estado_manifiestos.config(text="✅ Manifiestos completados.")
    except Exception as e:
        etiqueta_estado_manifiestos.config(text=f"❌ Error llenando manifiestos: {e}")

    boton_manifiestos_cargar["state"] = "normal"
    boton_manifiestos_ejecutar["state"] = "normal"
    etiqueta_cargando_manifiestos.config(text="")
    ventana.update()


# ----------------- GUI -----------------
ventana = Tk()
ventana.title("Automatizador RNDC")
ventana.geometry("500x400")

# Pantallas
frame_inicio = Frame(ventana)
frame_remesas = Frame(ventana)
frame_manifiestos = Frame(ventana)

def mostrar_frame_inicio():
    frame_remesas.pack_forget()
    frame_manifiestos.pack_forget()
    frame_inicio.pack()

def mostrar_frame_remesas():
    frame_inicio.pack_forget()
    frame_remesas.pack()

def mostrar_frame_manifiestos():
    frame_inicio.pack_forget()
    frame_manifiestos.pack()

# ---------------- INICIO -----------------
Label(frame_inicio, text="Seleccione el tipo de proceso").pack(pady=20)
Button(frame_inicio, text="Remesas", command=mostrar_frame_remesas).pack(pady=10)
Button(frame_inicio, text="Manifiestos", command=mostrar_frame_manifiestos).pack(pady=10)

# ---------------- REMESAS -----------------
Label(frame_remesas, text="Remesas - Subir archivo TXT").pack(pady=10)
boton_remesas_cargar = Button(frame_remesas, text="Seleccionar Archivo TXT", command=seleccionar_txt_remesas)
boton_remesas_cargar.pack(pady=5)
etiqueta_archivo_remesas = Label(frame_remesas, text="")
etiqueta_archivo_remesas.pack()

etiqueta_cargando_remesas = Label(frame_remesas, text="", fg="blue")
etiqueta_cargando_remesas.pack(pady=5)

boton_remesas_ejecutar = Button(frame_remesas, text="Ejecutar llenado automático", command=ejecutar_remesas)
boton_remesas_ejecutar["state"] = "disabled"
boton_remesas_ejecutar.pack(pady=10)

etiqueta_estado_remesas = Label(frame_remesas, text="")
etiqueta_estado_remesas.pack(pady=10)

Button(frame_remesas, text="⬅ Volver al menú", command=mostrar_frame_inicio).pack()

# ---------------- MANIFIESTOS -----------------
Label(frame_manifiestos, text="Manifiestos - Subir archivo TXT").pack(pady=10)
boton_manifiestos_cargar = Button(frame_manifiestos, text="Seleccionar Archivo TXT", command=seleccionar_txt_manifiestos)
boton_manifiestos_cargar.pack(pady=5)
etiqueta_archivo_manifiestos = Label(frame_manifiestos, text="")
etiqueta_archivo_manifiestos.pack()

etiqueta_cargando_manifiestos = Label(frame_manifiestos, text="", fg="blue")
etiqueta_cargando_manifiestos.pack(pady=5)

boton_manifiestos_ejecutar = Button(frame_manifiestos, text="Ejecutar llenado automático", command=ejecutar_manifiestos)
boton_manifiestos_ejecutar["state"] = "disabled"
boton_manifiestos_ejecutar.pack(pady=10)

etiqueta_estado_manifiestos = Label(frame_manifiestos, text="")
etiqueta_estado_manifiestos.pack(pady=10)

Button(frame_manifiestos, text="⬅ Volver al menú", command=mostrar_frame_inicio).pack()

# Iniciar pantalla
mostrar_frame_inicio()

ventana.mainloop()
