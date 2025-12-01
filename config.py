import os

DB_CONFIG = {
    'host': os.getenv('MYSQLHOST', 'localhost'),
    'user': os.getenv('MYSQLUSER', 'root'),
    'password': os.getenv('MYSQLPASSWORD', ''),
    'database': os.getenv('MYSQLDATABASE', 'iot_predictivo'),
    'port': int(os.getenv('MYSQLPORT', 3306))
}

SERVER_CONFIG = {
    'host': '0.0.0.0',
    'port': int(os.getenv('PORT', 5000)),
    'debug': False
}


# Umbrales de alerta
THRESHOLDS = {
    'temperature_max': 35.0,  # °C
    'humidity_max': 80.0,     # %
    'current_max': 15.0,      # A
    'risk_critical': 0.7,     # 70% de probabilidad de fallo
    'risk_high': 0.5          # 50% de probabilidad de fallo
}

