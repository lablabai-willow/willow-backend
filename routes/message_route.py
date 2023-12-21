# routes.py

from flask import Blueprint, jsonify, request
from controllers.message_controller import get_agent_response, get_conversation, delete_conversation, send_message, send_file

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
    files = request.files

    try:
        result, status_code = send_message(env, user, data, files)
        return jsonify(result), status_code
    except Exception as e:
        print(e)
        return jsonify({ "statusText": "error uploading message" }), 500
    
@controller.route('/api/sendFile', methods=['POST'])
def send_file_route():
    content_id = request.args.get('contentId')
    files = request.files
    try:
        result, status_code = send_file(content_id, files)
        return jsonify(result), status_code
    except Exception as e:
        print(e)
        return jsonify({ "statusText": "error processing file", "content_id": content_id}), 500
    
@controller.route('/api/getAgentResponse', methods=['POST'])
def get_agent_response_route():
    env = request.args.get('env')
    data = request.get_json()

    try:
        result, status_code = get_agent_response(env, data)
        return jsonify(result), status_code
    except Exception as e:
        print(e)
        return jsonify({ "statusText": "error recieving message" }), 500
