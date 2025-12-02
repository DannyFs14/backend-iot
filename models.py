import pymysql
from config import DB_CONFIG
from datetime import datetime

def get_db_connection():
    """Crea y retorna una conexión a MySQL"""
    try:
        connection = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            port=DB_CONFIG['port'],
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"Error conectando a MySQL: {e}")
        return None

def insert_sensor_reading(temperature, humidity, current):
    """Guarda una lectura de sensores en la base de datos"""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO lecturas_sensores (sensor_id, temperatura, humedad, corriente, timestamp)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, ('ESP32_001', temperature, humidity, current, datetime.now()))
            connection.commit()
            return cursor.lastrowid
    except Exception as e:
        print(f"Error insertando lectura: {e}")
        return None
    finally:
        connection.close()

def insert_prediction(reading_id, risk_level, failure_probability, factors):
    """Guarda una predicción en la base de datos"""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO predicciones (lectura_id, nivel_riesgo, riesgo_predicho, 
                                       factores, timestamp)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (reading_id, risk_level, failure_probability, 
                                factors, datetime.now()))
            connection.commit()
            return cursor.lastrowid
    except Exception as e:
        print(f"Error insertando predicción: {e}")
        return None
    finally:
        connection.close()

def insert_alert(prediction_id, alert_type, message, severity):
    """Guarda una alerta en la base de datos"""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO alertas (prediccion_id, tipo, mensaje, severidad, 
                                  timestamp, leida)
                VALUES (%s, %s, %s, %s, %s, FALSE)
            """
            cursor.execute(sql, (prediction_id, alert_type, message, severity, 
                                datetime.now()))
            connection.commit()
            return cursor.lastrowid
    except Exception as e:
        print(f"Error insertando alerta: {e}")
        return None
    finally:
        connection.close()

def get_latest_readings(limit=10):
    """Obtiene las últimas lecturas de sensores"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT r.*, p.nivel_riesgo, p.riesgo_predicho
                FROM lecturas_sensores r
                LEFT JOIN predicciones p ON r.id = p.lectura_id
                ORDER BY r.timestamp DESC
                LIMIT %s
            """
            cursor.execute(sql, (limit,))
            return cursor.fetchall()
    except Exception as e:
        print(f"Error obteniendo lecturas: {e}")
        return []
    finally:
        connection.close()

def get_active_alerts():
    """Obtiene las alertas activas"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT * FROM alertas
                WHERE leida = FALSE
                ORDER BY timestamp DESC
                LIMIT 50
            """
            cursor.execute(sql)
            return cursor.fetchall()
    except Exception as e:
        print(f"Error obteniendo alertas: {e}")
        return []
    finally:
        connection.close()



def authenticate_user(email, password):
    """Autentica un usuario y obtiene su equipo asignado"""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        with connection.cursor() as cursor:
            # <CHANGE> Hacer JOIN con equipos para obtener equipo_id
            sql = """
                SELECT u.*, e.equipo_id 
                FROM usuarios u
                LEFT JOIN equipos e ON e.operador_id = u.id
                WHERE u.email = %s AND u.password_hash = %s
            """
            print(f"[Auth] Buscando usuario: {email}")
            cursor.execute(sql, (email, password))
            user = cursor.fetchone()
            if user:
                print(f"[Auth] Usuario encontrado: {user['nombre']}, Equipo: {user.get('equipo_id')}")
                return {
                    'id': user['id'],
                    'name': user['nombre'],
                    'email': user['email'],
                    'role': user['rol'],
                    'equipo_id': user.get('equipo_id')  # <CHANGE> Incluir equipo_id
                }
            print(f"[Auth] Usuario no encontrado o contraseña incorrecta")
            return None
    except Exception as e:
        print(f"Error autenticando usuario: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        connection.close()





def get_filtered_readings(start_date=None, end_date=None):
    """Obtiene lecturas filtradas por fecha"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT r.*, p.nivel_riesgo, p.riesgo_predicho
                FROM lecturas_sensores r
                LEFT JOIN predicciones p ON r.id = p.lectura_id
            """
            params = []
            conditions = []
            
            if start_date:
                conditions.append("r.timestamp >= %s")
                params.append(start_date + ' 00:00:00')
            
            if end_date:
                conditions.append("r.timestamp <= %s")
                params.append(end_date + ' 23:59:59')
            
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            
            sql += " ORDER BY r.timestamp DESC LIMIT 500"
            
            print(f"[SQL] {sql}")
            print(f"[Params] {params}")
            
            cursor.execute(sql, params if params else None)
            results = cursor.fetchall()
            
            print(f"[Resultados] {len(results)} registros encontrados")
            
            return results
    except Exception as e:
        print(f"Error obteniendo lecturas filtradas: {e}")
        return []
    finally:
        connection.close()

def get_recent_alerts(limit=10):
    """Obtiene las alertas más recientes"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT id, prediccion_id, tipo, mensaje, severidad, 
                       timestamp, leida
                FROM alertas
                WHERE leida = FALSE
                ORDER BY timestamp DESC
                LIMIT %s
            """
            cursor.execute(sql, (limit,))
            return cursor.fetchall()
    except Exception as e:
        print(f"Error obteniendo alertas: {e}")
        return []
    finally:
        connection.close()


def update_alert_status(alert_id, status, notes=''):
    """Actualiza el estado de una alerta"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        with connection.cursor() as cursor:
            sql = """
                UPDATE alertas 
                SET estado = %s, notas = %s, leida = %s
                WHERE id = %s
            """
            leida = status in ['resuelto', 'en_proceso']
            cursor.execute(sql, (status, notes, leida, alert_id))
            connection.commit()
            print(f"[DB] Alerta {alert_id} actualizada a estado: {status}")
            return True
    except Exception as e:
        print(f"Error actualizando alerta: {e}")
        return False
    finally:
        connection.close()


def get_all_alerts(limit=50):
    """Obtiene todas las alertas (incluyendo leídas)"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT id, prediccion_id, tipo, mensaje, severidad, 
                       timestamp, leida, estado, notas
                FROM alertas
                ORDER BY timestamp DESC
                LIMIT %s
            """
            cursor.execute(sql, (limit,))
            return cursor.fetchall()
    except Exception as e:
        print(f"Error obteniendo todas las alertas: {e}")
        return []
    finally:
        connection.close()




def auto_resolve_alerts(temperature, current):
    """Resuelve alertas automaticamente cuando los valores vuelven a la normalidad"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        # Umbrales normales
        TEMP_MAX = 35.0
        CURRENT_MAX = 15.0
        
        # Si los valores estan normales, resolver alertas activas
        if temperature < TEMP_MAX and abs(current) < CURRENT_MAX:
            with connection.cursor() as cursor:
                sql = """
                    UPDATE alertas 
                    SET estado = 'resuelto', leida = TRUE
                    WHERE estado != 'resuelto' OR estado IS NULL
                """
                cursor.execute(sql)
                connection.commit()
                
                if cursor.rowcount > 0:
                    print(f"[Auto-Resolve] {cursor.rowcount} alertas resueltas automaticamente")
                return True
        return False
    except Exception as e:
        print(f"Error auto-resolviendo alertas: {e}")
        return False
    finally:
        connection.close()




def get_dashboard_alerts():
    """Obtiene alertas activas para el dashboard (no resueltas)"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        with connection.cursor() as cursor:
            # <CHANGE> Obtener alertas que NO estan resueltas
            sql = """
                SELECT id, prediccion_id, tipo, mensaje, severidad, 
                       timestamp, leida, estado, notas
                FROM alertas
                WHERE estado != 'resuelto' OR estado IS NULL
                ORDER BY timestamp DESC
                LIMIT 10
            """
            cursor.execute(sql)
            return cursor.fetchall()
    except Exception as e:
        print(f"Error obteniendo alertas dashboard: {e}")
        return []
    finally:
        connection.close()



# =============================================
# FUNCIONES PARA MULTI-EQUIPO
# =============================================

def get_all_equipos():
    """Obtiene todos los equipos registrados con su estado actual"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT 
                    e.id,
                    e.equipo_id,
                    e.nombre,
                    e.ubicacion,
                    e.area,
                    e.activo,
                    e.ultima_conexion,
                    u.nombre as operador_nombre,
                    u.email as operador_email,
                    (SELECT COUNT(*) FROM alertas a 
                     WHERE a.equipo_id = e.equipo_id 
                     AND a.estado != 'resuelto') as alertas_activas
                FROM equipos e
                LEFT JOIN usuarios u ON e.operador_id = u.id
                ORDER BY e.nombre
            """
            cursor.execute(sql)
            return cursor.fetchall()
    except Exception as e:
        print(f"Error obteniendo equipos: {e}")
        return []
    finally:
        connection.close()


def get_equipo_status(equipo_id):
    """Obtiene el estado actual de un equipo especifico"""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        with connection.cursor() as cursor:
            # Obtener ultima lectura del equipo
            sql = """
                SELECT 
                    ls.temperatura,
                    ls.humedad,
                    ls.corriente,
                    ls.timestamp,
                    p.nivel_riesgo,
                    p.riesgo_predicho
                FROM lecturas_sensores ls
                LEFT JOIN predicciones p ON ls.id = p.lectura_id
                WHERE ls.sensor_id = %s
                ORDER BY ls.timestamp DESC
                LIMIT 1
            """
            cursor.execute(sql, (equipo_id,))
            lectura = cursor.fetchone()
            
            # Obtener info del equipo
            sql_equipo = """
                SELECT e.*, u.nombre as operador_nombre
                FROM equipos e
                LEFT JOIN usuarios u ON e.operador_id = u.id
                WHERE e.equipo_id = %s
            """
            cursor.execute(sql_equipo, (equipo_id,))
            equipo = cursor.fetchone()
            
            # Contar alertas activas
            sql_alertas = """
                SELECT COUNT(*) as total
                FROM alertas
                WHERE equipo_id = %s AND estado != 'resuelto'
            """
            cursor.execute(sql_alertas, (equipo_id,))
            alertas = cursor.fetchone()
            
            if equipo:
                return {
                    'equipo': equipo,
                    'lectura': lectura,
                    'alertas_activas': alertas['total'] if alertas else 0
                }
            return None
    except Exception as e:
        print(f"Error obteniendo estado de equipo: {e}")
        return None
    finally:
        connection.close()


def update_equipo_conexion(equipo_id):
    """Actualiza la ultima conexion de un equipo"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        with connection.cursor() as cursor:
            sql = """
                UPDATE equipos 
                SET ultima_conexion = NOW()
                WHERE equipo_id = %s
            """
            cursor.execute(sql, (equipo_id,))
            connection.commit()
            return True
    except Exception as e:
        print(f"Error actualizando conexion: {e}")
        return False
    finally:
        connection.close()


def insert_sensor_reading_multi(equipo_id, temperature, humidity, current):
    """Guarda una lectura de sensores con ID de equipo"""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO lecturas_sensores (sensor_id, temperatura, humedad, corriente, timestamp)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (equipo_id, temperature, humidity, current, datetime.now()))
            connection.commit()
            
            # Actualizar ultima conexion del equipo
            update_equipo_conexion(equipo_id)
            
            return cursor.lastrowid
    except Exception as e:
        print(f"Error insertando lectura: {e}")
        return None
    finally:
        connection.close()


def insert_prediction_multi(reading_id, equipo_id, risk_level, failure_probability, factors):
    """Guarda una prediccion con ID de equipo"""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO predicciones (lectura_id, equipo_id, nivel_riesgo, riesgo_predicho, 
                                       factores, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (reading_id, equipo_id, risk_level, failure_probability, 
                                factors, datetime.now()))
            connection.commit()
            return cursor.lastrowid
    except Exception as e:
        print(f"Error insertando prediccion: {e}")
        return None
    finally:
        connection.close()


def insert_alert_multi(prediction_id, equipo_id, alert_type, message, severity):
    """Guarda una alerta con ID de equipo"""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO alertas (prediccion_id, equipo_id, tipo, mensaje, severidad, 
                                  timestamp, leida)
                VALUES (%s, %s, %s, %s, %s, %s, FALSE)
            """
            cursor.execute(sql, (prediction_id, equipo_id, alert_type, message, severity, 
                                datetime.now()))
            connection.commit()
            return cursor.lastrowid
    except Exception as e:
        print(f"Error insertando alerta: {e}")
        return None
    finally:
        connection.close()


def registrar_equipo(equipo_id, nombre, ubicacion, area=None, operador_id=None):
    """Registra un nuevo equipo en el sistema"""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO equipos (equipo_id, nombre, ubicacion, area, operador_id)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    nombre = VALUES(nombre),
                    ubicacion = VALUES(ubicacion),
                    area = VALUES(area),
                    operador_id = VALUES(operador_id)
            """
            cursor.execute(sql, (equipo_id, nombre, ubicacion, area, operador_id))
            connection.commit()
            return cursor.lastrowid
    except Exception as e:
        print(f"Error registrando equipo: {e}")
        return None
    finally:
        connection.close()