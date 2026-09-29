from database import db_session
from models import User, Checkup, Activity, Measurement_bpm

EMAIL = "aquieopaulo@gmail.com"

user = db_session.query(User).filter_by(
    email=EMAIL
).order_by(User.id.desc()).first()

print("Usuário encontrado:", user.id, user.email)

# Apaga medições relacionadas
db_session.query(Measurement_bpm).filter(
    Measurement_bpm.user_id == user.id
).delete()

# Apaga atividades
db_session.query(Activity).filter(
    Activity.user_id == user.id
).delete()

# Apaga checkups
db_session.query(Checkup).filter(
    Checkup.user_id == user.id
).delete()

# Apaga o usuário duplicado
db_session.delete(user)

db_session.commit()

print("Usuário duplicado e dados do seed removidos.")