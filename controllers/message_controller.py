from datetime import datetime
from dateutil import parser
from google.cloud import storage
from agent.agent_setup import agent_setup
from models.message_model import DevMessages, ProdMessages
import tempfile
import uuid

SUPPORTED_MESSAGE_TYPES = ["audio", "image", "text"]
SUPPORTED_ENVIRONMENTS = ["dev", "prod"]
BASE_STORAGE_BUCKET_URL = "https://storage.cloud.google.com/willow-conversation-assets/"
BUCKET_NAME = "willow-conversation-assets"
DATETIME_FORMAT = "'%Y-%m-%dT%H:%M:%S.%f%z'"

global agent
agent = agent_setup(simple_prompt=True)

def get_conversation(env, page=1, limit=10, last_document=None):
    if env not in SUPPORTED_ENVIRONMENTS:
        return {"error": "Invalid environment"}, 400

    try:
        message_model = get_message_model(env)

        if page == 1:
            messages = (
                message_model.collection
                .order('-created_at')   # sorted in descending order to get the most recent messages first
                .limit(limit)
                .fetch()
            )
        else:
            if not last_document:
                return {"error": "last_document is required for paginated queries after the first page"}, 400

            messages = (
                message_model.collection
                .order('-created_at')   # sorted in descending order to get the most recent messages first
                .limit(limit)
                .start_after(last_document)
                .fetch()
            )

        messages_data = [{"id": msg.id, **msg.to_dict()} for msg in messages]

        return {
            "status": "Successfully retrieved conversation",
            "page": page,
            "limit": limit,
            "total_messages": len(messages_data),
            "messages": messages_data
        }, 200

    except Exception as e:
        return {"error": str(e)}, 500

def delete_conversation(env):
    if env not in ['dev', 'prod']:
        return {"error": "Invalid environment"}, 400

    try:
        # delete all messages in db
        message_model = get_message_model(env)
        message_model.collection.delete_every()

        # reset agent
        agent.reset();

        return {"status": "Deleted and reset successfully"}, 200

    except Exception as e:
        return {"error": str(e)}, 500

def send_message(env, user, body):
    if not env or not user or not body:
        return { "status": "missing either env, user, or body data"}, 400

    # grab body attributes
    content_type = body.get("type")
    content = body.get("content")
    created_at_string = body.get("createdAt")
    print(content_type, content, created_at_string)
    # initialize dict of values we will write to firestore
    message_model = get_message_model(env)
    new_message = message_model()
    new_message.user = user
    new_message.type = content_type
    new_message.created_at = parser.parse(created_at_string)

    """
        - if content type is text, we should respond with agent response.
        - If its a file, simply save it and response with saved userMessage. We will get the agent response in the file upload endpoint
          which will be called right after
    """

    if content_type == "text":
        new_message.content = content
        new_message.save()
        agent_response, status_code = get_agent_response(env, body)

        if status_code != 200:
            return { "status": "something went wrong getting agent response", "userMessage": new_message.to_dict()}
        
        return { "userMessage": new_message.to_dict(), "agentResponse": agent_response["message"]}, 200 
    elif content_type == "image" or content_type == "audio":
        new_message.content = f'{uuid.uuid4()}'
        new_message.save()

        return { "userMessage": new_message.to_dict()}, 200
    else:
        return { "status": "incorrect file type", content_type: content_type }, 400


def send_file(content_id, env, request_files):
    if 'file' not in request_files or not request_files['file']:
        return { "status": "missing file" }, 400

    content_file = request_files['file']

    print("WE MADE IT HERE AT LEAST")
    with tempfile.NamedTemporaryFile() as temp_file:
        content_file.save(temp_file.name)
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(BUCKET_NAME)
        blob = bucket.blob(content_id)
        blob.upload_from_filename(temp_file.name)
    
    image_prompt = { "content": f'Analyze the image I sent at this URL: {BASE_STORAGE_BUCKET_URL}{content_id}. Given the context of what we talked about, what does it tell you about my emotional state?' }
    agent_response, status_code = get_agent_response(env, image_prompt)

    if status_code != 200:
        return { "status": "something went wrong getting agent response to image", "contentId": content_id}
    
    return { "agentResponse": agent_response["message"]}, 200

def get_agent_response(env,body):
    if not env or not body:
      return { "status": "missing either env, or message data"}, 400
    try:
        agent_response = agent.chat(body.get("content"))
        print(body.get("content"))

        message_model = get_message_model(env)
        new_message = message_model()
        new_message.user = "ai_coach"
        new_message.type = "text"
        new_message.created_at = datetime.utcnow()
        new_message.content = agent_response.response
        new_message.save()

        return {
            "status": "Successfully retrieved agent reply",
            "message": new_message.to_dict()
        }, 200
    except Exception as e:
        return {"error": str(e)}, 500

def get_message_model(env):
    if env == 'prod':
        return ProdMessages
    elif env == 'dev':
        return DevMessages