import sys
path = 'https://github.com/tinashekwande/finalproject.git'
if path not in sys.path:
    sys.path.append(path)

from your_flask_app import app as application
