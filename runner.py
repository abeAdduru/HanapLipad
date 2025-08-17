# runner.py
from src.app import app

if __name__ == '__main__':
    # The app.run() command will start the Flask development server.
    # debug=True will ensure the server reloads on code changes.
    app.run(debug=True)