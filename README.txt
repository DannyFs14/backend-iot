============================================
BACKEND IoT PREDICTIVO - INSTRUCCIONES
============================================

INSTALACIÓN:
1. Abre CMD o PowerShell en esta carpeta
2. Instala las dependencias:
   pip install -r requirements.txt

EJECUTAR EL SERVIDOR:
   python app.py

VERIFICAR QUE FUNCIONA:
   Abre tu navegador en: http://localhost:5000/health
   Deberías ver: {"status":"ok","message":"Backend funcionando correctamente"}

CONFIGURACIÓN:
   - Edita config.py si necesitas cambiar usuario/contraseña de MySQL
   - Por defecto usa Laragon (root sin contraseña)

ESTRUCTURA:
   - app.py: Servidor principal
   - models.py: Conexión a MySQL y funciones de base de datos
   - predictor.py: Lógica de predicción y alertas
   - config.py: Configuración