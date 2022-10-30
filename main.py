from datetime import timedelta, date
from os import remove, environ
from mutagen.mp3 import MP3
import uuid
from functools import wraps
from os.path import exists, join, expanduser, normpath
from flask import Flask, jsonify, send_file, request
import psycopg2
from firebase_admin import auth
import firebase_admin


default_app = firebase_admin.initialize_app()


def connect_data_base():
    connect_data_base = psycopg2.connect(dbname=environ.get('dbname'), user=environ.get(
        'userName'), password=environ.get('userPassword'), host=environ.get('databaseHost'))
    cursor = connect_data_base.cursor()

    return connect_data_base, cursor


app = Flask(__name__)


def only_main_server(func):
    @wraps(func)
    def _wrapper(*args, **kwargs):
        if request.headers.get('Authorization', None) == environ.get('serverKey'):
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
                    'SELECT `Id`, `PhotoId`,  FROM `Users` WHERE `Id`=?', (user_id, ))
                result = cursor.fetchone()
                if result is not None:
                    user['id'] = result[0]
                    user['imageId'] = result[1]
                    user['subscribe'] = False
                    cursor.execute(
                        'SELECT `WhenSubscribe`, `Type` FROM `Subscribes` WHERE `UserId`=? SORT BY `WhenSubscribe` LIMIT 1', (user_id, ))
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
        'SELECT `Id`, `PhotoId`, `IsSubscribe`, `AudioId` FROM `Meditations` WHERE `Id`=? AND `Language`=?', (meditation_id, language))
    result = cursor.fetchone()
    if result is not None:
        meditation = {}
        meditation['Id'] = result[0]
        meditation['PhotoId'] = result[1]
        meditation['IsSubscribe'] = result[2]
        meditation['AudioId'] = result[3]
        meditation['IsSubscribe'] = False
    cursor.close()
    connect.close()
    return meditation


@app.route('/')
def home():
    return 'Welcome!'


# @app.route('/users.image/<user_id>')
# @get_user_data
# def get_users_image(id):
#     if exists(f'./media/image/{id}.png'):
#         return send_file(f'./media/image/{id}.png')
#     else:
#         return '', 404


@app.route('/image/<image_id>')
def get_image_by_id(image_id):
    return return_if_exists(join('image', f'{image_id}.png'))


# @app.route('/audio/<audio_id>')
# @get_user_data
# def get_meditation_audio(user, audio_id):
#     meditation = get_meditation_data(audio_id)
#     if meditation is None:
#         return '', 404
#     if meditation['IsSubscribe'] and (user is None or user['subscribe'] is False):
#         return '', 402
#     return return_if_exists(join('audio', f'{audio_id}.mp3'))


# @app.route('/meditation.image/<meditation_id>')
# def get_meditation_image(meditation_id):
#     if exists(f'./media/image/{meditation_id}.png'):
#         return send_file(f'./media/image/{meditation_id}.png')
#     else:
#         return '', 404


@app.route('/meditation.audio/<meditation_id>')
@get_user_data
def get_meditation_audio(user, meditation_id):
    meditation = get_meditation_data(meditation_id)
    if meditation is None:
        return '', 404
    if meditation['IsSubscribe'] and (user is None or user['subscribe'] is False):
        return '', 402
    return return_if_exists(join('audio', f'{meditation["AudioId"]}.mp3'))


@app.route('/image', methods=['POST'])
@only_main_server
def post_image():
    if request.headers.get('Authorization', None) == environ.get('serverKey'):
        image_id = uuid.uuid4()
        with open(join(expanduser('~'), 'media', 'image', f'{image_id}.png'), 'bw') as image:
            image.write(request.get_data())
        return jsonify({'imageId': f'{image_id}'})
    return '', 403


@app.route('/image/<image_id>', methods=['PUT'])
@only_main_server
def put_image(image_id):
    if request.headers.get('Authorization', None) == environ.get('serverKey'):
        if exists(join(expanduser('~'), 'media', 'image', f'{image_id}.png')):
            remove(join(expanduser('~'), 'media', 'image', f'{image_id}.png'))
        image_id = uuid.uuid4()
        with open(join(expanduser('~'), 'media', 'image', f'{image_id}.png'), 'bw') as image:
            image.write(request.get_data())
        return jsonify({'imageId': f'{image_id}'})
    return '', 403


@app.route('/meditation.audio', methods=['POST'])
def post_audio():
    # environ.get('serverKey'):
    if request.headers.get('Authorization', None) == '12':
        audio_id = uuid.uuid4()
        print(audio_id, expanduser('~'))
        with open(join(expanduser('~'), 'media', 'audio', f'{audio_id}.mp3'), 'bw') as audio:
            audio.write(request.get_data())
        len_audio = MP3((join(expanduser('~'), 'media',
                        'audio', f'{audio_id}.mp3'))).info.length
        return jsonify({'audioId': f'{audio_id}', 'length': len_audio})
    return '', 403


def return_if_exists(uri):
    if exists(join(expanduser('~'), 'media', uri)):
        return send_file(join(expanduser('~'), 'media', uri))
    else:
        return '', 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False)
