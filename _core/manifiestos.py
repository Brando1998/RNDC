from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import time
from _utils.logger import registrar_log_remesa


def hacer_login(driver):
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

def navegar_a_formulario(driver):
    driver.get("https://rndc.mintransporte.gov.co/programasRNDC/creardocumento/tabid/69/ctl/CumplirManifiesto/mid/396/procesoid/6/default.aspx")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "dnn_ctr396_CumplirManifiesto_NUMMANIFIESTOCARGA"))
    )

def llenar_formulario_manifiesto(driver, codigo):
    from datetime import datetime, timedelta

    # observacion_texto = """NO SE ASUME NINGUNA RESPONSABILIDAD SOBRE LA MERCANCIA TRANSPORTADA, POLIZA, PESO VALORES DE FLETES E IMPUESTOS LOS ASUME DIRECTAMENTE EL CONDUCTOR, EL VEHICULO LLEVA EL PESO PERMITIDO Y LA MERCANCIA ES LICITA"""
    campos_utilizados = []

    # Buscar manifiesto
    input_manifiesto = driver.find_element(By.ID, "dnn_ctr396_CumplirManifiesto_NUMMANIFIESTOCARGA")
    input_manifiesto.clear()
    input_manifiesto.send_keys(codigo)
    input_manifiesto.send_keys("\t")
    time.sleep(1)

    # Tipo de cumplimiento
    Select(driver.find_element(By.ID, "dnn_ctr396_CumplirManifiesto_NOMTIPOCUMPLIDOMANIFIESTO")).select_by_visible_text("Cumplido Normal")
    campos_utilizados.append(("NOMTIPOCUMPLIDOMANIFIESTO", "Cumplido Normal"))

    # Campos con cero
    campos_cero = [
        "VALORADICIONALHORASCARGUE",
        "VALORADICIONALHORASDESCARGUE",
        "VALORADICIONALFLETE",
        "VALORDESCUENTOFLETE",
    ]
    for campo in campos_cero:
        campo_id = f"dnn_ctr396_CumplirManifiesto_{campo}"
        driver.find_element(By.ID, campo_id).clear()
        driver.find_element(By.ID, campo_id).send_keys("0")
        campos_utilizados.append((campo, "0"))

    # Obtener y calcular fecha entrega
    fecha_expedicion_id = "dnn_ctr396_CumplirManifiesto_FECHAEXPEDICIONMANIFIESTO"
    fecha_expedicion_str = driver.find_element(By.ID, fecha_expedicion_id).get_attribute("value").strip()

    try:
        # Aseguramos el formato de fecha
        fecha_expedicion = datetime.strptime(fecha_expedicion_str, "%d/%m/%Y")
        fecha_entrega = fecha_expedicion + timedelta(days=5)
        fecha_entrega_str = fecha_entrega.strftime("%d/%m/%Y")

        # Insertamos la nueva fecha
        fecha_entrega_id = "dnn_ctr396_CumplirManifiesto_FECHAENTREGADOCUMENTOS"
        driver.find_element(By.ID, fecha_entrega_id).clear()
        driver.find_element(By.ID, fecha_entrega_id).send_keys(fecha_entrega_str)
        campos_utilizados.append(("FECHAENTREGADOCUMENTOS", fecha_entrega_str))

    except Exception as e:
        raise Exception(f"No se pudo calcular fecha de entrega: {e}")

    # Observaciones (opcional, puedes descomentar si se requiere)
    # obs_id = "dnn_ctr396_CumplirManifiesto_OBSERVACIONES"
    # driver.find_element(By.ID, obs_id).clear()
    # driver.find_element(By.ID, obs_id).send_keys(observacion_texto)
    # campos_utilizados.append(("OBSERVACIONES", observacion_texto))

    time.sleep(1)
    return campos_utilizados


def guardar_y_manejar_alertas(driver, codigo, actualizar_estado_callback, campos):
    flete_id = "dnn_ctr396_CumplirManifiesto_VALORADICIONALFLETE"
    incremento = 100_000
    max_intentos = 20  # evitar bucles infinitos
    intentos = 0

    while intentos < max_intentos:
        try:
            guardar_btn = driver.find_element(By.ID, "dnn_ctr396_CumplirManifiesto_btGuardar")
            guardar_btn.click()

            WebDriverWait(driver, 3).until(EC.alert_is_present())
            alerta = driver.switch_to.alert
            mensaje_alerta = alerta.text
            alerta.accept()

            # Si la alerta indica error conocido, incrementar y reintentar
            if "error" in mensaje_alerta.lower() or "no se puede" in mensaje_alerta.lower():
                intentos += 1
                actualizar_estado_callback(f"⚠️ Alerta en manifiesto {codigo}: {mensaje_alerta}. Incrementando flete...")

                campo_flete = driver.find_element(By.ID, flete_id)
                valor_actual = int(campo_flete.get_attribute("value").replace(".", "").replace(",", "") or "0")
                nuevo_valor = valor_actual + incremento

                campo_flete.clear()
                campo_flete.send_keys(str(nuevo_valor))

                # Actualiza registro en campos
                for i, (nombre, _) in enumerate(campos):
                    if nombre == "VALORADICIONALFLETE":
                        campos[i] = ("VALORADICIONALFLETE", str(nuevo_valor))
                        break
                else:
                    campos.append(("VALORADICIONALFLETE", str(nuevo_valor)))

                time.sleep(1)
                continue
            else:
                # Se asumirá que fue exitoso
                registrar_log_remesa(codigo, mensaje_alerta, campos)
                actualizar_estado_callback(f"✅ Manifiesto {codigo}: {mensaje_alerta}")
                return
        except Exception as e:
            registrar_log_remesa(codigo, f"Error inesperado al guardar: {e}", campos)
            actualizar_estado_callback(f"⚠️ Error inesperado al guardar manifiesto {codigo}: {e}")
            return

    registrar_log_remesa(codigo, "❌ Demasiados intentos al guardar (flete ajustado múltiples veces)", campos)
    actualizar_estado_callback(f"❌ Manifiesto {codigo}: demasiados intentos, falló al guardar.")

def ejecutar_manifiestos(driver, codigos, actualizar_estado_callback):
    try:
        hacer_login(driver)
        navegar_a_formulario(driver)

        for codigo in codigos:
            actualizar_estado_callback(f"Procesando manifiesto {codigo}...")
            navegar_a_formulario(driver)
            try:
                campos = llenar_formulario_manifiesto(driver, codigo)
                guardar_y_manejar_alertas(driver, codigo, actualizar_estado_callback, campos)
            except Exception as e:
                registrar_log_remesa(codigo, f"Excepción: {e}", campos if 'campos' in locals() else [])
                actualizar_estado_callback(f"❌ Error en manifiesto {codigo}: {e}")
                navegar_a_formulario(driver)
                continue

        actualizar_estado_callback("✅ Todos los manifiestos completados.")
    except Exception as e:
        actualizar_estado_callback(f"❌ Error general llenando manifiestos: {e}")
