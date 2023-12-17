from flask import Flask
from routes.message_route import controller
import fireo

app = Flask(__name__)

# Set up Firebase Admin SDK and FireO
fireo.connection(from_file="serviceAccountKey.json")

# Register the controller blueprint
app.register_blueprint(controller)

if __name__ == '__main__':
    app.run(debug=True)