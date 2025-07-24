from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import time

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
    observacion_texto = """NO SE ASUME NINGUNA RESPONSABILIDAD SOBRE LA MERCANCIA TRANSPORTADA, POLIZA, PESO VALORES DE FLETES E IMPUESTOS LOS ASUME DIRECTAMENTE EL CONDUCTOR, EL VEHICULO LLEVA EL PESO PERMITIDO Y LA MERCANCIA ES LICITA"""
    fecha_actual = datetime.today().strftime("%d/%m/%Y")

    # Buscar manifiesto
    input_manifiesto = driver.find_element(By.ID, "dnn_ctr396_CumplirManifiesto_NUMMANIFIESTOCARGA")
    input_manifiesto.clear()
    input_manifiesto.send_keys(codigo)
    input_manifiesto.send_keys("\t")
    time.sleep(1)

    # Seleccionar tipo de cumplimiento
    Select(driver.find_element(By.ID, "dnn_ctr396_CumplirManifiesto_NOMTIPOCUMPLIDOMANIFIESTO")).select_by_visible_text("Cumplido Normal")

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

    # Fecha actual en múltiples campos relacionados con la entrega
    campos_fecha = [
        "FECHAENTREGADOCUMENTOS",
        "FECHALLEGADACARGUE",
        "FECHAENTRADACARGUE",
        "FECHASALIDACARGUE",
        "FECHALLEGADADESCARGUE",
        "FECHAENTRADADESCARGUE",
        "FECHASALIDADESCARGUE",
    ]
    for campo in campos_fecha:
        campo_id = f"dnn_ctr396_CumplirManifiesto_{campo}"
        driver.find_element(By.ID, campo_id).clear()
        driver.find_element(By.ID, campo_id).send_keys(fecha_actual)

    # Observaciones
    obs_id = "dnn_ctr396_CumplirManifiesto_OBSERVACIONES"
    driver.find_element(By.ID, obs_id).clear()
    driver.find_element(By.ID, obs_id).send_keys(observacion_texto)

    time.sleep(1)

def guardar_y_manejar_alertas(driver, codigo, actualizar_estado_callback):
    try:
        guardar_btn = driver.find_element(By.ID, "id_boton_guardar")
        guardar_btn.click()

        WebDriverWait(driver, 10).until(EC.alert_is_present())
        alerta = driver.switch_to.alert
        mensaje_alerta = alerta.text
        alerta.accept()

        actualizar_estado_callback(f"✅ Manifiesto {codigo}: {mensaje_alerta}")
    except Exception as e:
        actualizar_estado_callback(f"⚠️ Error al guardar manifiesto {codigo}: {e}")

def ejecutar_manifiestos(driver, codigos, actualizar_estado_callback):
    try:
        hacer_login(driver)
        navegar_a_formulario(driver)

        for codigo in codigos:
            actualizar_estado_callback(f"Procesando manifiesto {codigo}...")
            navegar_a_formulario(driver)
            try:
                llenar_formulario_manifiesto(driver, codigo)
                guardar_y_manejar_alertas(driver, codigo, actualizar_estado_callback)
            except Exception as e:
                actualizar_estado_callback(f"❌ Error en manifiesto {codigo}: {e}")
                navegar_a_formulario(driver)
                continue

        actualizar_estado_callback("✅ Todos los manifiestos completados.")
    except Exception as e:
        actualizar_estado_callback(f"❌ Error general llenando manifiestos: {e}")
