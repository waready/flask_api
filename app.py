from flask import Flask, render_template, jsonify, request
import requests
import json
from bs4 import BeautifulSoup
import os

app = Flask(__name__)

def obtener_token(session):
    """
    Obtiene el token CSRF de la página de login.
    Lanza una excepción si no puede.
    """
    url = 'https://sistemas.cepreuna.edu.pe/login'
    try:
        respuesta = session.get(url, timeout=10)
        respuesta.raise_for_status()
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error al acceder a la URL de login: {e}", exc_info=True)
        raise

    soup = BeautifulSoup(respuesta.text, 'html.parser')
    token_input = soup.find('input', {'name': '_token'})
    if not token_input:
        app.logger.error("No se encontró el input '_token' en el formulario de login.")
        raise ValueError("No se encontró el token CSRF en la página de login.")

    return token_input.get('value')

def iniciar_sesion(session, email, password):
    """
    Inicia sesión en la plataforma CEPREUNA.
    Retorna True si el login es exitoso, False en caso contrario.
    """
    try:
        token = obtener_token(session)
    except Exception as e:
        app.logger.error(f"Error obteniendo token CSRF: {e}", exc_info=True)
        return False

    url = 'https://sistemas.cepreuna.edu.pe/login'
    datos = {
        '_token': token,
        'email': email,
        'password': password
    }

    try:
        respuesta = session.post(url, data=datos, timeout=10)
        respuesta.raise_for_status()
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error al hacer POST para iniciar sesión: {e}", exc_info=True)
        return False

    # Verificamos si realmente entró o se quedó en la misma URL
    if respuesta.ok and respuesta.url != url:
        app.logger.info('Inicio de sesión exitoso.')
        return True
    else:
        app.logger.warning('Credenciales inválidas o error de login.')
        return False

def obtener_datos(session):
    """
    Descarga todos los registros paginados de la plataforma CEPREUNA
    y los retorna como una lista de diccionarios.
    Lanza excepciones si hay errores en las peticiones.
    """
    todos_los_datos = []
    pagina = 1

    while True:
        endpoint = (
            "https://sistemas.cepreuna.edu.pe/intranet/inscripcion/estudiante"
            "/lista/data?query=%7B%7D&limit=1000&ascending=1"
            f"&page={pagina}&byColumn=1"
        )
        try:
            respuesta = session.get(endpoint, timeout=10)
            respuesta.raise_for_status()
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error al obtener datos de la página {pagina}: {e}", exc_info=True)
            break

        datos_json = respuesta.json()
        # Si 'data' está vacío, significa que no hay más páginas
        data_pagina = datos_json.get('data', [])
        if not data_pagina:
            break

        todos_los_datos.extend(data_pagina)
        pagina += 1

    return todos_los_datos

@app.route('/')
def index():
    """
    Ruta principal que renderiza 'Index.html'.
    Asegúrate de tener un templates/Index.html para que funcione.
    """
    return render_template('index.html')

@app.route('/obtener_sedes', methods=['GET'])
def obtener_sedes():
    """
    Endpoint que:
      - Inicia sesión (credenciales fijas, ajústalas si es necesario).
      - Descarga datos paginados.
      - Filtra opcionalmente por 'sedes_id' usando ?sede=...
      - Retorna un JSON con los registros resultantes.
    """
    email = "esflores@cepreuna.edu.pe"   # Ajusta si hace falta
    password = "46386459"               # Ajusta si hace falta

    sede_filtro = request.args.get('sede', None)

    try:
        with requests.Session() as session:
            # Iniciamos sesión
            if not iniciar_sesion(session, email, password):
                return jsonify({'error': 'No se pudo iniciar sesión'}), 401

            # Obtenemos todos los datos
            datos = obtener_datos(session)

            # Procesamos y filtramos
            datos_procesados = []
            for registro in datos:
                # Si se especificó ?sede=xx, filtramos por sedes_id
                if sede_filtro and str(registro.get('sedes_id')) != sede_filtro:
                    continue

                # Obtenemos programa (o "Sin Programa" si no existe)
                programa = registro.get('programa', 'Sin Programa')

                # Si existe la clave 'sede' y 'denominacion' en el JSON:
                # sede_obj = registro.get('sede', {})
                # denominacion = sede_obj.get('denominacion', 'Desconocida')
                #
                # Pero si solo necesitas 'programa', puedes ignorar esto.

                # Agregamos el resultado final a la lista
                datos_procesados.append({
                    'sede': registro.get('sedes_id'),
                    'programa': (registro.get('sede') or {}).get('denominacion', 'Sin Denominación')
                })


            return jsonify(datos_procesados)

    except Exception as e:
        # Cualquier error no controlado
        app.logger.error(f"Error interno en /obtener_sedes: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Railway suele proveer el puerto en la variable de entorno PORT
    port = int(os.environ.get('PORT', 5000))
    # Para ver más detalles de errores, pon debug=True solo en desarrollo local
    app.run(host='0.0.0.0', port=port, debug=True)
