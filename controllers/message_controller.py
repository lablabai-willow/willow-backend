from datetime import datetime
from google.cloud import storage
from agent.agent_setup import agent_setup
from models.message_model import DevMessages, ProdMessages
import tempfile
import uuid

SUPPORTED_FILE_TYPES = ["audio", "image", "text"]
SUPPORTED_ENVIRONMENTS = ["dev", "prod"]
BASE_STORAGE_BUCKET_URL = "https://storage.cloud.google.com/willow-conversation-assets/"
BUCKET_NAME = "willow-conversation-assets"
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

# global agent
# agent = agent_setup()

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
        message_model = get_message_model(env)

        message_model.collection.delete_every()

        return {"status": "Deleted successfully"}, 200

    except Exception as e:
        return {"error": str(e)}, 500

def send_message(env, user, body, request_files):
    if not env or not user or not body:
      return { "status": "missing either env, user, or body data"}, 400

    # grab body attributes
    content_type = body.get("type")
    content = body.get("content")
    created_at_string = body.get("createdAt")

    # initialize dict of values we will write to firestore
    doc_id = uuid.uuid4()
    message_model = get_message_model(env)
    new_message = message_model()
    new_message.user = user
    new_message.type = content_type
    new_message.created_at = datetime.strptime(created_at_string, DATETIME_FORMAT)

    if content_type in SUPPORTED_FILE_TYPES:
        new_message.content = content if content_type == "text" else f'{uuid.uuid4()}'
    else:
        return { "status": "incorrect file type", content_type: content_type }, 400

    # write to db
    new_message.save()

    return { "status": "successfully registered message", "content": new_message.content }, 200


def send_file(content_id, request_files):
    if 'file' not in request_files or not request_files['file']:
        return { "statusText": "missing file" }, 400

    content_file = request_files['file']

    with tempfile.NamedTemporaryFile() as temp_file:
        content_file.save(temp_file.name)
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(BUCKET_NAME)
        blob = bucket.blob(content_id)
        blob.upload_from_filename(temp_file.name)
    
    return { "status": f"successfully uploaded file {content_id}" }, 200

def get_agent_response(env,body):
    if not env or not body:
      return { "statusText": "missing either env, or message data"}, 400
    try:
        agent_response = agent.chat(body.get("content"))

        message_model = get_message_model(env)
        new_message = message_model()
        new_message.user = "ai_coach"
        new_message.type = "text"
        created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        new_message.created_at = datetime.strptime(created_at, DATETIME_FORMAT)
        new_message.content = agent_response.response
        new_message.save()

        return {
            "status": "Successfully retrieved agent reply",
            "message": agent_response.response
        }, 200
    except Exception as e:
        return {"error": str(e)}, 500

def get_message_model(env):
    if env == 'prod':
        return ProdMessages
    elif env == 'dev':
        return DevMessages