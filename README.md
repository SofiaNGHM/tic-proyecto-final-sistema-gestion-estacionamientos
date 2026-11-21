# Sistema de gestion de estacionamientos con IoT

Proyecto final que simula los sensores ultrasonicos **HC-SR04** usados para detectar si un espacio de estacionamiento esta ocupado. Los datos se transmiten por MQTT a traves de un broker EMQX y se pueden visualizar en un monitor en consola.

## Problema

Los conductores pierden tiempo buscando espacios disponibles. La simulacion IoT permite conocer el estado ocupado/libre de cada espacio antes de llegar y puede convertirse en la fuente de datos de una aplicacion de estacionamiento.

## Arquitectura

```text
HC-SR04 simulado  --(JSON/MQTT)-->  Broker EMQX  --(suscripcion)-->  Monitor / Consumidores
```

Componentes:

| Componente | Carpeta | Funcion |
|---|---|---|
| Broker MQTT | `broker/` | Recibe y distribuye los mensajes entre dispositivos. |
| Sensor simulado | `sensor-hc-sr04-simulado/` | Genera distancias y estado por espacio, como un HC-SR04 real. |
| Monitor | `monitor/` | Se suscribe y muestra la ocupacion en consola. |

## Formato MQTT

- Broker: `localhost:1883` cuando se ejecuta localmente.
- Topico:

```text
iot/<parking-id>/espacio/<spot-id>/estado
```

 ejemplo:

```text
iot/estacionamiento-central/espacio/A-01/estado
```

- Payload:

```json
{
  "parking_id": "estacionamiento-central",
  "spot_id": "A-01",
  "timestamp": "2026-01-01T00:00:00+00:00",
  "occupied": true,
  "distance_cm": 15.2,
  "threshold_cm": 30,
  "sensor_model": "HC-SR04",
  "event": "occupied"
}
```

El sensor publica con `retain=True`, por lo que un consumidor recibe el ultimo estado conocido al conectarse.

## Ejecucion con Docker

Desde la carpeta `broker`:

```powershell
docker compose up -d --build
docker ps
```

Se arrancan el broker y el sensor. Para ver el tablero:

```powershell
docker compose --profile monitor up -d monitor
docker logs -f monitor_estacionamiento
```

Para detener el sistema:

```powershell
docker compose down
```

## Ejecucion local

### 1. Broker EMQX

```powershell
cd broker
docker compose up -d emqx
```

Panel administrativo de EMQX: <http://localhost:18083>
Usuario inicial: `admin` / Contraseña inicial: `public`

### 2. Sensor simulado

```powershell
cd ..
cd sensor-hc-sr04-simulado
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python parking_simulator.py --broker localhost --parking-id estacionamiento-central --spots 8
```

Argumentos utiles:

```text
--broker      Host o direccion IP del broker MQTT.
--port        Puerto MQTT, por defecto 1883.
--parking-id  Identificador del estacionamiento.
--spots       Cantidad de espacios simulados.
--interval    Segundos entre mediciones.
--once        Publica una sola medicion por espacio y termina.
```

### 3. Monitor

```powershell
cd ..
cd monitor
python -m pip install -r requirements.txt
python monitor.py --broker localhost --parking-id estacionamiento-central
```

Para escuchar todos los estacionamientos:

```powershell
python monitor.py --parking-id "#"
```

### 4. Verificacion con un cliente MQTT

Usando MQTT Explorer, MQTTX u otro cliente:

- Host: `localhost`
- Puerto: `1883`
- Topico: `iot/estacionamiento-central/#`

## Simulacion fisica del HC-SR04

El simulador usa valores representativos de distancia:

| Estado | Distancia simulada | Decision |
|---|---:|---|
| Ocupado | 4 a 24 cm | Vehiculo detectado. |
| Libre | 38 a 110 cm | No hay vehiculo en el espacio. |

El umbral de deteccion es 30 cm. Las transiciones usan un modelo probabilistico simple y estable para simular entradas y salidas de vehiculos.

## Pruebas

Desde la raiz del repositorio:

```powershell
python -m pip install -r sensor-hc-sr04-simulado\requirements.txt
python -m unittest discover -s . -p "test_*.py"
```

## Futuras integraciones

Este simulador publica un modelo de datos estable y listo para consumirse desde:

- API de gestion de estacionamientos.
- Aplicacion movil para conductores.
- Base de datos para metricas de uso.
- Sistema de reservas y cobros.
