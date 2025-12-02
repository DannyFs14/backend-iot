from datetime import datetime
from config import THRESHOLDS

def make_prediction(temperature, humidity, current):
    """Hace una prediccion basada en los datos de los sensores"""
    
    # Calcular nivel de riesgo y probabilidad
    risk_level, failure_probability = calculate_risk_level(temperature, humidity, current)
    
    # Determinar factores influyentes
    influential_factors = identify_influential_factors(temperature, humidity, current)
    
    return {
        'risk_level': risk_level,
        'failure_probability': failure_probability,
        'influential_factors': influential_factors,
        'timestamp': datetime.now().isoformat()
    }


def calculate_risk_level(temperature, humidity, current):
    """Calcula el nivel de riesgo basado en umbrales"""
    
    # Contar cuantos factores estan en zona critica o warning
    factores_criticos = 0
    factores_warning = 0
    
    # Temperatura
    if temperature >= 45:  # Critico
        factores_criticos += 1
    elif temperature >= 35:  # Warning
        factores_warning += 1
    
    # Humedad
    if humidity >= 85:  # Critico
        factores_criticos += 1
    elif humidity >= 70:  # Warning
        factores_warning += 1
    
    # Corriente
    if abs(current) >= 10:  # Critico
        factores_criticos += 1
    elif abs(current) >= 5:  # Warning
        factores_warning += 1
    
    # Determinar nivel de riesgo
    if factores_criticos >= 2:
        return 'critico', 100.0
    elif factores_criticos >= 1:
        return 'alto', 80.0
    elif factores_warning >= 2:
        return 'medio', 50.0
    elif factores_warning >= 1:
        return 'bajo', 20.0
    else:
        return 'bajo', 5.0


def identify_influential_factors(temperature, humidity, current):
    """Identifica los factores mas influyentes"""
    factors = []
    
    if temperature > THRESHOLDS['temperature_max']:
        factors.append('Temperatura elevada')
    
    if humidity > THRESHOLDS['humidity_max']:
        factors.append('Humedad elevada')
    
    if abs(current) > THRESHOLDS['current_max']:
        factors.append('Corriente elevada')
    
    if not factors:
        factors.append('Condiciones normales')
    
    return ', '.join(factors)


def check_alerts(temperature, humidity, current, risk_level):
    """Verifica si se deben generar alertas"""
    alerts = []
    
    # Alerta por temperatura
    if temperature >= 45:
        alerts.append({
            'type': 'temperature',
            'message': f'Temperatura critica: {temperature}°C',
            'severity': 'critico'
        })
    elif temperature >= 35:
        alerts.append({
            'type': 'temperature',
            'message': f'Temperatura elevada: {temperature}°C',
            'severity': 'advertencia'
        })
    
    # Alerta por humedad
    if humidity >= 85:
        alerts.append({
            'type': 'humidity',
            'message': f'Humedad critica: {humidity}%',
            'severity': 'critico'
        })
    elif humidity >= 70:
        alerts.append({
            'type': 'humidity',
            'message': f'Humedad elevada: {humidity}%',
            'severity': 'advertencia'
        })
    
    # Alerta por corriente
    if abs(current) >= 10:
        alerts.append({
            'type': 'current',
            'message': f'Corriente critica: {current}A',
            'severity': 'critico'
        })
    elif abs(current) >= 5:
        alerts.append({
            'type': 'current',
            'message': f'Corriente elevada: {current}A',
            'severity': 'advertencia'
        })
    
    # Alerta por nivel de riesgo general
    if risk_level == 'critico':
        alerts.append({
            'type': 'system',
            'message': 'Sistema en estado critico - Revision inmediata requerida',
            'severity': 'critico'
        })
    elif risk_level == 'alto':
        alerts.append({
            'type': 'system',
            'message': 'Riesgo alto detectado - Monitoreo cercano recomendado',
            'severity': 'advertencia'
        })
    
    return alerts