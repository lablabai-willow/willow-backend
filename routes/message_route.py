# routes.py

from flask import Blueprint, jsonify, request
from flask_cors import cross_origin
from controllers.message_controller import get_agent_response, get_conversation, delete_conversation, send_message, send_file
from agent.agent_setup import agent_setup
import traceback

controller = Blueprint('controller', __name__)

def print_and_return_exception(e, **additional_params):
    print('An error occurred', e)
    traceback.print_exc()
    return jsonify({ "status": "error getting conversation", "exception": e, **additional_params}), 500


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

    try:
        result, status_code = get_conversation(env, page, limit, last_document)
        return jsonify(result), status_code
    except Exception as e:
        return print_and_return_exception(e)

@controller.route('/api/conversation', methods=['DELETE'])
def delete_conversation_route():
    env = request.args.get('env')

    try:
        result, status_code = delete_conversation(env)
        return jsonify(result), status_code
    except Exception as e:
        return print_and_return_exception(e)

@controller.route('/api/sendMessage', methods=['POST'])
def send_message_route():
    env = request.args.get('env')
    user = request.args.get('user')
    data = request.get_json()
    try:
        result, status_code = send_message(env, user, data)
        return jsonify(result), status_code
    except Exception as e:
        return print_and_return_exception(e)
    
@controller.route('/api/sendFile', methods=['POST'])
def send_file_route():
    content_id = request.args.get('contentId')
    env = request.args.get('env')
    files = request.files
    try:
        result, status_code = send_file(content_id, env, files)
        return jsonify(result), status_code
    except Exception as e:
        return print_and_return_exception(e, additional_params={"content_id": content_id})
    
@controller.route('/api/getAgentResponse', methods=['POST'])
def get_agent_response_route():
    env = request.args.get('env')
    data = request.get_json()

    try:
        result, status_code = get_agent_response(env, data)
        return jsonify(result), status_code
    except Exception as e:
        return print_and_return_exception(e)