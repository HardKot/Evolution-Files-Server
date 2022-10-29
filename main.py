from os import remove
import uuid
from os.path import exists
from flask import Flask, send_file, request

app = Flask(__name__)

@app.route('/')
def home():
    return 'Wellcome!'

@app.route('/users.image/<user_id>')
def get_users_image(id):
    if exists(f'./media/image/{id}.png'):
        return send_file(f'./media/image/{id}.png')
    else:
        return '', 404

@app.route('/image/<image_id>')
def get_image_by_id(image_id):
    if exists(f'./media/image/{image_id}.png'):
        return send_file(f'./media/image/{image_id}.png')
    else:
        return '', 404

@app.route('/meditation.image/<meditation_id>')
def get_meditation_image(meditation_id):
    if exists(f'./media/image/{meditation_id}.png'):
        return send_file(f'./media/image/{meditation_id}.png')
    else:
        return '', 404

@app.route('/meditation.audio/<meditation_id>')
def get_meditation_image(meditation_id):
    if exists(f'./media/audio/{meditation_id}.mp3'):
        return send_file(f'./media/audio/{meditation_id}.mp3')
    else:
        return '', 404

@app.route('/image', methods=['POST'])
def post_image():
    image_base64 = request.get_json()
    image_id = uuid
    with open(f'media/image/{image_id}.png', 'w') as image:
        image.write(image_base64)
    return image_id

@app.route('/image/<image_id>', methods=['PUT'])
def post_image(image_id):
    image_base64 = request.get_json()
    if exists(f'./media/image/{image_id}.png'):
        remove(f'./media/image/{image_id}.png')
    image_id = uuid
    with open(f'media/image/{image_id}.png', 'w') as image:
        image.write(image_base64)
    return image_id

@app.route('/audio', methods=['POST'])
def post_audio():
    pass


if __name__ == '__main__':
    app.run(host='0.0.0.0')