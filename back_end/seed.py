# from datetime import date, datetime, timezone
# from database import db_session
# from models import User, Checkup, Activity, Measurement_bpm 

# DEMO_EMAIL = "aquieopaulo@gmail.com"

# print("SEED.PY FOI EXECUTADO")
# def seed_db():

#     print("Iniciando seed da Home...")

#     # ==========================================
#     # 1. USUÁRIO
#     # ==========================================

#     user = db_session.query(User).filter_by(
#         email=DEMO_EMAIL
#     ).first()

#     if not user:
#         user = User(
#             name="Teste",
#             phone="11999999999",
#             email=DEMO_EMAIL,
#             password="123456"
#         )

#         db_session.add(user)
#         db_session.commit()

#         print("Usuário de demonstração criado.")

#     else:
#         print("Usuário de demonstração já existe.")

#     user_id = user.id
#     print("ID DO USUÁRIO DO SEED:", user_id)

#     # ==========================================
#     # 2. VERIFICA SE A HOME JÁ FOI PREENCHIDA
#     # ==========================================

#     checkup_exists = db_session.query(Checkup).filter_by(
#         user_id=user_id
#     ).first()

#     if checkup_exists:
#         print("Dados da Home já existem. Nenhum dado foi duplicado.")
#         return

#     # ==========================================
#     # 3. ATIVIDADE
#     # ==========================================

#     activity = Activity(
#         user_id=user_id,
#         date=date(2026, 9, 11),

#         # BPM médio mostrado na Home
#         average_rate=97,

#         # BPM máximo
#         maximum_rate=140,

#         # 3 horas e 42 minutos
#         # 3 * 60 + 42 = 222 minutos
#         active_time=222,

#         intensity="Zona 4",

#         # Recuperação em minutos
#         time_recovery=34,

#         quant_sessions=4
#     )

#     db_session.add(activity)
#     db_session.commit()

#     print("Atividade criada.")

#     # ==========================================
#     # 4. MEDIÇÕES DE BPM
#     # ==========================================

#     measurements = [
#         Measurement_bpm(
#             user_id=user_id,
#             activity_id=activity.id,
#             bpm=62,
#             date_time=datetime(
#                 2026, 9, 11, 8, 0,
#                 tzinfo=timezone.utc
#             )
#         ),

#         Measurement_bpm(
#             user_id=user_id,
#             activity_id=activity.id,
#             bpm=78,
#             date_time=datetime(
#                 2026, 9, 11, 10, 0,
#                 tzinfo=timezone.utc
#             )
#         ),

#         Measurement_bpm(
#             user_id=user_id,
#             activity_id=activity.id,
#             bpm=97,
#             date_time=datetime(
#                 2026, 9, 11, 12, 0,
#                 tzinfo=timezone.utc
#             )
#         ),

#         Measurement_bpm(
#             user_id=user_id,
#             activity_id=activity.id,
#             bpm=140,
#             date_time=datetime(
#                 2026, 9, 11, 14, 0,
#                 tzinfo=timezone.utc
#             )
#         ),

#         Measurement_bpm(
#             user_id=user_id,
#             activity_id=activity.id,
#             bpm=83,
#             date_time=datetime(
#                 2026, 9, 10, 12, 0,
#                 tzinfo=timezone.utc
#             )
#         )
#     ]

#     db_session.add_all(measurements)

#     print("Medições de BPM criadas.")

#     # ==========================================
#     # 5. CHECKUPS — SEÇÃO "RECENTES"
#     # ==========================================

#     checkups = [

#         Checkup(
#             user_id=user_id,
#             type="Checkup geral",
#             date=date(2026, 9, 11),
#             average_bpm=78,
#             observation="Checkup geral realizado."
#         ),

#         Checkup(
#             user_id=user_id,
#             type="Checkup geral",
#             date=date(2026, 9, 10),
#             average_bpm=83,
#             observation="Checkup geral realizado."
#         )
#     ]

#     db_session.add_all(checkups)

#     # ==========================================
#     # 6. SALVA TUDO
#     # ==========================================

#     db_session.commit()
#     checkups = db_session.query(Checkup).all()

#     for checkup in checkups:
#         print(
#             "CHECKUP:",
#             checkup.id,
#             "USER_ID:",
#             checkup.user_id,
#             "DATA:",
#             checkup.date,
#             "TIPO:",
#             checkup.type
#         )
#     print("Checkups criados.")
#     print("Seed da Home concluído com sucesso!")

# if __name__ == "__main__":
#     seed_db()

"""Gera dados sintéticos para uma conta já existente no banco local.
Uso: python seed.py --user-id 3
"""
import argparse
from database import SessionLocal, init_db
from models import User, Measurement_ia
from simulador_ia import seed_user_data


def main():
    parser = argparse.ArgumentParser(description="Gerar conjunto demonstrativo de dados para uma conta.")
    parser.add_argument("--user-id", type=int, required=True)
    args = parser.parse_args()
    init_db()
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(id=args.user_id).first()
        if user is None:
            print("Conta não encontrada.")
            return 1
        before = db.query(Measurement_ia).filter_by(user_id=user.id).count()
        seed_user_data(db, user.id)
        after = db.query(Measurement_ia).filter_by(user_id=user.id).count()
        print(f"Medições de BPM sintéticas: {before} → {after}")
        return 0
    finally:
        SessionLocal.remove()


if __name__ == "__main__":
    raise SystemExit(main())
