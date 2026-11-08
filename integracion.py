#===========================
# Integracion.py
#
#  fuente 1 -Maria-: users, emocion_conjunto, emocion_especifica
#  fuente 2 -mondongo- moodsitto_nosql.trackeo_emocional
#  
#  users.id_user ==== trackeo_emocional.id_user
#
#===========================

#librerias
import json
import pymysql
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

# configuracion de conexion
maria_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '1234',  # ajustar a la contraseña del equipo
    'database': 'moodsitto',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

mongo_uri = "mongodb://127.0.0.1:27017/"
mongo_db  = "moodsitto_nosql"
mongo_col = "trackeo_emocional"


def consultar_mariadb():
    """Consultar a maria usuarios y emocion especifica"""
    conn = pymysql.connect(**maria_config)
    try:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT
                u.id_user,
                CONCAT(u.name, ' ', u.lastname1) AS nombre_completo,
                ee.nombre AS emocion_especifica,
                ec.id_emocion_conjun AS id_conjunto
            FROM users u
            JOIN emocion_conjunto ec ON 1=1
            JOIN emocion_especifica ee ON ee.id_emo_espe = ec.id_emo_espe
            LIMIT 10
            """)
            return cur.fetchall()
    finally:
        conn.close()


def consultar_mongodb(id_user):
    """consultar en mondongo registros de trackeos de un usuario"""
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
    # checar la conexion y cerrarla si mondongo no quiere chambear
    client.admin.command('ping')
    col = client[mongo_db][mongo_col]
    docs = list(col.find({"id_user": int(id_user)}).sort('fecha_hora', -1))

    # convertir ObjectId y datetime a tipo serial (chococrispis)
    for d in docs:
        d['_id'] = str(d['_id'])
        if 'fecha_hora' in d:
            d['fecha_hora'] = d['fecha_hora'].strftime('%Y-%m-%d %H:%M:%S')
    return docs


def main():
    # fuente maria
    try:
        usuarios = consultar_mariadb()
    except Exception as e:
        print(json.dumps({
            "completo": False,
            "warning": "mariadb no chambea: " + str(e)
        }, ensure_ascii=False, indent=2))
        return

    # Fuente mondongo y union
    resultado = []
    error_mongo = None

    try:
        for u in usuarios:
            trackeos = consultar_mongodb(u['id_user'])
            resultado.append({
                "usuario": u["nombre_completo"],
                "emocion": u["emocion_especifica"],
                "trackeos": trackeos
            })
    except ServerSelectionTimeoutError as e:
        error_mongo = "Mondongo no quiere chambear"
    except Exception as e:
        error_mongo = "Error en mondongo: " + str(e)

    # salida
    if error_mongo:
        # no se devuelve [] ni se marca 0, integracion queda incompleta
        print(json.dumps({
            "completo": False,
            "warning": error_mongo,
            "datos_mariadb": usuarios,
            "trackeos": None
        }, ensure_ascii=False, indent=2, default=str))
    else:
        print(json.dumps({
            "completo": True,
            "datos": resultado
        }, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()