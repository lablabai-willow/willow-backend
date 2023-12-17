from flask import jsonify, request
from datetime import datetime
from models.message_model import DevMessage, ProdMessage

def get_conversation(env, page=1, limit=10, last_document=None):
    if env not in ['dev', 'prod']:
        return {"error": "Invalid environment"}, 400

    try:
        message_model = get_message_model(env)

        if page == 1:
            messages = (
                message_model.collection
                .order('created_at')
                .limit(limit)
                .fetch()
            )
        else:
            if not last_document:
                return {"error": "last_document is required for paginated queries after the first page"}, 400

            messages = (
                message_model.collection
                .order('created_at')
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

def send_message(env, user, data):
    if env not in ['dev', 'prod'] or user not in ['ai_coach', 'end_user']:
        return {"error": "Invalid environment or user"}, 400

    try:
        message_type = data.get('message_type')
        content = data.get('content')

        if message_type not in ['image', 'audio', 'text']:
            return {"error": "Invalid message type"}, 400

        message_model = get_message_model(env)
        new_message = message_model()
        new_message.user = user
        new_message.message_type = message_type
        new_message.content = content
        new_message.created_at = datetime.now()
        new_message.save()

        return {"status": "Message saved successfully"}, 200

    except Exception as e:
        return {"error": str(e)}, 500

def get_message_model(env):
    if env == 'prod':
        return ProdMessage
    elif env == 'dev':
        return DevMessage
