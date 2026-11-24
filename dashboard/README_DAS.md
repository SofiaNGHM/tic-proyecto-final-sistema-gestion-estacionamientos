# 🅿️ Dashboard de Estacionamiento Inteligente (Streamlit)

Este módulo corresponde a la interfaz gráfica del **Sistema Inteligente de Gestión de Estacionamientos**. Está desarrollado en Python utilizando **Streamlit** para el frontend y **Paho-MQTT** para la comunicación en tiempo real con el hardware (sensores IoT simulados).

## 📋 Características principales

- **Monitoreo en tiempo real:** Se conecta al broker MQTT (EMQX) y actualiza el estado de los 8 espacios de estacionamiento automáticamente cada 2 segundos.
- **Mapa visual interactivo:** Muestra los espacios en verde (libre) o rojo (ocupado).
- **Métricas clave:** Panel con contadores de espacios totales, libres, ocupados y tasa de ocupación.
- **Historial gráfico:** Gráfico de línea que muestra la evolución de la ocupación en el tiempo.
- **Modo de contingencia (Simulación):** Permite hacer clic en los espacios para cambiar su estado manualmente (útil si el sensor falla durante la demo).
- **Análisis Predictivo (Módulo IA):** Genera un reporte descriptivo (actualmente simulado, con preparación para conectar a n8n/OpenAI).

## 🛠️ Requisitos previos

Antes de ejecutar esta interfaz, asegúrate de tener instalado:
1. **Python 3.10+**
2. **Docker Desktop** (necesario para levantar el broker MQTT y el sensor simulado del proyecto principal).
3. Las librerías listadas en el archivo `requirements.txt` (que se instalarán en el siguiente paso).

## 🚀 Guía de Ejecución

Para probar la interfaz se necesita tener corriendo el ecosistema IoT.

### Paso 1: Levantar el Broker MQTT y el Sensor (Terminal 1)
Desde la raíz del repositorio principal (fuera de esta carpeta), asegúrate de que el broker y el sensor simulado estén en ejecución:
```bash
# Levantar el broker (si no está en Docker Desktop)
cd ../broker
docker compose up -d

# En otra terminal, levantar el sensor simulado
cd ../sensor-hc-sr04-simulado
python parking_simulator.py --broker localhost --parking-id estacionamiento-central --spots 8