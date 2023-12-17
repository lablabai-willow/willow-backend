from fireo.fields import TextField, DateTime
from fireo.models import Model

class ProdMessage(Model):
    user = TextField()
    message_type = TextField()
    content = TextField()
    # content_id = TextField(column_name="contentId")
    created_at = DateTime()

class DevMessage(Model):
    user = TextField()
    message_type = TextField()
    content = TextField()
    # content_id = TextField(column_name="contentId")
    created_at = DateTime()