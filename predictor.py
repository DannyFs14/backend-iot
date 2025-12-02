import numpy as np
from config import THRESHOLDS

def calculate_risk_score(temperature, humidity, current):
    """
    Calcula el puntaje de riesgo basado en los valores de sensores
    Retorna un valor entre 0 (sin riesgo) y 1 (riesgo crítico)
    """
    # Normalizar valores
    temp_norm = min(temperature / THRESHOLDS['temperature_max'], 1.5)
    humidity_norm = min(humidity / THRESHOLDS['humidity_max'], 1.5)
    current_norm = min(abs(current) / THRESHOLDS['current_max'], 1.5)
    
    # Pesos para cada factor
    weights = {
        'temperature': 0.35,
        'humidity': 0.25,
        'current': 0.40
    }
    
    # Calcular riesgo ponderado
    risk_score = (
        temp_norm * weights['temperature'] +
        humidity_norm * weights['humidity'] +
        current_norm * weights['current']
    )
    
    # Limitar entre 0 y 1
    return min(max(risk_score, 0), 1)

def determine_risk_level(risk_score):
    """Determina el nivel de riesgo basado en el puntaje"""
    if risk_score >= THRESHOLDS['risk_critical']:
        return 'critical'
    elif risk_score >= THRESHOLDS['risk_high']:
        return 'high'
    elif risk_score >= 0.3:
        return 'medium'
    else:
        return 'low'

def calculate_influential_factors(temperature, humidity, current):
    """
    Calcula qué factores son más influyentes en el riesgo
    Retorna un string JSON con los porcentajes
    """
    import json
    
    # Calcular desviación de cada parámetro respecto al umbral
    temp_impact = min((temperature / THRESHOLDS['temperature_max']) * 100, 100)
    humidity_impact = min((humidity / THRESHOLDS['humidity_max']) * 100, 100)
    current_impact = min((abs(current) / THRESHOLDS['current_max']) * 100, 100)
    
    factors = {
        'Temperatura': round(temp_impact, 1),
        'Humedad': round(humidity_impact, 1),
        'Corriente': round(current_impact, 1)
    }
    
    return json.dumps(factors)

def make_prediction(temperature, humidity, current):
    """
    Realiza una predicción completa basada en los datos de sensores
    Retorna un diccionario con el nivel de riesgo, probabilidad y factores
    """
    risk_score = calculate_risk_score(temperature, humidity, current)
    risk_level = determine_risk_level(risk_score)
    factors = calculate_influential_factors(temperature, humidity, current)
    
    return {
        'risk_level': risk_level,
        'failure_probability': round(risk_score, 3),
        'influential_factors': factors
    }

def check_alerts(temperature, humidity, current, risk_level):
    """
    Verifica si se deben generar alertas basadas en los valores
    Retorna una lista de alertas
    """
    alerts = []
    
    if temperature > THRESHOLDS['temperature_max']:
        alerts.append({
            'type': 'high_temperature',
            'message': f'Temperatura crítica: {temperature}°C',
            'severity': 'critical'
        })
    
    if humidity > THRESHOLDS['humidity_max']:
        alerts.append({
            'type': 'high_humidity',
            'message': f'Humedad elevada: {humidity}%',
            'severity': 'warning'
        })
    
    if abs(current) > THRESHOLDS['current_max']:
        alerts.append({
            'type': 'high_current',
            'message': f'Corriente anormal: {current}A',
            'severity': 'critical'
        })
    
    if risk_level == 'critical':
        alerts.append({
            'type': 'system_failure_risk',
            'message': 'Riesgo crítico de fallo del sistema',
            'severity': 'critical'
        })
    
    return alerts