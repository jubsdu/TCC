"""Remove uma conta de demonstração e seus dados. Uso: python limpar_seed.py --user-id 3"""
import argparse

from database import SessionLocal, init_db
from models import (
    User, Measurement_ia, Checkup, Activity, Cardiac_zone, Recovery,
    Physical_assessment, Goal_weekly, Measurement_bpm, Episode_anxious,
    Episode_trigger, Accompaniment, Measurement_pressure, Measurement_ppg,
    Warning_pressure, Report_weekly, Assessment_anxious,
)


def main():
    parser = argparse.ArgumentParser(description="Apagar uma conta e os dados associados do SQLite local.")
    parser.add_argument("--user-id", type=int, required=True, help="ID numérico da conta que será removida")
    args = parser.parse_args()
    init_db()
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(id=args.user_id).first()
        if user is None:
            print("Conta não encontrada.")
            return 1
        confirm = input(f"Apagar a conta de ID {args.user_id} e todos os dados dela? Digite APAGAR para confirmar: ")
        if confirm != "APAGAR":
            print("Cancelado.")
            return 0
        episode_ids = [row.id for row in db.query(Episode_anxious.id).filter_by(user_id=user.id).all()]
        if episode_ids:
            db.query(Episode_trigger).filter(Episode_trigger.episode_id.in_(episode_ids)).delete(synchronize_session=False)
        for model in [
            Measurement_bpm, Measurement_ia, Checkup, Cardiac_zone, Recovery,
            Physical_assessment, Goal_weekly, Episode_anxious, Accompaniment,
            Measurement_ppg, Measurement_pressure, Warning_pressure,
            Report_weekly, Assessment_anxious,
        ]:
            db.query(model).filter_by(user_id=user.id).delete(synchronize_session=False)
        db.query(Activity).filter_by(user_id=user.id).delete(synchronize_session=False)
        db.delete(user)
        db.commit()
        print("Conta e dados relacionados removidos.")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        SessionLocal.remove()


if __name__ == "__main__":
    raise SystemExit(main())
