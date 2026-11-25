import streamlit as st
import pandas as pd
from datetime import datetime
import paho.mqtt.client as mqtt
import json
import queue
import requests
import os

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Smart Parking", page_icon="🅿️", layout="wide")

# --- CONFIGURACIÓN MQTT ---
MQTT_BROKER = "localhost"      
MQTT_PORT = 1883
PARKING_ID = "estacionamiento-central"
MQTT_TOPIC = f"iot/{PARKING_ID}/espacio/+/estado"
TOTAL_SPOTS = 8
# --- CONFIGURACIÓN N8N ---
N8N_ANALYSIS_WEBHOOK = os.getenv(
    "N8N_ANALYSIS_WEBHOOK",
    "https://primary-production-35ad554b.up.railway.app/webhook/parking-analysis"
)

# --- COLA GLOBAL (Fuera del session_state para evitar el error de Threads) ---
# Esta cola recibe los mensajes del hilo de MQTT
mqtt_queue = queue.Queue()

# --- ESTADO DE LA SESIÓN ---
if 'parking_data' not in st.session_state:
    st.session_state.parking_data = {f"A-{i+1:02d}": False for i in range(TOTAL_SPOTS)}
if 'history' not in st.session_state:
    st.session_state.history = []
if 'mqtt_connected' not in st.session_state:
    st.session_state.mqtt_connected = False
if 'last_update' not in st.session_state:
    st.session_state.last_update = "Sin datos"

def update_state():
    occupied = sum(st.session_state.parking_data.values())
    st.session_state.history.append({
        "Hora": datetime.now().strftime("%H:%M:%S"),
        "Ocupados": occupied
    })
    if len(st.session_state.history) > 20:
        st.session_state.history.pop(0)

# --- CALLBACK DE MQTT (Corre en segundo plano) ---
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        # Guardamos el mensaje en la cola global (NO en session_state)
        mqtt_queue.put(payload)
    except Exception as e:
        print(f"Error procesando mensaje MQTT: {e}")

# --- CLIENTE MQTT ---
@st.cache_resource
def init_mqtt():
    # Usamos CallbackAPIVersion.VERSION2 para quitar el DeprecationWarning
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_message
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.subscribe(MQTT_TOPIC)
        client.loop_start()  
        return client
    except Exception as e:
        print(f"No se pudo conectar a MQTT: {e}")
        return None

if 'mqtt_client' not in st.session_state:
    st.session_state.mqtt_client = init_mqtt()
    if st.session_state.mqtt_client:
        st.session_state.mqtt_connected = True


# --- DASHBOARD CON ACTUALIZACIÓN AUTOMÁTICA ---
@st.fragment(run_every="2s")
def render_dashboard():

    # 1. Procesar mensajes recibidos por MQTT
    updated = False

    while not mqtt_queue.empty():
        payload = mqtt_queue.get()

        spot_id = payload.get("spot_id")
        occupied = payload.get("occupied", False)
        timestamp = payload.get("timestamp", "Actualizado")

        if spot_id in st.session_state.parking_data:
            # Actualizar la última recepción, aunque no cambie la ocupación
            st.session_state.last_update = timestamp

            # Actualizar el estado del espacio
            if st.session_state.parking_data[spot_id] != occupied:
                st.session_state.parking_data[spot_id] = occupied
                updated = True

    # Registrar en el historial solo los cambios de ocupación
    if updated:
        update_state()

    # 2. Calcular métricas
    occupied_count = sum(st.session_state.parking_data.values())
    total_spots = len(st.session_state.parking_data)

    # 3. Encabezado
    st.title("🅿️ Panel de aparcamiento inteligente")

    if st.session_state.mqtt_connected:
        st.success(
            f"🟢 Conectado a MQTT - Última actualización: "
            f"{st.session_state.last_update}"
        )
    else:
        st.warning("🟡 Modo Simulación - Sin conexión MQTT.")

    if occupied_count == total_spots:
        st.error("🔴 ESTACIONAMIENTO LLENO - Alerta enviada por n8n")

    st.divider()

    # 4. Distribución del dashboard
    col_left, col_right = st.columns([1.2, 1])

    with col_left:
        st.subheader("🗺️ Mapa de Espacios")

        spot_ids = list(st.session_state.parking_data.keys())

        for row in range(2):
            cols = st.columns(4)

            for col_idx in range(4):
                spot_index = row * 4 + col_idx

                if spot_index < len(spot_ids):
                    spot_id = spot_ids[spot_index]
                    is_occupied = st.session_state.parking_data[spot_id]

                    with cols[col_idx]:
                        if is_occupied:
                            if st.button(
                                f"🚗 {spot_id}",
                                key=f"spot_{spot_id}",
                                use_container_width=True,
                                type="primary"
                            ):
                                st.session_state.parking_data[spot_id] = False
                                update_state()
                                st.rerun()
                        else:
                            if st.button(
                                f"🟢 {spot_id}",
                                key=f"spot_{spot_id}",
                                use_container_width=True
                            ):
                                st.session_state.parking_data[spot_id] = True
                                update_state()
                                st.rerun()

        st.divider()

        st.subheader("📊 Estado Actual")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Total", total_spots)
        c2.metric("Libres", total_spots - occupied_count)
        c3.metric("Ocupados", occupied_count)
        c4.metric(
            "Ocupación",
            f"{(occupied_count / total_spots) * 100:.0f}%"
        )

    with col_right:
        st.subheader("📈 Historial de Ocupación")

        if st.session_state.history:
            df = pd.DataFrame(st.session_state.history)
            st.line_chart(
                df.set_index("Hora")["Ocupados"],
                color="#f56565"
            )
        else:
            st.caption("Aún no hay datos.")

        st.divider()




# Ejecutar dashboard
render_dashboard()
