from main import app
from os.path import join, expanduser, exists
from os import getpid, mkdir

if __name__ == '__main__':
    from logging.handlers import RotatingFileHandler
    from logging import Formatter, INFO
    if not exists(join(expanduser('~'), 'logs')):
        mkdir(join(expanduser('~'), 'logs'))
    file_handler = RotatingFileHandler(join(expanduser(
        '~'), 'logs', f'files-Server-{getpid()}.log'), maxBytes=10240, backupCount=3)
    file_handler.setFormatter(Formatter(
        "[%(asctime)s] - %(levelname)s: %(message)s, in %(pathname)s:%(lineno)d "))
    file_handler.setLevel(INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(INFO)
    app.logger.info('Server start')
    app.run()
