# routes.py

from flask import Blueprint, jsonify, request
from controllers.message_controller import get_conversation, delete_conversation, send_message

controller = Blueprint('controller', __name__)

@controller.route('/', methods=['GET'])
def hello_world():
    #return hello world in json
    return jsonify({"message": "Hello, World!"}), 200

@controller.route('/api/conversation', methods=['GET'])
def get_conversation_route():
    env = request.args.get('env')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 0))
    last_document = request.args.get('last_document')

    result, status_code = get_conversation(env, page, limit, last_document)

    return jsonify(result), status_code

@controller.route('/api/conversation', methods=['DELETE'])
def delete_conversation_route():
    env = request.args.get('env')

    result, status_code = delete_conversation(env)

    return jsonify(result), status_code

@controller.route('/api/sendMessage', methods=['POST'])
def send_message_route():
    env = request.args.get('env')
    user = request.args.get('user')

    data = request.get_json()

    result, status_code = send_message(env, user, data)

    return jsonify(result), status_code