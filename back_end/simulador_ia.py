"""Geração de dados sintéticos individuais para demonstração do VitaPulse.

Os números gerados são fictícios. O modelo joblib existente é usado somente para
classificar a amostra sintética quando é compatível; ele não mede sinais reais.
"""
from __future__ import annotations

import logging
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean

from models import (
    Measurement_ia, User, Category, Checkup, Activity, Cardiac_zone, Recovery,
    Physical_assessment, Goal_weekly, Measurement_bpm, Episode_anxious, Trigger,
    Episode_trigger, Tecnic, Accompaniment, Measurement_pressure,
    Measurement_ppg, Warning_pressure, Report_weekly,
)

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent
MAX_READINGS_PER_USER = 600
_MODEL = None
_MODEL_TRIED = False


def _load_model():
    global _MODEL, _MODEL_TRIED
    if _MODEL_TRIED:
        return _MODEL
    _MODEL_TRIED = True
    model_path = BASE_DIR / "modelo_ia.joblib"
    try:
        if model_path.exists():
            import joblib
            _MODEL = joblib.load(model_path)
            logger.info("Modelo de classificação carregado: %s", model_path.name)
    except Exception as exc:  # fallback estatístico mantém o aplicativo funcional
        logger.warning("Modelo opcional não pôde ser carregado; usando regra local: %s", exc)
        _MODEL = None
    return _MODEL


def predict_synthetic_sample(bpm: int, rmssd: float) -> tuple[int, float]:
    """Retorna classe/probabilidade demonstrativas para uma amostra sintética."""
    model = _load_model()
    if model is not None:
        try:
            import pandas as pd
            frame = pd.DataFrame([{"heart_rate": bpm, "hrv_rmssd": rmssd}])
            predicted = int(model.predict(frame)[0])
            probabilities = model.predict_proba(frame)[0]
            classes = list(model.classes_)
            positive_index = classes.index(1) if 1 in classes else int(probabilities.argmax())
            return predicted, float(probabilities[positive_index])
        except Exception as exc:
            logger.warning("Falha na inferência do modelo; usando regra local: %s", exc)

    # Fallback de demonstração, não é avaliação clínica.
    score = 0.08 + max(0, bpm - 90) / 120 + max(0, 35 - rmssd) / 100
    probability = max(0.02, min(0.95, score))
    return (1 if probability >= 0.45 else 0), float(probability)


def _make_reading(db, user_id: int, bpm: int, recorded_at: datetime, rng=None):
    rng = rng or random
    bpm = int(max(50, min(125, bpm)))
    rr = 60000.0 / bpm
    rmssd = round(rng.uniform(18.0, 68.0), 2)
    previous = (
        db.query(Measurement_ia)
        .filter(Measurement_ia.user_id == user_id)
        .order_by(Measurement_ia.date_time.desc())
        .limit(14)
        .all()
    )
    recent_bpm = [float(item.bpm) for item in previous if item.bpm is not None]
    bpm_average = round(mean(recent_bpm + [bpm]), 2)
    result, probability = predict_synthetic_sample(bpm, rmssd)
    measurement = Measurement_ia(
        user_id=user_id,
        bpm=bpm,
        rr=round(rr, 2),
        rmssd=rmssd,
        bpm_medio=bpm_average,
        resultado_ia=result,
        probabilidade_ia=round(probability, 4),
        date_time=recorded_at,
    )
    db.add(measurement)
    db.flush()
    return measurement


def create_live_reading(db, user_id: int):
    """Cria e persiste um novo ponto para a tela ao vivo."""
    previous = (
        db.query(Measurement_ia)
        .filter(Measurement_ia.user_id == user_id)
        .order_by(Measurement_ia.date_time.desc())
        .first()
    )
    if previous and previous.bpm is not None:
        base = int(previous.bpm)
    else:
        base = random.randint(68, 84)

    # Variação suave com picos ocasionais, sem sair do intervalo da simulação.
    if random.random() < 0.07:
        variation = random.choice([-1, 1]) * random.randint(7, 15)
    else:
        variation = random.randint(-3, 3)
    bpm = max(55, min(120, base + variation))
    item = _make_reading(db, user_id, bpm, datetime.now())

    # Limita a quantidade de pontos persistidos para o app não crescer sem limite.
    count = db.query(Measurement_ia).filter(Measurement_ia.user_id == user_id).count()
    if count > MAX_READINGS_PER_USER:
        old_ids = [
            row.id for row in (
                db.query(Measurement_ia.id)
                .filter(Measurement_ia.user_id == user_id)
                .order_by(Measurement_ia.date_time.desc())
                .offset(MAX_READINGS_PER_USER)
                .all()
            )
        ]
        if old_ids:
            db.query(Measurement_ia).filter(Measurement_ia.id.in_(old_ids)).delete(synchronize_session=False)
    db.commit()
    db.refresh(item)
    return item


def seed_global_choices(db) -> None:
    """Garante opções auxiliares usadas pelas telas."""
    categories = [
        ("Frequência cardíaca", "pulse-icon.png", "Acompanhe o BPM", 1),
        ("Ansiedade", "anxiety-icon.png", "Registre episódios", 2),
        ("Pressão arterial", "pressure-icon.png", "Histórico demonstrativo", 3),
        ("Performance física", "performance-icon.png", "Atividade e recuperação", 4),
    ]
    if db.query(Category).count() == 0:
        db.add_all([Category(name=n, icon=i, description=d, order=o) for n, i, d, o in categories])

    trigger_names = ["Sobrecarga", "Sono irregular", "Cafeína", "Situação social", "Preocupações"]
    existing_triggers = {item.name for item in db.query(Trigger).all()}
    for name in trigger_names:
        if name not in existing_triggers:
            db.add(Trigger(name=name))

    techniques = [
        ("Respiração", "Exercício de respiração para controle da ansiedade", "respiracao-icon.png"),
        ("Relaxamento", "Técnica de relaxamento", "relaxamento-icon.png"),
        ("Aterramento", "Técnica de aterramento", "aterramento-icon.png"),
        ("Registrar sentimentos", "Registro dos sentimentos percebidos", "registrar-icon.png")
    ]
    existing_techniques = {item.name for item in db.query(Tecnic).all()}
    for name, description, icon in techniques:
        if name not in existing_techniques:
            db.add(Tecnic(name=name, description=description, icon=icon))
    db.commit()


def seed_user_data(db, user_id: int) -> None:
    """Garante dados sintéticos para as telas, preenchendo somente tabelas vazias."""
    seed_global_choices(db)
    rng = random.Random(f"vitapulse-{user_id}-{datetime.now().date().isoformat()}")
    now = datetime.now()
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    def has_rows(model):
        return db.query(model).filter_by(user_id=user_id).first() is not None

    # Série de frequência cardíaca usada pelo medidor e pelos gráficos.
    if not has_rows(Measurement_ia):
        baseline = rng.randint(68, 82)
        for index in range(48):
            stamp = now - timedelta(minutes=(47 - index) * 10)
            pulse = baseline + round(4 * __import__("math").sin(index / 4)) + rng.randint(-5, 5)
            if index % 13 == 0:
                pulse += rng.randint(5, 13)
            _make_reading(db, user_id, max(55, min(120, pulse)), stamp, rng)

    # Atividades; se já existirem, são reutilizadas nas tabelas dependentes.
    activities = db.query(Activity).filter_by(user_id=user_id).order_by(Activity.date.desc()).all()
    if not activities:
        activities = []
        for index in range(3):
            activity = Activity(
                user_id=user_id,
                date=today - timedelta(days=index * 2 + rng.randint(0, 1)),
                average_rate=rng.randint(75, 98),
                maximum_rate=rng.randint(118, 158),
                active_time=rng.randint(25, 95),
                intensity=rng.choice(["Zona 2", "Zona 3", "Zona 4"]),
                time_recovery=rng.randint(12, 45),
                quant_sessions=rng.randint(1, 3),
            )
            db.add(activity)
            db.flush()
            activities.append(activity)

    if not has_rows(Measurement_bpm):
        for activity in activities:
            for point in range(5):
                base_date = datetime.combine(activity.date or today, datetime.min.time())
                db.add(Measurement_bpm(
                    user_id=user_id,
                    activity_id=activity.id,
                    bpm=max(60, min(170, (activity.average_rate or 80) + rng.randint(-12, 38))),
                    date_time=base_date + timedelta(hours=8, minutes=point * 8),
                ))

    if not has_rows(Cardiac_zone):
        for activity in activities:
            db.add(Cardiac_zone(
                user_id=user_id,
                date=activity.date or today,
                zone=activity.intensity or "Zona 2",
                intensity=activity.intensity or "Zona 2",
                minutes=rng.randint(8, 35),
            ))

    if not has_rows(Checkup):
        for index in range(3):
            db.add(Checkup(
                user_id=user_id,
                type=rng.choice(["Checkup geral", "Avaliação física", "Acompanhamento"]),
                date=today - timedelta(days=index + 1),
                average_bpm=rng.randint(69, 94),
                observation="Registro sintético para demonstração do aplicativo.",
            ))

    if not has_rows(Recovery):
        for index in range(2):
            final_bpm = rng.randint(72, 94)
            bpm_1 = final_bpm + rng.randint(5, 13)
            bpm_2 = final_bpm + rng.randint(1, 7)
            db.add(Recovery(
                user_id=user_id,
                date=today - timedelta(days=index + 1),
                final_bpm=final_bpm,
                bpm_1_min=bpm_1,
                bpm_2_min=bpm_2,
                queda_2_min=bpm_1 - bpm_2,
            ))

    if not has_rows(Physical_assessment):
        db.add(Physical_assessment(
            user_id=user_id,
            beggining_date=today - timedelta(days=14),
            end_date=today,
            average_fc=round(sum(a.average_rate or 0 for a in activities) / max(len(activities), 1)),
            active_time=sum(a.active_time or 0 for a in activities),
            quant_sessions=sum(a.quant_sessions or 0 for a in activities),
        ))

    if not has_rows(Goal_weekly):
        db.add(Goal_weekly(
            user_id=user_id,
            beginning_week=monday,
            end_week=monday + timedelta(days=6),
            goal_activity=180,
            activity_completed=sum(a.active_time or 0 for a in activities),
            goal_intensity=3,
            intensity_completed=len(activities),
            goal_sessions=4,
            sessions_completed=sum(a.quant_sessions or 0 for a in activities),
        ))

    if not has_rows(Episode_anxious):
        triggers = db.query(Trigger).all()
        for index in range(6):
            episode = Episode_anxious(
                user_id=user_id,
                date_time=now - timedelta(days=rng.randint(0, 12), hours=rng.randint(0, 23)),
                level_anxious=rng.randint(2, 8),
                cardiac_rate=rng.randint(78, 112),
                minutes=rng.randint(5, 35),
                observation="Episódio sintético para demonstração; não representa avaliação clínica.",
            )
            db.add(episode)
            db.flush()
            if triggers:
                db.add(Episode_trigger(episode_id=episode.id, trigger_id=rng.choice(triggers).id))

    # Medidas de pressão e sinais PPG são gerados/associados sem duplicar o histórico.
    pressures = db.query(Measurement_pressure).filter_by(user_id=user_id).order_by(Measurement_pressure.date_time.desc()).all()
    if not pressures:
        pressures = []
        for index in range(12):
            stamp = now - timedelta(days=rng.randint(0, 13), hours=rng.randint(0, 23))
            pressure = Measurement_pressure(
                user_id=user_id,
                date_time=stamp,
                sistolica=rng.randint(108, 139),
                diastolica=rng.randint(66, 89),
                cardiac_rate=rng.randint(66, 104),
                origin="simulação",
                observation="Valor fictício de demonstração; não usar para decisões de saúde.",
            )
            db.add(pressure)
            db.flush()
            pressures.append(pressure)

    # Se o banco já tinha medições antigas (por exemplo, da semana fixa de setembro),
    # preserva-as e completa os últimos 14 dias para alimentar semana atual e comparação.
    existing_days = {
        row.date_time.date()
        for row in pressures
        if row.date_time is not None
    }
    for day_offset in range(13, -1, -1):
        measurement_day = today - timedelta(days=day_offset)
        if measurement_day in existing_days:
            continue
        stamp = datetime.combine(measurement_day, datetime.min.time()).replace(
            hour=rng.choice([8, 10, 14, 17]), minute=rng.choice([0, 15, 30, 45])
        )
        pressure = Measurement_pressure(
            user_id=user_id,
            date_time=stamp,
            sistolica=rng.randint(110, 136),
            diastolica=rng.randint(68, 86),
            cardiac_rate=rng.randint(65, 98),
            origin="simulação",
            observation="Medição sintética para demonstração; não usar para decisões de saúde.",
        )
        db.add(pressure)
        db.flush()
        pressures.append(pressure)
        existing_days.add(measurement_day)

    # Garante um registro PPG associado a cada medição de pressão, inclusive em bancos
    # que já tinham PPGs antigos mas não os registros mais recentes.
    existing_ppg_pressure_ids = {
        row.measurement_pressure_id
        for row in db.query(Measurement_ppg).filter_by(user_id=user_id).all()
    }
    for pressure in pressures:
        if pressure.id in existing_ppg_pressure_ids:
            continue
        db.add(Measurement_ppg(
            user_id=user_id,
            measurement_pressure_id=pressure.id,
            cardiac_rate=pressure.cardiac_rate,
            hrv=round(rng.uniform(20, 62), 2),
            quality_sign=round(rng.uniform(75, 99), 2),
            date_time=pressure.date_time or now,
        ))

    # Alertas contextuais são criados pela rota da página de pressão, depois
    # que ela garante a existência de leituras recentes para o usuário.
    # Não inserir o aviso genérico "Dados de demonstração" dentro de ALERTAS.

    if not has_rows(Report_weekly):
        db.add(Report_weekly(
            user_id=user_id,
            beginning_date=monday,
            end_date=monday + timedelta(days=6),
        ))

    if not db.query(Accompaniment).filter_by(user_id=user_id).first():
        db.add(Accompaniment(user_id=user_id, psychotherapy=False, consultation=False, medication=False))

    db.commit()
    logger.info("Dados sintéticos verificados/criados para user_id=%s", user_id)