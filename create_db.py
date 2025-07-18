from app import myapp_obj, db
from app.models import User

with myapp_obj.app_context():
    db.create_all()
    print("✅ Database created!")
