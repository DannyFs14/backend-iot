from flask import Flask, request, jsonify
from flask_cors import CORS
from config import SERVER_CONFIG
import models
import predictor

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que el servidor está funcionando"""
    return jsonify({'status': 'ok', 'message': 'Backend funcionando correctamente'})

@app.route('/api/ingest', methods=['POST'])
def ingest_data():
    """Recibe datos del ESP32 y los procesa"""
    try:
        data = request.get_json()
        
        temperature = float(data.get('temperature', 0))
        humidity = float(data.get('humidity', 0))
        current = float(data.get('current', 0))
        
        print(f"[Datos recibidos] Temp: {temperature}°C, Hum: {humidity}%, Corriente: {current}A")
        
        reading_id = models.insert_sensor_reading(temperature, humidity, current)
        
        if not reading_id:
            return jsonify({'error': 'Error guardando datos'}), 500
        
        prediction = predictor.make_prediction(temperature, humidity, current)
        
        prediction_id = models.insert_prediction(
            reading_id,
            prediction['risk_level'],
            prediction['failure_probability'],
            prediction['influential_factors']
        )
        
        alerts = predictor.check_alerts(
            temperature, humidity, current, prediction['risk_level']
        )
        
        for alert in alerts:
            models.insert_alert(
                prediction_id,
                alert['type'],
                alert['message'],
                alert['severity']
            )

            # <NUEVO> Auto-resolver alertas si los valores volvieron a la normalidad
        models.auto_resolve_alerts(temperature, current)
        
        print(f"[Predicción] Riesgo: {prediction['risk_level']} ({prediction['failure_probability']*100:.1f}%)")
        
        return jsonify({
            'success': True,
            'reading_id': reading_id,
            'prediction': prediction,
            'alerts': alerts
        })
        
    except Exception as e:
        print(f"[Error] {str(e)}")
        return jsonify({'error': str(e)}), 500
    


@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    """Obtiene datos para el dashboard, filtrado por equipo si se especifica"""
    try:
        # <CHANGE> Obtener el parametro equipo_id de la query string
        equipo_id = request.args.get('equipo_id')
        
        print(f"[API Dashboard] Solicitado para equipo_id: {equipo_id}")
        
        connection = models.get_db_connection()
        if not connection:
            return jsonify({'error': 'No hay conexion a la base de datos'}), 500
        
        with connection.cursor() as cursor:
            # <CHANGE> Filtrar por equipo_id si se especifica
            if equipo_id:
                sql = """
                    SELECT * FROM lecturas_sensores 
                    WHERE sensor_id = %s
                    ORDER BY timestamp DESC LIMIT 1
                """
                cursor.execute(sql, (equipo_id,))
                print(f"[API Dashboard] Filtrando por sensor_id: {equipo_id}")
            else:
                sql = """
                    SELECT * FROM lecturas_sensores 
                    ORDER BY timestamp DESC LIMIT 1
                """
                cursor.execute(sql)
                print(f"[API Dashboard] Sin filtro, obteniendo ultima lectura general")
            
            current_reading = cursor.fetchone()
            
            if current_reading:
                print(f"[API Dashboard] Lectura obtenida - Sensor: {current_reading.get('sensor_id')}, Temp: {current_reading.get('temperatura')}")
            
            # <CHANGE> Filtrar alertas por equipo_id si se especifica
            if equipo_id:
                sql_alerts = """
                    SELECT * FROM alertas 
                    WHERE equipo_id = %s
                    ORDER BY timestamp DESC LIMIT 10
                """
                cursor.execute(sql_alerts, (equipo_id,))
            else:
                sql_alerts = """
                    SELECT * FROM alertas 
                    ORDER BY timestamp DESC LIMIT 10
                """
                cursor.execute(sql_alerts)
            
            alerts = cursor.fetchall()
        
        connection.close()
        
        if not current_reading:
            return jsonify({
                'current': {
                    'temperature': 0,
                    'humidity': 0,
                    'current': 0,
                    'risk_level': 'low',
                    'failure_probability': 0
                },
                'alerts': []
            })
        
        # Formatear respuesta
        response = {
            'current': {
                'temperature': current_reading['temperatura'],
                'humidity': current_reading['humedad'],
                'current': current_reading['corriente'],
                'risk_level': current_reading.get('nivel_riesgo', 'low'),
                'failure_probability': current_reading.get('riesgo_predicho', 0)
            },
            'alerts': [{
                'id': a['id'],
                'alert_type': a.get('tipo', ''),
                'message': a.get('mensaje', ''),
                'severity': a.get('severidad', ''),
                'timestamp': a['timestamp'].isoformat() if a.get('timestamp') else None,
                'status': a.get('estado', 'pendiente')
            } for a in alerts]
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"[Error Dashboard] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500




@app.route('/api/history', methods=['GET'])
def get_history():
    """Obtiene el historial de lecturas"""
    try:
        limit = int(request.args.get('limit', 100))
        readings = models.get_latest_readings(limit=limit)
        
        formatted_readings = []
        for r in readings:
            formatted_readings.append({
                'id': r['id'],
                'temperature': r['temperatura'],
                'humidity': r['humedad'],
                'current': r['corriente'],
                'timestamp': r['timestamp'].isoformat() if r['timestamp'] else None,
                'risk_level': r.get('nivel_riesgo'),
                'failure_probability': r.get('riesgo_predicho')
            })
        
        return jsonify({'readings': formatted_readings})
        
    except Exception as e:
        print(f"[Error Historial] {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        connection = models.get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Error de conexion'}), 500
        
        with connection.cursor() as cursor:
            sql = """
                SELECT u.*, e.equipo_id 
                FROM usuarios u
                LEFT JOIN equipos e ON e.operador_id = u.id
                WHERE u.email = %s
            """
            cursor.execute(sql, (email,))
            user = cursor.fetchone()
        
        connection.close()
        
        # <CHANGE> Usar password_hash en lugar de password
        if user and user['password_hash'] == password:
            return jsonify({
                'success': True,
                'user': {
                    'id': user['id'],
                    'name': user['nombre'],
                    'email': user['email'],
                    'role': user['rol'],
                    'equipo_id': user.get('equipo_id', None)
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Credenciales invalidas'}), 401
            
    except Exception as e:
        print(f"[Error Login] {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

    

    # Reemplazar el endpoint /api/historial existente con este:
@app.route('/api/historial', methods=['GET'])
def get_historial():
    """Obtiene el historial de lecturas con filtros de fecha y equipo"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        equipo_id = request.args.get('equipo_id')  # <CHANGE> Agregar filtro por equipo
        
        print(f"[API Historial] Filtros - Inicio: {start_date}, Fin: {end_date}, Equipo: {equipo_id}")
        
        connection = models.get_db_connection()
        if not connection:
            return jsonify({'error': 'No hay conexion'}), 500
        
        with connection.cursor() as cursor:
            sql = """
                SELECT r.*, p.nivel_riesgo, p.riesgo_predicho, r.sensor_id as equipo_id
                FROM lecturas_sensores r
                LEFT JOIN predicciones p ON r.id = p.lectura_id
                WHERE 1=1
            """
            params = []
            
            # <CHANGE> Filtrar por equipo si se especifica
            if equipo_id:
                sql += " AND r.sensor_id = %s"
                params.append(equipo_id)
            
            if start_date:
                sql += " AND r.timestamp >= %s"
                params.append(start_date + ' 00:00:00')
            
            if end_date:
                sql += " AND r.timestamp <= %s"
                params.append(end_date + ' 23:59:59')
            
            sql += " ORDER BY r.timestamp DESC LIMIT 500"
            
            cursor.execute(sql, params if params else None)
            readings = cursor.fetchall()
        
        connection.close()
        
        formatted_readings = []
        for r in readings:
            # <CHANGE> Obtener nombre del equipo
            equipo_nombre = r.get('sensor_id', 'Desconocido')
            if equipo_nombre == 'ESP32_001':
                equipo_nombre = 'Laptop RRHH'
            elif equipo_nombre == 'ESP32_002':
                equipo_nombre = 'Laptop Contabilidad'
            elif equipo_nombre == 'ESP32_003':
                equipo_nombre = 'Laptop Administracion'
            
            formatted_readings.append({
                'id': r['id'],
                'temperature': r['temperatura'],
                'humidity': r['humedad'],
                'current': r['corriente'],
                'timestamp': r['timestamp'].isoformat() if r['timestamp'] else None,
                'risk_level': r.get('nivel_riesgo'),
                'failure_probability': r.get('riesgo_predicho'),
                'equipo_id': r.get('sensor_id'),
                'equipo_nombre': equipo_nombre
            })
        
        print(f"[API Historial] Devolviendo {len(formatted_readings)} registros")
        
        return jsonify({'readings': formatted_readings})
        
    except Exception as e:
        print(f"[Error Historial] {str(e)}")
        return jsonify({'error': str(e)}), 500

# Agregar endpoint para explicabilidad por equipo
@app.route('/api/explicacion', methods=['GET'])
def get_explicacion():
    """Obtiene la explicacion del modelo, filtrada por equipo si se especifica"""
    try:
        equipo_id = request.args.get('equipo_id')  # <CHANGE> Agregar filtro por equipo
        
        connection = models.get_db_connection()
        if not connection:
            return jsonify({'error': 'No hay conexion'}), 500
        
        with connection.cursor() as cursor:
            if equipo_id:
                # Obtener ultima lectura del equipo especifico
                sql = """
                    SELECT * FROM lecturas_sensores 
                    WHERE sensor_id = %s 
                    ORDER BY timestamp DESC LIMIT 1
                """
                cursor.execute(sql, (equipo_id,))
            else:
                # Obtener la ultima lectura de cualquier equipo
                sql = """
                    SELECT * FROM lecturas_sensores 
                    ORDER BY timestamp DESC LIMIT 1
                """
                cursor.execute(sql)
            
            current = cursor.fetchone()
        
        connection.close()
        
        if not current:
            return jsonify({
                'razon_principal': 'No hay datos suficientes para generar una explicacion',
                'factores_influyentes': [],
                'equipo_id': equipo_id,
                'equipo_nombre': 'Sin datos'
            })
        
        temp = current['temperatura']
        humidity = current['humedad']
        corriente = current['corriente']
        
        # Calcular importancia de cada factor
        factores = []
        
        # Temperatura (importancia 0-35%)
        temp_importance = min(abs(temp - 25) * 2, 35)
        factores.append({
            'factor': 'Temperatura',
            'importancia': round(temp_importance, 1)
        })
        
        # Humedad (importancia 0-25%)
        humidity_importance = min(abs(humidity - 50) * 0.5, 25)
        factores.append({
            'factor': 'Humedad',
            'importancia': round(humidity_importance, 1)
        })
        
        # Corriente (importancia 0-40%)
        current_importance = min(abs(corriente) * 8, 40)
        factores.append({
            'factor': 'Corriente',
            'importancia': round(current_importance, 1)
        })
        
        # Ordenar por importancia descendente
        factores.sort(key=lambda x: x['importancia'], reverse=True)
        
        # Generar razon principal
        factor_principal = factores[0]
        
        if factor_principal['factor'] == 'Temperatura':
            if temp > 30:
                razon = f"La temperatura elevada ({temp}°C) es el principal factor de riesgo."
            elif temp < 15:
                razon = f"La temperatura baja ({temp}°C) puede afectar el rendimiento."
            else:
                razon = f"La temperatura actual ({temp}°C) esta dentro de rangos normales."
        elif factor_principal['factor'] == 'Corriente':
            if abs(corriente) > 5:
                razon = f"La corriente ({corriente}A) supera los niveles seguros."
            else:
                razon = f"La corriente ({corriente}A) esta en niveles normales."
        else:
            if humidity > 70:
                razon = f"La humedad elevada ({humidity}%) puede causar problemas."
            else:
                razon = f"La humedad actual ({humidity}%) esta en niveles aceptables."
        
        # <CHANGE> Agregar info del equipo
        eq_id = current.get('sensor_id', 'Desconocido')
        equipo_nombre = eq_id
        if eq_id == 'ESP32_001':
            equipo_nombre = 'Laptop RRHH'
        elif eq_id == 'ESP32_002':
            equipo_nombre = 'Laptop Contabilidad'
        
        return jsonify({
            'razon_principal': razon,
            'factores_influyentes': factores,
            'equipo_id': eq_id,
            'equipo_nombre': equipo_nombre
        })
        
    except Exception as e:
        print(f"[Error Explicacion] {str(e)}")
        return jsonify({'error': str(e)}), 500
    

@app.route('/api/alertas', methods=['GET'])
def get_alertas():
    """Obtiene las alertas activas del sistema"""
    try:
        alertas = models.get_recent_alerts(limit=10)
        
        return jsonify({
            'alertas': alertas
        })
        
    except Exception as e:
        print(f"[Error Alertas] {str(e)}")
        return jsonify({'error': str(e)}), 500
    



@app.route('/api/alertas/<int:alerta_id>/estado', methods=['PUT'])
def update_alert_status(alerta_id):
    """Actualiza el estado de una alerta (solo para admin/TI)"""
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        notas = data.get('notas', '')
        
        print(f"[Alertas] Actualizando alerta {alerta_id} a estado: {nuevo_estado}")
        
        result = models.update_alert_status(alerta_id, nuevo_estado, notas)
        
        if result:
            return jsonify({'success': True, 'message': 'Alerta actualizada'})
        else:
            return jsonify({'success': False, 'message': 'Error actualizando alerta'}), 500
            
    except Exception as e:
        print(f"[Error Actualizar Alerta] {str(e)}")
        return jsonify({'error': str(e)}), 500


# Reemplazar el endpoint /api/alertas/todas con este:
@app.route('/api/alertas/todas', methods=['GET'])
def get_all_alerts():
    """Obtiene todas las alertas, filtradas por equipo si se especifica"""
    try:
        equipo_id = request.args.get('equipo_id')  # <CHANGE> Agregar filtro por equipo
        
        connection = models.get_db_connection()
        if not connection:
            return jsonify({'error': 'No hay conexion'}), 500
        
        with connection.cursor() as cursor:
            sql = """
                SELECT a.id, a.prediccion_id, a.tipo, a.mensaje, a.severidad, 
                       a.timestamp, a.leida, a.estado, a.notas, a.equipo_id
                FROM alertas a
                WHERE 1=1
            """
            params = []
            
            # <CHANGE> Filtrar por equipo si se especifica
            if equipo_id:
                sql += " AND a.equipo_id = %s"
                params.append(equipo_id)
            
            sql += " ORDER BY a.timestamp DESC LIMIT 50"
            
            cursor.execute(sql, params if params else None)
            alertas = cursor.fetchall()
        
        connection.close()
        
        formatted_alerts = []
        for a in alertas:
            # <CHANGE> Obtener nombre del equipo
            eq_id = a.get('equipo_id', 'Desconocido')
            equipo_nombre = eq_id
            if eq_id == 'ESP32_001':
                equipo_nombre = 'Laptop RRHH'
            elif eq_id == 'ESP32_002':
                equipo_nombre = 'Laptop Contabilidad'
            elif eq_id == 'ESP32_003':
                equipo_nombre = 'Laptop Administracion'
            
            formatted_alerts.append({
                'id': a['id'],
                'tipo': a.get('tipo', ''),
                'mensaje': a.get('mensaje', ''),
                'severidad': a.get('severidad', ''),
                'timestamp': a['timestamp'].isoformat() if a.get('timestamp') else None,
                'estado': a.get('estado', 'pendiente'),
                'notas': a.get('notas', ''),
                'leida': a.get('leida', False),
                'equipo_id': eq_id,
                'equipo_nombre': equipo_nombre
            })
        
        return jsonify({'alertas': formatted_alerts})
        
    except Exception as e:
        print(f"[Error Todas Alertas] {str(e)}")
        return jsonify({'error': str(e)}), 500




# =============================================
# ENDPOINTS PARA MULTI-EQUIPO
# =============================================

@app.route('/api/ingest/v2', methods=['POST'])
def ingest_data_v2():
    """Recibe datos del ESP32 con ID de equipo"""
    try:
        data = request.get_json()
        
        # Obtener equipo_id del request (obligatorio en v2)
        equipo_id = data.get('equipo_id', 'ESP32_001')
        temperature = float(data.get('temperature', 0))
        humidity = float(data.get('humidity', 0))
        current = float(data.get('current', 0))
        
        print(f"[Equipo: {equipo_id}] Temp: {temperature}°C, Hum: {humidity}%, Corriente: {current}A")
        
        # Usar funciones multi-equipo
        reading_id = models.insert_sensor_reading_multi(equipo_id, temperature, humidity, current)
        
        if not reading_id:
            return jsonify({'error': 'Error guardando datos'}), 500
        
        prediction = predictor.make_prediction(temperature, humidity, current)
        
        prediction_id = models.insert_prediction_multi(
            reading_id,
            equipo_id,
            prediction['risk_level'],
            prediction['failure_probability'],
            prediction['influential_factors']
        )
        
        alerts = predictor.check_alerts(
            temperature, humidity, current, prediction['risk_level']
        )
        
        for alert in alerts:
            models.insert_alert_multi(
                prediction_id,
                equipo_id,
                alert['type'],
                alert['message'],
                alert['severity']
            )
        
        # Auto-resolver alertas si valores normales
        models.auto_resolve_alerts(temperature, current)
        
        print(f"[{equipo_id}] Riesgo: {prediction['risk_level']} ({prediction['failure_probability']*100:.1f}%)")
        
        return jsonify({
            'success': True,
            'equipo_id': equipo_id,
            'reading_id': reading_id,
            'prediction': prediction,
            'alerts': alerts
        })
        
    except Exception as e:
        import traceback
        print("\n\n========== ERROR EN /api/ingest/v2 ==========")
        print(traceback.format_exc())   # <-- ESTO SI MUESTRA EL ERROR REAL
        print("===========================================\n\n")
        return jsonify({'error': str(e)}), 500



@app.route('/api/equipos/todos', methods=['GET'])
def get_all_equipos():
    """Obtiene todos los equipos con su estado actual (para TI)"""
    try:
        equipos = models.get_all_equipos()
        
        result = []
        for eq in equipos:
            # Obtener estado actual del equipo
            status = models.get_equipo_status(eq['equipo_id'])
            
            equipo_data = {
                'id': eq['id'],
                'equipo_id': eq['equipo_id'],
                'nombre': eq['nombre'],
                'ubicacion': eq['ubicacion'],
                'area': eq['area'],
                'operador': eq.get('operador_nombre', 'Sin asignar'),
                'alertas_activas': eq.get('alertas_activas', 0),
                'ultima_conexion': eq['ultima_conexion'].isoformat() if eq.get('ultima_conexion') else None,
                'activo': eq['activo']
            }
            
            # Agregar datos de sensores si hay lectura reciente
            if status and status.get('lectura'):
                lectura = status['lectura']
                equipo_data['temperatura'] = lectura.get('temperatura')
                equipo_data['humedad'] = lectura.get('humedad')
                equipo_data['corriente'] = lectura.get('corriente')
                equipo_data['nivel_riesgo'] = lectura.get('nivel_riesgo', 'unknown')
                equipo_data['riesgo_predicho'] = lectura.get('riesgo_predicho', 0)
                
                # Determinar si esta online (ultima lectura < 30 segundos)
                if lectura.get('timestamp'):
                    from datetime import datetime, timedelta
                    ahora = datetime.now()
                    ultima = lectura['timestamp']
                    equipo_data['online'] = (ahora - ultima).total_seconds() < 30
                else:
                    equipo_data['online'] = False
            else:
                equipo_data['online'] = False
                equipo_data['temperatura'] = None
                equipo_data['humedad'] = None
                equipo_data['corriente'] = None
                equipo_data['nivel_riesgo'] = 'unknown'
                equipo_data['riesgo_predicho'] = 0
            
            result.append(equipo_data)
        
        return jsonify({'equipos': result})
        
    except Exception as e:
        print(f"[Error Equipos] {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/equipos/<equipo_id>', methods=['GET'])
def get_equipo_detail(equipo_id):
    """Obtiene el detalle de un equipo especifico"""
    try:
        status = models.get_equipo_status(equipo_id)
        
        if not status:
            return jsonify({'error': 'Equipo no encontrado'}), 404
        
        return jsonify(status)
        
    except Exception as e:
        print(f"[Error Equipo Detail] {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/equipos/registrar', methods=['POST'])
def registrar_equipo():
    """Registra un nuevo equipo"""
    try:
        data = request.get_json()
        
        equipo_id = data.get('equipo_id')
        nombre = data.get('nombre')
        ubicacion = data.get('ubicacion', 'UGEL Lambayeque')
        area = data.get('area')
        operador_id = data.get('operador_id')
        
        if not equipo_id or not nombre:
            return jsonify({'error': 'equipo_id y nombre son requeridos'}), 400
        
        result = models.registrar_equipo(equipo_id, nombre, ubicacion, area, operador_id)
        
        if result:
            return jsonify({'success': True, 'message': 'Equipo registrado'})
        else:
            return jsonify({'error': 'Error registrando equipo'}), 500
            
    except Exception as e:
        print(f"[Error Registrar Equipo] {str(e)}")
        return jsonify({'error': str(e)}), 500



if __name__ == '__main__':
    print("=" * 50)
    print("SERVIDOR BACKEND IoT PREDICTIVO")
    print("=" * 50)
    print("Modo de ejecución: LOCAL")
    print(f"Servidor local: http://{SERVER_CONFIG['host']}:{SERVER_CONFIG['port']}")
    print("=" * 50)

    app.run(
        host=SERVER_CONFIG['host'],
        port=SERVER_CONFIG['port'],
        debug=SERVER_CONFIG['debug']
    )

















