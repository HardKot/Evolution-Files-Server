from datetime import timedelta, date
from os import remove, environ, getcwd, chdir, mkdir
from mutagen.mp3 import MP3
import uuid
from functools import wraps
from os.path import exists, join, expanduser
from flask import Flask, jsonify, send_file, request
import psycopg2
from firebase_admin import auth, credentials
import firebase_admin
import validators


firebase_admin.initialize_app(credentials.Certificate(
    join(expanduser('~'), 'firebase_key.json')))


def connect_data_base():
    connect_data_base = psycopg2.connect(dbname=environ.get(
        'DATABASE_NAME'), user=environ.get(
        'DATABASE_NAME'), password=environ.get('DATABASE_PASSWORD'), host='localhost')
    cursor = connect_data_base.cursor()

    return connect_data_base, cursor


app = Flask(__name__)


def only_main_server(func):
    @wraps(func)
    def _wrapper(*args, **kwargs):
        if request.headers.get('Authorization', None) == environ.get('key'):
            return func(*args, **kwargs)
        return '', 403
    return _wrapper


def get_user_data(func):
    @wraps(func)
    def _wrapper(*args, **kwargs):
        token = request.headers.get('Authorization', None)
        user = None
        try:
            if token is not None:
                user_id = auth.verify_id_token(token)
                connect, cursor = connect_data_base()
                cursor.execute(
                    'SELECT "Id", "PhotoId" FROM "Users" WHERE "Id"=%s', (user_id, ))
                result = cursor.fetchone()
                if result is not None:
                    user = {
                        'id': None,
                        'imageId': None,
                        'subscribe': None
                    }
                    user['id'] = result[0]
                    user['imageId'] = result[1]
                    user['subscribe'] = False
                    cursor.execute(
                        'SELECT "WhenSubscribe", "Type" FROM "Subscribes" WHERE "UserId"=%s ORDER BY "WhenSubscribe" LIMIT 1', (user_id, ))
                    result = cursor.fetchone()
                    if result is not None:
                        end_subscriber = result[0]
                        count_day_subscribe = 0
                        if result[1] == 'Week':
                            count_day_subscribe = 7
                        elif result[1] == 'Month':
                            count_day_subscribe = 30
                        elif result[1] == 'Month6':
                            count_day_subscribe = 180
                        end_subscriber += timedelta(days=count_day_subscribe)
                        if end_subscriber >= date.today():
                            user['subscribe'] = True
                cursor.close()
                connect.close()
        except ValueError:
            return '', 400
        except auth.InvalidIdTokenError:
            return '', 400
        except auth.ExpiredIdTokenError:
            return '', 400
        except auth.RevokedIdTokenError:
            return '', 400
        except auth.CertificateFetchError:
            return '', 400
        except auth.UserDisabledError:
            return '', 400
        else:
            return func(user=user, *args, **kwargs)
    return _wrapper


def get_meditation_data(meditation_id, language='ru'):
    meditation = None
    connect, cursor = connect_data_base()
    cursor.execute(
        'SELECT "Id", "PhotoId", "IsSubscribed", "AudioId" FROM "Meditations" WHERE "Id"=%s AND "Language"=%s', (meditation_id, language))
    result = cursor.fetchone()
    if result is not None:
        meditation = {}
        meditation['Id'] = result[0]
        meditation['PhotoId'] = result[1]
        meditation['IsSubscribe'] = result[2]
        meditation['AudioId'] = result[3]
    cursor.close()
    connect.close()
    return meditation


def check_or_create_folder(func):
    @wraps(func)
    def _wrapper(*args, **kwargs):
        work_dir = getcwd()
        chdir('~')
        if not exists(join(expanduser('~'), 'media')):
            mkdir('media')
            chdir('~/media')
            mkdir('image')
            mkdir('audio')
        else:
            if not exists(join(expanduser('~'), 'media/image')):
                chdir('~/media')
                mkdir('image')
            if not exists(join(expanduser('~'), 'media/audio')):
                chdir('~/media')
                mkdir('audio')
        chdir(work_dir)
        return func(*args, **kwargs)
    return _wrapper


def write_log(func):
    @wraps(func)
    def _wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            app.logger.error(f'{request.method: request.url}, {exc}')
            return '', 500
    return _wrapper


@app.route('/image/<image_id>')
@write_log
def get_image_by_id(image_id):
    return return_if_exists(join('image', f'{image_id}.png'))


@app.route('/meditation.audio/<meditation_id>', methods=['GET'])
@get_user_data
@write_log
def get_meditation_audio(user, meditation_id):
    if not validators.uuid(meditation_id):
        return '', 404
    meditation = get_meditation_data(meditation_id)
    if meditation is None:
        return '', 404

    if meditation['IsSubscribe'] and (user is None or user['subscribe'] is False):
        return '', 402
    return return_if_exists(join('audio', f'{meditation["AudioId"]}.mp3'))


@app.route('/image', methods=['POST'])
@only_main_server
@check_or_create_folder
@write_log
def post_image():
    image_id = uuid.uuid4()
    with open(join(expanduser('~'), 'media', 'image', f'{image_id}.png'), 'bw') as image:
        image.write(request.get_data())
    return jsonify({'imageId': f'{image_id}'})


@app.route('/image/<image_id>', methods=['PUT'])
@only_main_server
@check_or_create_folder
@write_log
def put_image(image_id):
    if not validators.uuid(image_id):
        return '', 404
    if exists(join(expanduser('~'), 'media', 'image', f'{image_id}.png')):
        remove(join(expanduser('~'), 'media', 'image', f'{image_id}.png'))
    image_id = uuid.uuid4()
    with open(join(expanduser('~'), 'media', 'image', f'{image_id}.png'), 'bw') as image:
        image.write(request.get_data())
    return jsonify({'imageId': f'{image_id}'})


@app.route('/meditation.audio', methods=['POST'])
@only_main_server
@check_or_create_folder
@write_log
def post_audio():
    audio_id = uuid.uuid4()
    with open(join(expanduser('~'), 'media', 'audio', f'{audio_id}.mp3'), 'bw') as audio:
        audio.write(request.get_data())
    len_audio = MP3((join(expanduser('~'), 'media',
                          'audio', f'{audio_id}.mp3'))).info.length
    return jsonify({'audioId': f'{audio_id}', 'length': len_audio})


def return_if_exists(uri):
    if exists(join(expanduser('~'), 'media', uri)):
        return send_file(join(expanduser('~'), 'media', uri))
    else:
        return '', 404
