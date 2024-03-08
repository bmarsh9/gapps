from app import create_app
import os
import logging

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
app.logger.setLevel(logging.INFO)

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
