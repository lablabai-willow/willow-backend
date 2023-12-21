from flask import Flask
from flask_cors import CORS
from routes.message_route import controller
import fireo
import os


app = Flask(__name__)
CORS(app, resources={ "api/*": { "origins": "http://localhost:5713"}})

# Set up environment variables
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "serviceAccountKey.json"

# Set up Firebase Admin SDK and FireO
fireo.connection(from_file="serviceAccountKey.json")

# Register the controller blueprint
app.register_blueprint(controller)

if __name__ == '__main__':
    app.run(debug=True)