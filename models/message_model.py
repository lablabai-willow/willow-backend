from fireo.fields import TextField, DateTime
from fireo.models import Model

class ProdMessages(Model):
    user = TextField()
    type = TextField()
    content = TextField()
    content_id = TextField(column_name="contentId")
    created_at = DateTime(column_name="createdAt")

class DevMessages(Model):
    user = TextField()
    type = TextField()
    content = TextField()
    content_id = TextField(column_name="contentId")
    created_at = DateTime(column_name="createdAt")