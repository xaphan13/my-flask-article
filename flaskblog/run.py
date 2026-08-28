import gunicorn
import waitress
from paste.translogger import TransLogger

from flaskblog import create_app

app = create_app(debug_mode=True)


if __name__ == "__main__":
    # waitress.serve(app, listen='0.0.0.0:5000')
    waitress.serve(TransLogger(app), host="0.0.0.0", port=5000)
    # app.run(host='0.0.0.0', port=5000)

    # python - m waitress --host=0.0.0.0 --port=5000 run:app
    # waitress-serve --host=0.0.0.0 --port=5000 run:app
    # gunicorn -w 1 -b 0.0.0.0:5000 flaskblog.run:app
    # gunicorn --bind 0.0.0.0:5000 flaskblog.run:app
