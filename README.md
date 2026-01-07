# 🚀 AutoRNDC - Procesamiento Paralelo de Remesas

## 📋 Descripción

Nueva funcionalidad que permite procesar un archivo de remesas dividido en múltiples sesiones paralelas, cada una con su propio navegador Chrome, acelerando significativamente el tiempo total de procesamiento.

## ✨ Características Nuevas

### 🔄 Procesamiento Paralelo
- **Divide automáticamente** tu archivo en N partes
- **Ejecuta N navegadores simultáneamente**, cada uno procesando una parte
- **Monitoreo en tiempo real** de cada sesión
- **Progreso individual y global** visible en tiempo real

### 📊 Ventana de Monitoreo
- Vista detallada de cada sesión activa
- Barra de progreso por sesión
- Estadísticas globales consolidadas
- Controles para pausar/continuar/cancelar todas las sesiones

## 🎯 ¿Cuándo usar procesamiento paralelo?

### ✅ Recomendado:
- Archivos con **50+ remesas**
- Cuando necesitas **procesar rápidamente**
- Tienes buena conexión a internet

### ⚠️ No recomendado:
- Archivos con menos de 10 remesas
- Conexión inestable
- PC con recursos limitados

## 📖 Guía de Uso

### 1. Ejecutar la aplicación

```bash
# Si estás en desarrollo
python app_paralelo.py

# Si tienes el .exe
AutoRNDC_Paralelo.exe
```

### 2. Seleccionar archivo TXT

1. Haz clic en **"📂 Seleccionar Archivo TXT"**
2. Elige tu archivo con los códigos de remesas

### 3. Configurar número de sesiones

Usa el slider para elegir cuántas sesiones paralelas quieres:

| Sesiones | Recomendado para | Velocidad |
|----------|------------------|-----------|
| 1 | < 20 remesas | Normal |
| 2 | 20-50 remesas | 2x más rápido |
| 3 | 50-100 remesas | 3x más rápido |
| 4 | 100-200 remesas | 4x más rápido |
| 5 | 200+ remesas | 5x más rápido |

**💡 Consejo:** Más sesiones = más rápido, pero también más recursos del PC

### 4. Ejecutar

1. Haz clic en **"▶ Ejecutar Procesamiento Paralelo"**
2. Se abrirá la **Ventana de Monitoreo**
3. Verás cada sesión procesando su parte en tiempo real

### 5. Monitorear

La ventana de monitoreo muestra:

```
┌─────────────────────────────────────┐
│  Sesión 1                           │
│  Procesando remesa 12345...         │
│  ████████████░░░░░ 60%             │
│  15 / 25                            │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Sesión 2                           │
│  Procesando remesa 67890...         │
│  ███████████████░░ 80%             │
│  20 / 25                            │
└─────────────────────────────────────┘

📊 Progreso Global
Total: 35/50 remesas | Sesiones: 2/2 activas
████████████████░░░░ 70%
```

### 6. Controles durante la ejecución

| Botón | Acción |
|-------|--------|
| ⏸ Pausar Todas | Pausa todas las sesiones |
| ▶ Continuar Todas | Reanuda todas las sesiones |
| ⛔ Cancelar Todas | Detiene todo el proceso |

## 📁 Estructura de Archivos

### Nuevos archivos:
```
AutoRNDC/
├── _core/
│   └── remesas_paralelo.py      # Motor de procesamiento paralelo
├── _gui/
│   └── main_window_paralelo.py  # Interfaz mejorada
├── app_paralelo.py              # Punto de entrada
└── README_PARALELO.md           # Este archivo
```

### Logs generados:
```
_logs/
├── log_remesa_sesion1_2025-01-07_10-30-00.csv
├── log_remesa_sesion2_2025-01-07_10-30-00.csv
├── log_remesa_sesion3_2025-01-07_10-30-00.csv
└── eventos_remesa_2025-01-07_10-30-00.json
```

## 🔧 Detalles Técnicos

### Cómo funciona la división:

Si tienes **100 remesas** y eliges **3 sesiones**:
- Sesión 1: remesas 1-34 (34 remesas)
- Sesión 2: remesas 35-67 (33 remesas)
- Sesión 3: remesas 68-100 (33 remesas)

La distribución es **automática y equitativa**.

### Requisitos del sistema:

- **RAM:** +2GB disponible por sesión
- **CPU:** Multi-core recomendado
- **Red:** Conexión estable (el servidor RNDC debe soportar múltiples sesiones)

### Limitaciones:

- Máximo **5 sesiones paralelas** (por estabilidad)
- Mínimo **1 remesa por sesión** (no puedes tener más sesiones que remesas)

## ❓ Preguntas Frecuentes

### ¿Puedo usar el modo tradicional (sin paralelo)?

Sí, simplemente elige **1 sesión** en el slider. Funcionará exactamente igual que antes.

### ¿Se pueden procesar dos archivos diferentes a la vez?

No desde la misma instancia. Pero puedes abrir dos veces el programa .exe y procesar archivos diferentes (como hacías antes).

### ¿Qué pasa si una sesión falla?

Las demás sesiones continuarán procesando normalmente. Al final verás el resumen con las sesiones exitosas y fallidas.

### ¿Los checkpoints funcionan con múltiples sesiones?

Sí, cada sesión tiene su propio checkpoint independiente para poder reanudar si algo falla.

## 🐛 Solución de Problemas

### Problema: "No se pueden crear N sesiones"

**Causa:** Tienes menos remesas que sesiones solicitadas.

**Solución:** Reduce el número de sesiones o aumenta el tamaño del archivo.

---

### Problema: Las sesiones se cierran inesperadamente

**Causa:** Posible problema de memoria o conexión.

**Solución:** Reduce el número de sesiones a 2 o 3.

---

### Problema: El proceso es muy lento a pesar de usar múltiples sesiones

**Causa:** Cuello de botella en el servidor RNDC o tu conexión.

**Solución:** El procesamiento paralelo no siempre es más rápido si el servidor tiene límites de velocidad.

## 📞 Soporte

Si encuentras problemas:

1. Revisa los logs en `_logs/`
2. Verifica tu conexión a internet
3. Intenta con menos sesiones primero (2-3)

## 🎉 Ventajas del Procesamiento Paralelo

### Antes (1 sesión):
```
100 remesas × 30 segundos/remesa = 50 minutos
```

### Ahora (5 sesiones):
```
100 remesas ÷ 5 sesiones × 30 segundos/remesa = 10 minutos
```

**¡5 veces más rápido!** 🚀

---

**Versión:** 2.0.0-PARALELO  
**Última actualización:** Enero 2025