from flask import Flask, jsonify, request, render_template
import requests
import json
from bs4 import BeautifulSoup
from collections import defaultdict
import os

app = Flask(__name__, template_folder='templates')

nombres_sedes = {1: 'Virtual', 2: 'Juliaca', 3: 'Puno', 4: 'Juli-Chucuito', 5: 'Ayaviri', 6: 'Azángaro', 7: 'Huancané-Moho', 8: 'Ilave'}

nombres_areas = {1: 'Biomédicas', 2: 'Ingenierías', 3: 'Sociales'}
nombres_turnos = {1: 'Mañana', 2: 'Tarde', 3: 'Noche'}

def obtener_token(session):
    url = 'https://sistemas.cepreuna.edu.pe/login'
    respuesta = session.get(url)
    if respuesta.status_code != 200:
        print('Error al obtener el token CSRF.')
        return None

    soup = BeautifulSoup(respuesta.text, 'html.parser')
    token = soup.find('input', {'name': '_token'})['value']
    return token

def iniciar_sesion(session, email, password):
    token = obtener_token(session)
    if not token:
        return False

    url = 'https://sistemas.cepreuna.edu.pe/login'
    datos = {
        '_token': token,
        'email': email,
        'password': password
    }

    respuesta = session.post(url, data=datos)

    if respuesta.ok and respuesta.url != url:
        print('Inicio de sesión exitoso.')
        return True
    else:
        print('Error al iniciar sesión.')
        return False

def obtener_datos(session):
    todos_los_datos = []
    pagina = 1

    while True:
        url = f'https://sistemas.cepreuna.edu.pe/intranet/inscripcion/estudiante/lista/data?query=%7B%7D&limit=1000&ascending=1&page={pagina}&byColumn=1'
        respuesta = session.get(url)

        if respuesta.status_code != 200:
            print(f'Error al obtener datos de la página {pagina}.')
            break

        datos = respuesta.json()

        if not datos.get('data'):
            break

        todos_los_datos.extend(datos['data'])
        pagina += 1

    return todos_los_datos

def filtrar_datos_por_sede(datos, sede_filtro):
    if not sede_filtro:
        return datos
    return [registro for registro in datos if str(registro.get('sedes_id')) == sede_filtro]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/obtener_datos', methods=['GET'])
def obtener_datos_endpoint():
    email = "esflores@cepreuna.edu.pe"
    password = "46386459"
    sede_filtro = request.args.get('sede', None)

    with requests.Session() as session:
        if iniciar_sesion(session, email, password):
            datos = obtener_datos(session)
            datos_filtrados = filtrar_datos_por_sede(datos, sede_filtro)

            conteo_areas = defaultdict(int)
            conteo_turnos = defaultdict(lambda: defaultdict(int))

            for registro in datos_filtrados:
                area_nombre = nombres_areas.get(registro.get('areas_id'), 'Sin Área')
                turno_nombre = nombres_turnos.get(registro.get('turnos_id'), 'Sin Turno')

                conteo_areas[area_nombre] += 1
                conteo_turnos[area_nombre][turno_nombre] += 1

            total_inscritos = sum(conteo_areas.values())

            respuesta = {
                'total_inscritos': total_inscritos,
                'areas': dict(conteo_areas),
                'turnos': {area: dict(turnos) for area, turnos in conteo_turnos.items()}
            }

            return jsonify(respuesta)
        else:
            return jsonify({'error': 'No se pudo iniciar sesión'}), 401

if __name__ == '__main__':
    # Railway suele proveer el puerto en la variable de entorno PORT
    port = int(os.environ.get('PORT', 5000))
    # Para ver más detalles de errores, pon debug=True solo en desarrollo local
    app.run(host='0.0.0.0', port=port, debug=True)





















