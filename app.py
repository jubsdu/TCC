import os
from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_cors import CORS
from database import SessionLocal, init_db
from models import User, Doctor, Category, Checkup, Activity, Cardiac_zone, Recovery, Physical_assessment, Goal_weekly, Measurement_bpm, Episode_anxious, Trigger, Episode_trigger, Tecnic, Episode_tecniques, Accompaniment, Measurement_pressure, Measurement_ppg, Warning_pressure, Report_weekly

app = Flask(__name__)
CORS(app)

db_session = SessionLocal()

@app.route('/')
def index():
    return render_template('index.html')

from flask import Flask, render_template

app = Flask(__name__)

# Route principal / Index
@app.route('/')
def index():
    return render_template('index.html')

# Home
@app.route('/home')
def home():
    return render_template('home.html')

# Autenticação e Conta
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get("password")

        print("LOGIN RECEBIDO:", email)

        user = db_session.query(User).filter_by(email=email).first()

        if user and user.password == password:
            print("LOGIN CORRETO - ID:", user.id)
            return render_template('home.html')

        print("LOGIN INCORRETO")

        return render_template('login.html', error='Email ou senha incorretos.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get("name")
        phone = request.form.get("phone")
        email = request.form.get("email")
        password = request.form.get("password")

        user = User(
            name=name,
            phone=phone,
            email=email,
            password=password
        )        

        db_session.add(user)
        db_session.commit()

        return render_template('login.html')

    return render_template('register.html')

@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        # Processa a solicitação de recuperação de senha
        return redirect(url_for('verification'))
    return render_template('forgot.html')

@app.route('/new-password', methods=['GET', 'POST'])
def new_password():
    if request.method == 'POST':
        # Salva a nova senha
        return redirect(url_for('login'))
    return render_template('new-password.html')

@app.route('/verification', methods=['GET', 'POST'])
def verification():
    if request.method == 'POST':
        # Valida o código digitado
        return redirect(url_for('new_password'))
    return render_template('verification.html')

# Onboarding
@app.route('/onboarding-reason', methods=['GET', 'POST'])
def onboarding_reason():
    if request.method == 'POST':
        return redirect(url_for('onboarding_treatment'))
    return render_template('onboarding-reason.html')

@app.route('/onboarding-treatment', methods=['GET', 'POST'])
def onboarding_treatment():
    if request.method == 'POST':
        return redirect(url_for('register'))
    return render_template('onboarding-treatment.html')

# Módulos de Saúde e Monitoramento
@app.route('/anxiety')
def anxiety():
    return render_template('anxiety.html')

@app.route('/performance')
def performance():
    return render_template('performance.html')

@app.route('/pressure')
def pressure():
    return render_template('pressure.html')

@app.route('/report')
def report():
    return render_template('report.html')

# USUÁRIOS
# @app.route('/api/users/<int:id>/delete', methods=['GET'])
# def delete_user(id):
#     user = db_session.query(User).filter_by(id=id).first()

#     if not user:
#         return "Usuário não encontrado", 404

#     db_session.delete(user)
#     db_session.commit()

#     return f"Usuário {id} deletado com sucesso!"

@app.route('/api/users', methods=["GET", "POST"])
def users():
    if request.method == "GET":
        users = db_session.query(User).all()

        return jsonify([
            {
                "id": user.id,
                "name": user.name,
                "phone": user.phone,
                "email": user.email,
                "photo": user.photo,
                "created_at": user.created_at
            }
            for user in users
        ])

    if request.method == "POST":
        data = request.get_json()

        user = User(
            name=data.get("name"),
            phone=data.get("phone"),
            email=data.get("email"),
            password=data.get("password"),
            photo=data.get("photo")
        )

        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        return jsonify({
            "message": "Usuário criado com sucesso",
            "id": user.id
        }), 201 

@app.route('/api/users/<int:id>', methods=["GET"])
def get_user(id):
    user = db_session.query(User).filter(User.id == id).first()

    if not user:
        return jsonify({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "photo": user.photo
        })

@app.route('/api/users/<int:id>', methods=["PUT"])
def update_user(id):
    user = db_session.query(User).filter(User.id == id). first()

    if not user:
        return jsonify({
            "error": "Usuário não encontrado"
        }), 404
    
    data = request.get_json()

    if "name" in data:
        user.name = data["name"]
    
    if "phone" in data:
        user.phone = data["phone"]
    
    if "email" in data:
        user.email = data["email"]

    if "password" in data:
        user.password = data["password"]
    
    if "photo" in data:
        user.photo = data["photo"]

    db_session.commit()

    return jsonify({
        "message": "Usuário atualizado com sucesso"
    })

#PERFORMANCE
@app.route('/api/activities', methods=["GET"])
def get_activities():
    user_id = request.args.get("user_id", type=int)

    query = db_session.query(Activity)

    if user_id:
        query = query.filter(Activity.user_id == user_id)

    activities = query.order_by(Activity.date.desc()).all()

    return jsonify([
        {
        "id": activity.id,
        "user_id": activity.user_id,
        "date": activity.date,
        "average_rate": activity.average_rate,
        "maximium_rate": activity.maximium_rate,
        "active_time": activity.active_time,
        "intensity": activity.intensity,
        "time_recovery": activity.time_recovery,
        "quant_sessions": activity.quant_sessions
    }
        for activity in activities
    ])

@app.route('/api/activities', methods=["POST"])
def create_activity():
    data = request.get_json()

    activity = Activity(
        user_id=data.get("user_id"),
        date=data.get("date"),
        average_rate=data.get("average_rate"),
        maximium_rate=data.get("maximium_rate"),
        active_time=data.get("active_time"),
        intensity=data.get("intensity"),
        time_recovery=data.get("time_recovery"),
        quant_sessions=data.get("quant_sessions")
    )

    db_session.add(activity)
    db_session.commit()
    db_session.refresh(activity)

    return jsonify({
        "message": "Atividade registrada com sucesso",
        "activity": {
            "id": activity.id,
            "user_id": activity.user_id,
            "date": activity.date,
            "average_rate": activity.average_rate,
            "maximium_rate": activity.maximium_rate,
            "active_time": activity.active_time,
            "intensity": activity.intensity,
            "time_recovery": activity.time_recovery,
            "quant_sessions": activity.quant_sessions
        }
    }), 201

@app.route('/api/bpm', methods=["GET"])
def get_bpm():
    user_id = request.args.get("user_id", type=int)

    query = db_session.query(Measurement_bpm)

    if user_id:
        query = query.filter(Measurement_bpm.user_id == user_id)
    
    measurements = query.order_by(
        Measurement_bpm.date_time.desc()
    ).all()

    return jsonify([
        {
            "id": measurement.id,
            "user_id": measurement.user_id,
            "activity_id": measurement.activity_id,
            "bpm": measurement.bpm,
            "date_time": measurement.date_time
        }
        for measurement in measurements
    ])

@app.route('/api/bpm', methods=["POST"])
def create_bpm():
    data = request.get_json()

    measurement = Measurement_bpm(
        user_id=data.get("user_id"),
        activity_id=data.get("activity_id"),
        bpm=data.get("bpm")
    )

    db_session.add(measurement)
    db_session.commit()
    db_session.refresh(measurement)

    return jsonify({
        "message": "Medição de BPM registrada com sucesso",
        "measurement": {
            "id": measurement.id,
            "user_id": measurement.user_id,
            "activity_id": measurement.activity_id,
            "bpm": measurement.bpm,
            "date_time": measurement.date_time
        }
    }), 201

@app.route('/api/cardiac-zones', methods=["GET"])
def get_cardiac_zones():
    user_id = request.args.get("user_id", type=int)

    query = db_session.query(Cardiac_zone)

    if user_id:
        query = query.filter(Cardiac_zone.user_id == user_id)
    
    zones = query.order_by(Cardiac_zone.date.desc()).all()

    return jsonify([
        {
            "id": zone.id,
            "user_id": zone.user_id,
            "date": zone.date,
            "zone": zone.zone,
            "intensity": zone.intensity,
            "minutes": zone.minutes
        }
        for zone in zones
    ])

@app.route('/api/cardiac-zones', methods=["POST"])
def create_cardiac_zones():
    data = request.get_json()

    zone = Cardiac_zone(
        user_id=data.get("user_id"),
        date=data.get("date"),
        zone=data.get("zone"),
        intensity=data.get("intensity"),
        minutes=data.get("minutes")
    )

    db_session.add(zone)
    db_session.commit()
    db_session.refresh(zone)

    return jsonify({
        "message": "Zona cardíaca registrada com sucesso",
        "zone": {
            "id": zone.id,
            "user_id": zone.user_id,
            "date": zone.date,
            "zone": zone.zone,
            "intensity": zone.intensity,
            "minutes": zone.minutes
        }
    }), 201

@app.route('/api/recoveries', methods=["GET"])
def get_recoveries():
    user_id = request.args.get("user_id", type=int)

    query = db_session.query(Recovery)

    if user_id:
        query = query.filter(Recovery.user_id == user_id)
    
    recoveries = query.order_by(Recovery.date.desc()).all()

    return jsonify([
        {
           "id": recovery.id,
            "user_id": recovery.user_id,
            "date": recovery.date,
            "final_bpm": recovery.final_bpm,
            "bpm_1_min": recovery.bpm_1_min,
            "bpm_2_min": recovery.bpm_2_min,
            "queda_2_min": recovery.queda_2_min
        }
        for recovery in recoveries
    ])

@app.route('/api/recoveries', methods=["POST"])
def create_recoveries():
    data = request.get_json()

    recovery = Recovery(
        user_id=data.get("user_id"),
        date=data.get("date"),
        final_bpm=data.get("final_bpm"),
        bpm_1_min=data.get("bpm_1_min"),
        bpm_2_min=data.get("bpm_2_min"),
        queda_2_min=data.get("queda_2_min")
    )

    db_session.add(recovery)
    db_session.commit()
    db_session.refresh(recovery)

    return jsonify({
        "message": "Recuperação registrada com sucesso",
        "recovery": {
            "id": recovery.id,
            "user_id": recovery.user_id,
            "date": recovery.date,
            "final_bpm": recovery.final_bpm,
            "bpm_1_min": recovery.bpm_1_min,
            "bpm_2_min": recovery.bpm_2_min,
            "queda_2_min": recovery.queda_2_min
        }
    }), 201

@app.route('/api/weekly-goals', methods=["GET"])
def get_weekly_goals():
    user_id = request.args.get("user_id", type=int)

    query = db_session.query(Goal_weekly)

    if user_id:
        query = query.filter(Goal_weekly.user_id == user_id)
    
    goals = query.order_by(Goal_weekly.date.desc()).all()

    return jsonify([
        {
        "id": goal.id,
        "user_id": goal.user_id,
        "beggining_week": goal.beggining_week,
        "end_week": goal.end_week,
        "goal_activity": goal.goal_activity,
        "activity_completed": goal.activity_completed,
        "goal_intensity": goal.goal_intensity,
        "intensity_completed": goal.intensity_completed,
        "goal_sessions": goal.goal_sessions,
        "sessions_completed": goal.sessions_completed
    }
        for goal in goals
    ])

@app.route('/api/weekly-goals', methods=["POST"])
def create_weekly_goals():
    data = request.get_json()

    goal = Goal_weekly(
        user_id=data.get("user_id"),
        beggining_week=data.get("beggining_week"),
        end_week=data.get("end_week"),
        goal_activity=data.get("goal_activity"),
        activity_completed=data.get("activity_completed", 0),
        goal_intensity=data.get("goal_intensity"),
        intensity_completed=data.get("intensity_completed", 0),
        goal_sessions=data.get("goal_sessions"),
        sessions_completed=data.get("sessions_completed", 0)
    )

    db_session.add(goal)
    db_session.commit()
    db_session.refresh(goal)

    return jsonify({
        "message": "Meta semanal criada com sucesso",
        "goal": {
            "id": goal.id,
            "user_id": goal.user_id,
            "beggining_week": goal.beggining_week,
            "end_week": goal.end_week,
            "goal_activity": goal.goal_activity,
            "activity_completed": goal.activity_completed,
            "goal_intensity": goal.goal_intensity,
            "intensity_completed": goal.intensity_completed,
            "goal_sessions": goal.goal_sessions,
            "sessions_completed": goal.sessions_completed
        }
    }), 201

@app.route('/api/physical-assessments', methods=["GET"])
def get_physical_assessments():
    user_id = request.args.get("user_id", type=int)

    query = db_session.query(Physical_assessment)

    if user_id:
        query = query.filter(
            Physical_assessment.user_id == user_id
        )

    assessments = query.order_by(
        Physical_assessment.beggining_date.desc()
    ).all()

    return jsonify([
        {
            "id": assessment.id,
            "user_id": assessment.user_id,
            "beggining_date": assessment.beggining_date,
            "end_date": assessment.end_date,
            "average_fc": assessment.average_fc,
            "active_time": assessment.active_time,
            "quant_sessions": assessment.quant_sessions
        }
        for assessment in assessments
    ])

# ANSIEDADE
@app.route('/api/anxiety/episodes', methods=["GET"])
def get_anxiety_episodes():
    user_id = request.args.get("user_id", type=int)

    query = db_session.query(Episode_anxious)

    if user_id:
        query = query.filter(
            Episode_anxious.user_id == user_id
        )

    episodes = query.order_by(
        Episode_anxious.beggining_date.desc()
    ).all()

    return jsonify([
       {
            "id": episode.id,
            "user_id": episode.user_id,
            "date_time": episode.date_time,
            "level_anxious": episode.level_anxious,
            "cardiac_rate": episode.cardiac_rate,
            "minutes": episode.minutes,
            "observation": episode.observation
        }
        for episode in episodes
    ])

@app.route('/api/anxiety/episodes', methods=["POST"])
def create_anxiety_episodes():
    data = request.get_json()

    episode = Episode_anxious(
        user_id=data.get("user_id"),
        level_anxious=data.get("level_anxious"),
        cardiac_rate=data.get("cardiac_rate"),
        minutes=data.get("minutes"),
        observation=data.get("observation")
    )

    db_session.add(episode)
    db_session.commit()
    db_session.refresh(episode)

    return jsonify({
        "message": "Episódio de ansiedade registrado com sucesso",
        "episode": {
            "id": episode.id,
            "user_id": episode.user_id,
            "date_time": episode.date_time,
            "level_anxious": episode.level_anxious,
            "cardiac_rate": episode.cardiac_rate,
            "minutes": episode.minutes,
            "observation": episode.observation
        }
    }), 201

@app.route('/api/anxiety/summary', methods=["GET"])
def anxiety_summary():
    user_id = request.args.get("user_id", type=int)

    if not user_id:
        return jsonify({
            "error": "user_id é obrigatório"
        }), 400

    episodes = db_session.query(Episode_anxious).filter(
        Episode_anxious.user_id == user_id
    ).all()

    if not episodes:
        return jsonify({
            "total_episodes": 0,
            "average_level": 0,
            "average_bpm": 0,
            "total_minutes": 0
        })

    levels = [
        episode.level_anxious
        for episode in episodes
        if episode.level_anxious is not None
    ]

    bpms = [
        episode.cardiac_rate
        for episode in episodes
        if episode.cardiac_rate is not None
    ]

    minutes = [
        episode.minutes
        for episode in episodes
        if episode.minutes is not None
    ]

    average_level = sum(levels) / len(levels) if levels else 0
    average_bpm = sum(bpms) / len(bpms) if bpms else 0
    total_minutes = sum(minutes)

    return jsonify({
        "total_episodes": len(episodes),
        "average_level": round(average_level, 2),
        "average_bpm": round(average_bpm, 2),
        "total_minutes": total_minutes
    })

@app.route('/api/anxiety/trend', methods=["GET"])
def anxiety_trend():
    user_id = request.args.get("user_id", type=int)

    if not user_id:
        return jsonify({
            "error": "user_id é obrigatório"
        }), 400

    episodes = db_session.query(Episode_anxious).filter(
        Episode_anxious.user_id == user_id
    ).order_by(
        Episode_anxious.date_time.asc()
    ).all()

    return jsonify([
        {
            "date": episode.date_time,
            "level": episode.level_anxious,
            "bpm": episode.cardiac_rate
        }
        for episode in episodes
    ])

#PRESSÃO
@app.route('/api/pressure', methods=["GET"])
def get_pressure():
    user_id = request.args.get("user_id", type=int)

    query = db_session.query(Measurement_pressure)

    if user_id:
        query = query.filter(
            Measurement_pressure.user_id == user_id
        )

    measurements = query.order_by(
        Measurement_pressure.date_time.desc()
    ).all()

    return jsonify([
        {
            "id": measurement.id,
            "user_id": measurement.user_id,
            "date_time": measurement.date_time,
            "sistolica": measurement.sistolica,
            "diastolica": measurement.diastolica,
            "cardiac_rate": measurement.cardiac_rate,
            "origin": measurement.origin,
            "observation": measurement.observation
        }
        for measurement in measurements
    ])

@app.route('/api/pressure', methods=["POST"])
def create_pressure():
    data = request.get_json()

    measurement = Measurement_pressure(
        user_id=data.get("user_id"),
        sistolica=data.get("sistolica"),
        diastolica=data.get("diastolica"),
        cardiac_rate=data.get("cardiac_rate"),
        origin=data.get("origin"),
        observation=data.get("observation")
    )

    db_session.add(measurement)
    db_session.commit()
    db_session.refresh(measurement)

    return jsonify({
        "message": "Medição de pressão registrada com sucesso",
        "pressure": {
            "id": measurement.id,
            "user_id": measurement.user_id,
            "date_time": measurement.date_time,
            "sistolica": measurement.sistolica,
            "diastolica": measurement.diastolica,
            "cardiac_rate": measurement.cardiac_rate,
            "origin": measurement.origin,
            "observation": measurement.observation
        }
    }), 201

@app.route('/api/pressure/summary', methods=["GET"])
def pressure_summary():
    user_id = request.args.get("user_id", type=int)

    if not user_id:
        return jsonify({
            "error": "user_id é obrigatório"
        }), 400

    measurements = db_session.query(
        Measurement_pressure
    ).filter(
        Measurement_pressure.user_id == user_id
    ).all()

    if not measurements:
        return jsonify({
            "total_measurements": 0,
            "average_systolic": 0,
            "average_diastolic": 0,
            "average_bpm": 0
        })

    systolic = [
        measurement.sistolica
        for measurement in measurements
        if measurement.sistolica is not None
    ]

    diastolic = [
        measurement.diastolica
        for measurement in measurements
        if measurement.diastolica is not None
    ]

    bpms = [
        measurement.cardiac_rate
        for measurement in measurements
        if measurement.cardiac_rate is not None
    ]

    average_systolic = (
        sum(systolic) / len(systolic)
        if systolic else 0
    )

    average_diastolic = (
        sum(diastolic) / len(diastolic)
        if diastolic else 0
    )

    average_bpm = (
        sum(bpms) / len(bpms)
        if bpms else 0
    )

    return jsonify({
        "total_measurements": len(measurements),
        "average_systolic": round(average_systolic, 2),
        "average_diastolic": round(average_diastolic, 2),
        "average_bpm": round(average_bpm, 2)
    })

@app.route('/api/pressure/history', methods=["GET"])
def pressure_history():
    user_id = request.args.get("user_id", type=int)

    if not user_id:
        return jsonify({
            "error": "user_id é obrigatório"
        }), 400

    measurements = db_session.query(
        Measurement_pressure
    ).filter(
        Measurement_pressure.user_id == user_id
    ).order_by(
        Measurement_pressure.date_time.asc()
    ).all()

    return jsonify([
        {
            "id": measurement.id,
            "date": measurement.date_time,
            "sistolica": measurement.sistolica,
            "diastolica": measurement.diastolica,
            "cardiac_rate": measurement.cardiac_rate,
            "origin": measurement.origin
        }
        for measurement in measurements
    ])

@app.route('/api/ppg/latest', methods=["GET"])
def get_latest_ppg():
    user_id = request.args.get("user_id", type=int)

    if not user_id:
        return jsonify({
            "error": "user_id é obrigatório"
        }), 400

    ppg = db_session.query(Measurement_ppg).filter(
        Measurement_ppg.user_id == user_id
    ).order_by(
        Measurement_ppg.date_time.desc()
    ).first()

    if not ppg:
        return jsonify({
            "error": "Nenhuma medição PPG encontrada"
        }), 404

    return jsonify({
        "id": ppg.id,
        "user_id": ppg.user_id,
        "measurement_preassure_id": ppg.measurement_preassure_id,
        "cardiac_rate": ppg.cardiac_rate,
        "hrv": ppg.hrv,
        "quality_sign": ppg.quality_sign,
        "date_time": ppg.date_time
    })

@app.route('/api/pressure/warnings', methods=["GET"])
def get_pressure_warnings():
    user_id = request.args.get("user_id", type=int)

    query = db_session.query(Warning_pressure)

    if user_id:
        query = query.filter(
            Warning_pressure.user_id == user_id
        )

    warnings = query.order_by(
        Warning_pressure.data.desc()
    ).all()

    return jsonify([
        {
            "id": warning.id,
            "user_id": warning.user_id,
            "data": warning.data,
            "title": warning.title,
            "message": warning.message,
            "level": warning.level,
            "viewed": warning.viewed
        }
        for warning in warnings
    ])

@app.route('/api/pressure/warnings', methods=["POST"])
def create_pressure_warning():
    data = request.get_json()

    warning = Warning_pressure(
        user_id=data.get("user_id"),
        data=data.get("data"),
        title=data.get("title"),
        message=data.get("message"),
        level=data.get("level"),
        viewed=data.get("viewed", False)
    )

    db_session.add(warning)
    db_session.commit()
    db_session.refresh(warning)

    return jsonify({
        "message": "Alerta criado com sucesso",
        "warning": {
            "id": warning.id,
            "user_id": warning.user_id,
            "data": warning.data,
            "title": warning.title,
            "message": warning.message,
            "level": warning.level,
            "viewed": warning.viewed
        }
    }), 201

# RELATÓRIO
@app.route('/api/reports/weekly', methods=["GET"])
def get_weekly_report():
    user_id = request.args.get("user_id", type=int)

    if not user_id:
        return jsonify({
            "error": "user_id é obrigatório"
        }), 400

    report = db_session.query(Report_weekly).filter(
        Report_weekly.user_id == user_id
    ).order_by(
        Report_weekly.beggining_date.desc()
    ).first()

    if not report:
        return jsonify({
            "message": "Nenhum relatório semanal encontrado"
        }), 404

    # ATIVIDADES
    activities = db_session.query(Activity).filter(
        Activity.user_id == user_id,
        Activity.date >= report.beggining_date,
        Activity.date <= report.end_date
    ).all()

    # ANSIEDADE
    anxiety_episodes = db_session.query(Episode_anxious).filter(
        Episode_anxious.user_id == user_id,
        Episode_anxious.date_time >= report.beggining_date,
        Episode_anxious.date_time <= report.end_date
    ).all()

    # PRESSÃO
    pressure_measurements = db_session.query(
        Measurement_pressure
    ).filter(
        Measurement_pressure.user_id == user_id,
        Measurement_pressure.date_time >= report.beggining_date,
        Measurement_pressure.date_time <= report.end_date
    ).all()

    # CÁLCULOS

    total_activities = len(activities)

    total_active_time = sum(
        activity.active_time
        for activity in activities
        if activity.active_time is not None
        and isinstance(activity.active_time, (int, float))
    )

    total_anxiety_episodes = len(anxiety_episodes)

    anxiety_levels = [
        episode.level_anxious
        for episode in anxiety_episodes
        if episode.level_anxious is not None
    ]

    average_anxiety = (
        sum(anxiety_levels) / len(anxiety_levels)
        if anxiety_levels else 0
    )

    total_pressure_measurements = len(pressure_measurements)

    return jsonify({
        "id": report.id,
        "user_id": report.user_id,
        "beggining_date": report.beggining_date,
        "end_date": report.end_date,
        "created_at": report.created_at,

        "performance": {
            "total_activities": total_activities,
            "total_active_time": total_active_time
        },

        "anxiety": {
            "total_episodes": total_anxiety_episodes,
            "average_level": round(average_anxiety, 2)
        },

        "pressure": {
            "total_measurements": total_pressure_measurements
        }
    })

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    print("Sucesso!")