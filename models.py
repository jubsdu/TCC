from database import Base
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Time, Date, ForeignKey, Boolean, Numeric
from datetime import datetime, timezone

class Measurement_ia(Base):
    __tablename__ = "measurements_ia"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    bpm = Column(Integer)
    rr = Column(Numeric(8, 2))
    rmssd = Column(Numeric(8, 2))
    bpm_medio = Column(Numeric(8, 2))

    resultado_ia = Column(Integer)

    probabilidade_ia = Column(
        Numeric(5, 4)
    )

    date_time = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    phone = Column(String(20))
    email = Column(String(100), unique=True, nullable=False)
    password = Column(Text)
    photo = Column(String(255))
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    charge = Column(String(50))
    gender = Column(String(50))

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    icon = Column(String(50))
    description = Column(String(100))
    order = Column(Integer)

class Checkup(Base):
    __tablename__ = "checkups"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(50))
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    date = Column(Date)
    average_bpm = Column(Float)
    observation = Column(Text)

# class Medicao_bpm(Base):
#     __tablename__ = "medicoes_bpm"
#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
#     sistolica = Column(Integer)
#     diastolica = Column(Integer)
#     date_time = Column(
#         DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
#     )

#PERFORMANCE FÍSICA
class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date)
    average_rate = Column(Integer)
    maximum_rate = Column(Integer)
    active_time = Column(Integer)
    intensity = Column(String(50))
    time_recovery = Column(Integer)
    quant_sessions = Column(Integer)

class Cardiac_zone(Base):
    __tablename__ = "cardiac_zones"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date)
    zone = Column(String(50))
    intensity = Column(String(50))
    minutes = Column(Integer)

class Recovery(Base):
    __tablename__ = "recoveries"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date)
    final_bpm = Column(Integer)
    bpm_1_min = Column(Integer)
    bpm_2_min = Column(Integer)
    queda_2_min = Column(Integer)

class Physical_assessment(Base):
    __tablename__ = "physical_assessments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    beggining_date = Column(Date)
    end_date = Column(Date)
    average_fc = Column(Integer)
    active_time = Column(Integer)
    quant_sessions = Column(Integer)

class Goal_weekly(Base):
    __tablename__ = "goals_weekly"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    beginning_week = Column(Date)
    end_week = Column(Date)
    goal_activity = Column(Integer)
    activity_completed = Column(Integer)
    goal_intensity = Column(Integer)
    intensity_completed = Column(Integer)
    goal_sessions = Column(Integer)
    sessions_completed = Column(Integer)

class Measurement_bpm(Base):
    __tablename__ = "measurements_bpm"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)
    bpm = Column(Integer)
    date_time = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

#ANSIEDADE
class Episode_anxious(Base):
    __tablename__ = "episodes_anxious"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date_time = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    level_anxious = Column(Integer)
    cardiac_rate = Column(Integer)
    minutes = Column(Integer)
    observation = Column(Text)

class Trigger(Base):
    __tablename__ = "triggers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
class Episode_trigger(Base):
    __tablename__ = "episodes_triggers"
    id = Column(Integer, primary_key=True, index=True)
    episode_id = Column(Integer, ForeignKey("episodes_anxious.id"), nullable=False)
    trigger_id = Column(Integer, ForeignKey("triggers.id"), nullable=False)

class Tecnic(Base):
    __tablename__ = "tecniques"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    description = Column(Text)
    icon = Column(String(200))
class Episode_tecniques(Base):
    __tablename__ = "episodes_tecniques"
    id = Column(Integer, primary_key=True, index=True)
    episode_id = Column(Integer, ForeignKey("episodes_anxious.id"), nullable=False)
    tecnic_id = Column(Integer, ForeignKey("tecniques.id"), nullable=False)

class Accompaniment(Base):
    __tablename__ = "accompaniments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    psychotherapy = Column(Boolean)
    consultation = Column(Boolean)
    medication = Column(Boolean)

class Assessment_anxious(Base):
    __tablename__ = "assessments_anxious"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    beginning_period = Column(Date)
    end_period = Column(Date)
    average_level = Column(Numeric(4, 2))
    average_bpm = Column(Integer)

# PRESSÃO ARTERIAL
class Measurement_pressure(Base):
    __tablename__ = "measurements_pressure"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date_time = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    sistolica = Column(Integer)
    diastolica = Column(Integer)
    cardiac_rate = Column(Integer)
    origin = Column(String(50))
    observation = Column(Text)

class Measurement_ppg(Base):
    __tablename__ = "measurements_ppg"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    measurement_pressure_id =  Column(Integer, ForeignKey("measurements_pressure.id"), nullable=False)
    cardiac_rate = Column(Integer)
    hrv = Column(Numeric(6, 2))
    quality_sign = Column(Numeric(5, 2))
    date_time = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

class Warning_pressure(Base):
    __tablename__ = "warnings_pressure"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    data = Column(Date)
    title = Column(String(100))
    message = Column(Text)
    level = Column(String(50))
    viewed = Column(Boolean)

# RELATÓRIO SEMANAL
class Report_weekly(Base):
    __tablename__ = "reports_weekly"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    beginning_date = Column(Date)
    end_date = Column(Date)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

if __name__ == "__main__":
    print("Sucesso!")