from fireo.fields import TextField, DateTime
from fireo.models import Model

class ProdMessages(Model):
    user = TextField()
    type = TextField()
    content = TextField()
    created_at = DateTime()

class DevMessages(Model):
    user = TextField()
    type = TextField()
    content = TextField()
    created_at = DateTime()