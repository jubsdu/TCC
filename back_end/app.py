import os
import logging
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash
from database import SessionLocal, init_db
from models import Measurement_ia, User, Category, Checkup, Activity, Cardiac_zone, Recovery, Physical_assessment, Goal_weekly, Measurement_bpm, Episode_anxious, Trigger, Episode_trigger, Tecnic, Episode_tecniques, Accompaniment, Measurement_pressure, Measurement_ppg, Warning_pressure, Report_weekly, Assessment_anxious
from simulador_ia import create_live_reading, seed_global_choices, seed_user_data

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "vitapulse-chave-local-trocar-em-producao")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "0") == "1",
    MAX_CONTENT_LENGTH=2 * 1024 * 1024,
)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("vitapulse")
# scoped_session mantém compatibilidade com as consultas do app original e permite
# liberar a sessão corretamente ao fim de cada requisição.
db_session = SessionLocal

# Cria as tabelas necessárias na primeira execução e aplica as migrações simples.
init_db()


@app.teardown_appcontext
def cleanup_db_session(_exception=None):
    if _exception is not None:
        db_session.rollback()
    db_session.remove()


def _current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    user = db_session.query(User).filter_by(id=user_id).first()
    if user is None:
        session.clear()
    return user


def _require_user(completed=True):
    user = _current_user()
    if user is None:
        return None, redirect(url_for("login"))
    if completed and not getattr(user, "onboarding_completed", True):
        target = "onboarding_treatment" if user.onboarding_reason else "onboarding_reason"
        return None, redirect(url_for(target))
    return user, None


def _safe_password_check(stored_password, candidate):
    if not stored_password:
        return False
    # Contas antigas usavam texto puro; aceitamos uma vez e migram para hash no login.
    if stored_password.startswith(("pbkdf2:", "scrypt:")):
        try:
            return check_password_hash(stored_password, candidate)
        except (ValueError, TypeError):
            return False
    return stored_password == candidate


def _ensure_user_data(user):
    # A função do simulador evita duplicar conjuntos já completos e preenche tabelas ausentes.
    seed_global_choices(db_session)
    seed_user_data(db_session, user.id)


def _bpm_stats(user_id, limit=120):
    readings = (
        db_session.query(Measurement_ia)
        .filter(Measurement_ia.user_id == user_id)
        .order_by(Measurement_ia.date_time.desc())
        .limit(limit)
        .all()
    )
    values = [int(item.bpm) for item in readings if item.bpm is not None]
    latest = readings[0] if readings else None
    return {
        "latest": latest,
        "current": int(latest.bpm) if latest and latest.bpm is not None else 0,
        "minimum": min(values) if values else 0,
        "maximum": max(values) if values else 0,
        "average": round(sum(values) / len(values), 1) if values else 0,
        "readings": readings,
    }

@app.route('/')
def index():
    return render_template('index.html')

# Home
import random
from datetime import date, datetime, timezone, timedelta

# @app.route('/home')
# def home():
#     user_id = session.get('user_id')

#     if not user_id:
#         return redirect(url_for('login'))

#     user = db_session.query(User).filter_by(id=user_id).first()

#     if not user:
#         session.clear()
#         return redirect(url_for('login'))

#     return render_template('home.html', user=user)

@app.route('/api/ia-data', methods=['GET', 'POST'])
def api_ia_data():
    """Compatibilidade com a API antiga, limitada à conta autenticada."""
    user, error_response = _require_user(completed=False)
    if error_response:
        return jsonify({"erro": "Autenticação necessária."}), 401

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        try:
            bpm = int(data.get("bpm"))
        except (TypeError, ValueError):
            return jsonify({"erro": "O campo bpm precisa ser numérico."}), 400
        if not 35 <= bpm <= 220:
            return jsonify({"erro": "BPM fora do limite permitido."}), 400
        try:
            rr = data.get("rr")
            if rr is None:
                rr = round(60000 / bpm, 2)
            rmssd = data.get("rmssd")
            if rmssd is None:
                # O registro enviado continua sendo guardado; RMSSD recebe uma estimativa
                # sintética apenas quando o cliente não a forneceu.
                rmssd = round(random.uniform(20.0, 65.0), 2)
            resultado_ia = data.get("resultado_ia")
            probabilidade_ia = data.get("probabilidade_ia")
            if resultado_ia is None or probabilidade_ia is None:
                from simulador_ia import predict_synthetic_sample
                prediction, probability = predict_synthetic_sample(bpm, float(rmssd))
                if resultado_ia is None:
                    resultado_ia = prediction
                if probabilidade_ia is None:
                    probabilidade_ia = probability
            parsed_date = data.get("horario") or data.get("date_time")
            recorded_at = datetime.fromisoformat(parsed_date) if parsed_date else datetime.now()
            values = [float(item.bpm) for item in db_session.query(Measurement_ia)
                      .filter_by(user_id=user.id).order_by(Measurement_ia.date_time.desc()).limit(14).all()
                      if item.bpm is not None]
            average = data.get("bpm_medio")
            if average is None:
                average = round((sum(values) + bpm) / (len(values) + 1), 2)
            reading = Measurement_ia(
                user_id=user.id, bpm=bpm, rr=rr, rmssd=rmssd,
                bpm_medio=average, resultado_ia=resultado_ia,
                probabilidade_ia=probabilidade_ia, date_time=recorded_at,
            )
            db_session.add(reading)
            db_session.commit()
            db_session.refresh(reading)
            return jsonify({"status": "ok", "mensagem": "Medida registrada.",
                            "id": reading.id, "simulated": True}), 201
        except Exception:
            db_session.rollback()
            logger.exception("Erro ao salvar medida IA")
            return jsonify({"erro": "Erro ao salvar a medição."}), 500

    rows = (db_session.query(Measurement_ia).filter_by(user_id=user.id)
            .order_by(Measurement_ia.date_time.desc()).limit(100).all())
    return jsonify([{
        "id": item.id,
        "user_id": item.user_id,
        "bpm": item.bpm,
        "rr": float(item.rr) if item.rr is not None else None,
        "rmssd": float(item.rmssd) if item.rmssd is not None else None,
        "bpm_medio": float(item.bpm_medio) if item.bpm_medio is not None else None,
        "resultado_ia": item.resultado_ia,
        "probabilidade_ia": float(item.probabilidade_ia) if item.probabilidade_ia is not None else None,
        "date_time": item.date_time.isoformat() if item.date_time else None,
        "simulated": True,
    } for item in rows])

# Autenticação e Conta
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        user = db_session.query(User).filter(func.lower(User.email) == email).first()
        if user is None or not _safe_password_check(user.password, password):
            return render_template('login.html', error='Email ou senha inválidos.'), 401

        # Migra a senha de texto puro das versões antigas para hash com salt.
        if user.password and not user.password.startswith(('pbkdf2:', 'scrypt:')):
            user.password = generate_password_hash(password)
            db_session.commit()

        session.clear()
        session['user_id'] = user.id
        if getattr(user, 'onboarding_completed', True):
            _ensure_user_data(user)
            return redirect(url_for('home'))
        return redirect(url_for('onboarding_treatment' if user.onboarding_reason else 'onboarding_reason'))

    return render_template('login.html', error=None)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        phone = (request.form.get('phone') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''

        if not name or not email or not password:
            return render_template('register.html', error='Preencha nome, email e senha.'), 400
        if len(password) < 6:
            return render_template('register.html', error='A senha precisa ter pelo menos 6 caracteres.'), 400
        if db_session.query(User).filter(func.lower(User.email) == email).first():
            return render_template('register.html', error='Este email já está cadastrado.'), 409

        user = User(
            name=name[:50], phone=phone[:20] or None, email=email[:100],
            password=generate_password_hash(password), onboarding_completed=False,
        )
        try:
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
        except IntegrityError:
            db_session.rollback()
            return render_template('register.html', error='Este email já está cadastrado.'), 409
        except Exception:
            db_session.rollback()
            logger.exception('Falha ao criar conta')
            return render_template('register.html', error='O cadastro falhou. Tente novamente.'), 500

        session.clear()
        session['user_id'] = user.id
        return redirect(url_for('onboarding_reason'))

    return render_template('register.html', error=None)


def criar_dados_iniciais(user_id):
    print(f"CRIANDO DADOS INICIAIS PARA USUÁRIO {user_id}")

    # ==========================================
    # 1. ATIVIDADE
    # ==========================================
    
    activity = Activity(
        user_id=user_id,
        date=date.today() - timedelta(days=random.randint(0, 7)),
        average_rate=random.randint(70, 100),
        maximum_rate=random.randint(120, 160),
        active_time=random.randint(30, 240),
        intensity=random.choice([
            "Zona 2",
            "Zona 3",
            "Zona 4"
        ]),
        time_recovery=random.randint(15, 60),
        quant_sessions=random.randint(1, 5)
    )

    db_session.add(activity)
    db_session.flush()

    # ==========================================
    # 2. MEDIÇÕES DE BPM
    # ==========================================

    for i in range(5):

        measurement = Measurement_bpm(
            user_id=user_id,
            activity_id=activity.id,
            bpm=random.randint(60, 140),
            date_time=datetime.now(timezone.utc) - timedelta(
                hours=random.randint(1, 48)
            )
        )

        db_session.add(measurement)

    # ==========================================
    # 3. CHECKUPS RECENTES
    # ==========================================

    for i in range(2):

        checkup = Checkup(
            user_id=user_id,
            type=random.choice([
                "Checkup geral",
                "Avaliação física",
                "Acompanhamento"
            ]),
            date=date.today() - timedelta(days=i + 1),
            average_bpm=random.randint(70, 100),
            observation="Checkup realizado com sucesso."
        )

        db_session.add(checkup)

    # ==========================================
    # 4. SALVA TUDO
    # ==========================================

    db_session.commit()
    print(f"DADOS INICIAIS DO USUÁRIO {user_id} CRIADOS!")

def criar_dados_performance(user_id):

    print(f"CRIANDO PERFORMANCE PARA USUÁRIO {user_id}")

    hoje = date.today()

    # ==========================================
    # ATIVIDADE DA SEMANA
    # ==========================================

    data_atividade = hoje - timedelta(days=1)

    media_bpm = random.randint(70, 90)
    max_bpm = random.randint(130, 170)

    atividade = Activity(
        user_id=user_id,
        date=data_atividade,
        average_rate=media_bpm,
        maximum_rate=max_bpm,
        active_time=random.randint(180, 240),
        intensity=random.choice([
            "Zona 3",
            "Zona 4"
        ]),
        time_recovery=random.randint(25, 45),
        quant_sessions=random.randint(3, 5)
    )

    db_session.add(atividade)
    db_session.flush()

    # ==========================================
    # ZONAS CARDÍACAS
    # ==========================================

    zonas = [
        ("Zona 1", "Muito leve", random.randint(8, 20)),
        ("Zona 2", "Leve/moderada", random.randint(15, 35)),
        ("Zona 3", "Moderada", random.randint(15, 30)),
        ("Zona 4", "Intensa", random.randint(5, 15)),
        ("Zona 5", "Muito intensa", random.randint(1, 5))
    ]

    for zona, intensidade, minutos in zonas:

        db_session.add(
            Cardiac_zone(
                user_id=user_id,
                date=data_atividade,
                zone=zona,
                intensity=intensidade,
                minutes=minutos
            )
        )

    # ==========================================
    # RECUPERAÇÃO
    # ==========================================

    final_bpm = random.randint(150, 175)
    bpm_1 = random.randint(120, 145)
    bpm_2 = random.randint(105, 125)

    queda_2 = final_bpm - bpm_2

    db_session.add(
        Recovery(
            user_id=user_id,
            date=data_atividade,
            final_bpm=final_bpm,
            bpm_1_min=bpm_1,
            bpm_2_min=bpm_2,
            queda_2_min=queda_2
        )
    )

    # ==========================================
    # EVOLUÇÃO / AVALIAÇÃO FÍSICA
    # ==========================================

    inicio_semana = hoje - timedelta(days=6)

    db_session.add(
        Physical_assessment(
            user_id=user_id,
            beggining_date=inicio_semana,
            end_date=hoje,
            average_fc=media_bpm,
            active_time=atividade.active_time,
            quant_sessions=atividade.quant_sessions
        )
    )

    # ==========================================
    # METAS DA SEMANA
    # ==========================================

    meta_atividade = 150
    atividade_realizada = random.randint(100, 150)

    meta_intensidade = 90
    intensidade_realizada = random.randint(45, 90)

    meta_sessoes = 4
    sessoes_realizadas = random.randint(2, 4)

    db_session.add(
        Goal_weekly(
            user_id=user_id,
            beginning_week=inicio_semana,
            end_week=hoje,

            goal_activity=meta_atividade,
            activity_completed=atividade_realizada,

            goal_intensity=meta_intensidade,
            intensity_completed=intensidade_realizada,

            goal_sessions=meta_sessoes,
            sessions_completed=sessoes_realizadas
        )
    )

    # ==========================================
    # MEDIÇÕES DE BPM
    # ==========================================

    for i in range(8):

        db_session.add(
            Measurement_bpm(
                user_id=user_id,
                activity_id=atividade.id,
                bpm=random.randint(65, max_bpm),
                date_time=datetime.now(timezone.utc)
                - timedelta(hours=random.randint(1, 72))
            )
        )

    db_session.commit()

    print(f"PERFORMANCE DO USUÁRIO {user_id} CRIADA!")

def criar_dados_ansiedade(user_id):

    print("Criando dados de ansiedade para usuário:", user_id)

    # =========================================================
    # 1. ACOMPANHAMENTO
    # =========================================================

    acompanhamento = db_session.query(Accompaniment).filter_by(
        user_id=user_id
    ).first()

    if not acompanhamento:

        acompanhamento = Accompaniment(
            user_id=user_id,
            psychotherapy=False,
            consultation=False,
            medication=False
        )

        db_session.add(acompanhamento)

        print("Acompanhamento criado.")

    # =========================================================
    # 2. GATILHOS
    # =========================================================

    trigger_names = [
        "Estudos",
        "Sono",
        "Social"
    ]

    triggers = {}

    for name in trigger_names:

        trigger = db_session.query(Trigger).filter_by(
            name=name
        ).first()

        if not trigger:

            trigger = Trigger(
                name=name
            )

            db_session.add(trigger)
            db_session.flush()

            print("Gatilho criado:", name)

        triggers[name] = trigger


    # =========================================================
    # 3. TÉCNICAS
    # =========================================================

    tecnic_names = [
        ("Relaxamento", "Técnica de relaxamento", "relaxamento-icon.png"),
        ("Aterramento", "Técnica de aterramento", "aterramento-icon.png"),
        ("Registrar sentimentos", "Registro dos sentimentos percebidos", "registrar-icon.png")
    ]

    tecnicas = {}

    for name, description, icon in tecnic_names:

        tecnic = db_session.query(Tecnic).filter_by(
            name=name
        ).first()

        if not tecnic:

            tecnic = Tecnic(
                name=name,
                description=description,
                icon=icon
            )

            db_session.add(tecnic)
            db_session.flush()

            print("Técnica criada:", name)

        else:

            tecnic.description = description
            tecnic.icon = icon

            print("Técnica atualizada:", name)

        tecnicas[name] = tecnic

    # =========================================================
    # 4. VERIFICA SE O USUÁRIO JÁ POSSUI EPISÓDIOS
    # =========================================================

    episode_exists = db_session.query(Episode_anxious).filter_by(
        user_id=user_id
    ).first()

    if episode_exists:

        print("Dados de ansiedade já existem para este usuário.")

        db_session.commit()

        return

    # =========================================================
    # 5. EPISÓDIOS DE ANSIEDADE
    # =========================================================

    hoje = datetime.now()

    data_inicio = (
        hoje - timedelta(days=hoje.weekday())
    ).replace(
        hour=9,
        minute=0,
        second=0,
        microsecond=0
    )

    episodios = [

        {
            "dia": 0,
            "hora": 14,
            "nivel": 6,
            "bpm": 91,
            "minutos": 15,
            "observacao": "Ansiedade durante os estudos.",
            "gatilho": "Estudos",
            "tecnica": "Respiração"
        },

        {
            "dia": 0,
            "hora": 17,
            "nivel": 7,
            "bpm": 104,
            "minutos": 18,
            "observacao": "Sensação de ansiedade durante período de estudos.",
            "gatilho": "Estudos",
            "tecnica": "Relaxamento"
        },

        {
            "dia": 1,
            "hora": 10,
            "nivel": 5,
            "bpm": 88,
            "minutos": 12,
            "observacao": "Episódio leve durante a manhã.",
            "gatilho": "Sono",
            "tecnica": "Respiração"
        },

        {
            "dia": 2,
            "hora": 15,
            "nivel": 8,
            "bpm": 112,
            "minutos": 25,
            "observacao": "Ansiedade elevada durante estudos.",
            "gatilho": "Estudos",
            "tecnica": "Aterramento"
        },

        {
            "dia": 5,
            "hora": 16,
            "nivel": 6,
            "bpm": 96,
            "minutos": 17,
            "observacao": "Ansiedade associada a situação social.",
            "gatilho": "Social",
            "tecnica": "Relaxamento"
        },

        {
            "dia": 6,
            "hora": 9,
            "nivel": 5,
            "bpm": 87,
            "minutos": 14,
            "observacao": "Episódio leve pela manhã.",
            "gatilho": "Sono",
            "tecnica": "Respiração"
        },

        {
            "dia": 6,
            "hora": 18,
            "nivel": 7,
            "bpm": 101,
            "minutos": 25,
            "observacao": "Ansiedade durante interação social.",
            "gatilho": "Social",
            "tecnica": "Registrar sentimentos"
        }
    ]

    for dados in episodios:

        data_episodio = data_inicio + timedelta(days=dados["dia"])

        data_episodio = data_episodio.replace(
            hour=dados["hora"],
            minute=random.choice([0, 15, 30, 45])
        )

        episodio = Episode_anxious(
            user_id=user_id,
            date_time=data_episodio,
            level_anxious=dados["nivel"],
            cardiac_rate=dados["bpm"],
            minutes=dados["minutos"],
            observation=dados["observacao"]
        )

        db_session.add(episodio)
        db_session.flush()

        # =====================================================
        # GATILHO DO EPISÓDIO
        # =====================================================

        episode_trigger = Episode_trigger(
            episode_id=episodio.id,
            trigger_id=triggers[dados["gatilho"]].id
        )

        db_session.add(episode_trigger)

        # =====================================================
        # TÉCNICA UTILIZADA
        # =====================================================

        episode_tecnic = Episode_tecniques(
            episode_id=episodio.id,
            tecnic_id=tecnicas[dados["tecnica"]].id
        )

        db_session.add(episode_tecnic)

    # =========================================================
    # 6. SALVA TUDO
    # =========================================================

    db_session.commit()

    print("Dados de ansiedade criados com sucesso!")

# =========================================================
# CRIAR DADOS DE PRESSÃO ARTERIAL
# =========================================================

def criar_dados_pressao(user_id):

    print("Criando dados de pressão para usuário:", user_id)

    # Verifica se o usuário já possui dados
    pressure_exists = db_session.query(
        Measurement_pressure
    ).filter_by(
        user_id=user_id
    ).first()

    if pressure_exists:
        print("Dados de pressão já existem para este usuário.")
        return

    # ---------------------------------------------------------
    # 1. MEDIÇÕES DE PRESSÃO
    # ---------------------------------------------------------

    data_inicio = datetime(2026, 9, 21, 8, 0)

    measurements = [
        {
            "dia": 0,
            "hora": 8,
            "sistolica": 118,
            "diastolica": 76,
            "bpm": 72,
            "origin": "Manual",
            "observation": "Medição realizada pela manhã."
        },
        {
            "dia": 1,
            "hora": 9,
            "sistolica": 122,
            "diastolica": 79,
            "bpm": 75,
            "origin": "PPG",
            "observation": "Medição realizada após o café da manhã."
        },
        {
            "dia": 2,
            "hora": 14,
            "sistolica": 128,
            "diastolica": 82,
            "bpm": 81,
            "origin": "Manual",
            "observation": "Medição realizada durante a tarde."
        },
        {
            "dia": 3,
            "hora": 10,
            "sistolica": 135,
            "diastolica": 86,
            "bpm": 84,
            "origin": "PPG",
            "observation": "Pressão acima das medições anteriores."
        },
        {
            "dia": 4,
            "hora": 16,
            "sistolica": 125,
            "diastolica": 80,
            "bpm": 78,
            "origin": "Manual",
            "observation": "Medição realizada durante a tarde."
        },
        {
            "dia": 5,
            "hora": 9,
            "sistolica": 119,
            "diastolica": 77,
            "bpm": 70,
            "origin": "PPG",
            "observation": "Medição realizada pela manhã."
        },
        {
            "dia": 6,
            "hora": 18,
            "sistolica": 130,
            "diastolica": 84,
            "bpm": 82,
            "origin": "Manual",
            "observation": "Medição realizada no final do dia."
        }
    ]

    created_measurements = []

    for dados in measurements:

        date_measurement = data_inicio + timedelta(
            days=dados["dia"]
        )

        date_measurement = date_measurement.replace(
            hour=dados["hora"],
            minute=random.choice([0, 15, 30, 45])
        )

        measurement = Measurement_pressure(
            user_id=user_id,
            date_time=date_measurement,
            sistolica=dados["sistolica"],
            diastolica=dados["diastolica"],
            cardiac_rate=dados["bpm"],
            origin=dados["origin"],
            observation=dados["observation"]
        )

        db_session.add(measurement)
        db_session.flush()

        created_measurements.append(measurement)

        print(
            "Medição criada:",
            measurement.sistolica,
            "/",
            measurement.diastolica
        )

    # ---------------------------------------------------------
    # 2. DADOS PPG
    # ---------------------------------------------------------

    for measurement in created_measurements:

        # Criamos PPG somente para medições originadas pelo PPG
        if measurement.origin != "PPG":
            continue

        ppg = Measurement_ppg(
            user_id=user_id,
            measurement_pressure_id=measurement.id,
            cardiac_rate=measurement.cardiac_rate,
            hrv=random.choice([42.5, 45.2, 48.7, 51.3, 55.1]),
            quality_sign=random.choice([91.5, 93.2, 95.7, 97.1, 98.4]),
            date_time=measurement.date_time
        )

        db_session.add(ppg)

        print(
            "PPG criado para medição:",
            measurement.id
        )

    # ---------------------------------------------------------
    # 3. AVISOS
    # ---------------------------------------------------------

    warnings = [
        {
            "dia": 3,
            "title": "Pressão acima do habitual",
            "message": "Foi registrada uma medição de pressão acima das medições anteriores.",
            "level": "atenção"
        },
        {
            "dia": 6,
            "title": "Acompanhe sua pressão",
            "message": "Uma nova medição foi registrada. Continue acompanhando seus dados.",
            "level": "informativo"
        }
    ]

    for warning_data in warnings:

        warning = Warning_pressure(
            user_id=user_id,
            data=(
                data_inicio +
                timedelta(days=warning_data["dia"])
            ).date(),
            title=warning_data["title"],
            message=warning_data["message"],
            level=warning_data["level"],
            viewed=False
        )

        db_session.add(warning)

        print(
            "Aviso criado:",
            warning_data["title"]
        )

    db_session.commit()

    print("Dados de pressão criados com sucesso!")

# =========================================================
# CRIAR DADOS DO RELATÓRIO SEMANAL
# =========================================================

def criar_dados_relatorio(user_id):

    print("Criando relatório semanal para usuário:", user_id)

    # Semana de teste: 21/09/2026 até 27/09/2026
    beginning_date = date(2026, 9, 21)
    end_date = date(2026, 9, 27)

    # Verifica se já existe relatório para esse período
    report_exists = (
        db_session.query(Report_weekly)
        .filter(
            Report_weekly.user_id == user_id,
            Report_weekly.beginning_date == beginning_date,
            Report_weekly.end_date == end_date
        )
        .first()
    )

    if report_exists:

        print("Relatório semanal já existe para este usuário.")

        return report_exists

    # Cria o relatório
    report = Report_weekly(
        user_id=user_id,
        beginning_date=beginning_date,
        end_date=end_date
    )

    db_session.add(report)

    db_session.flush()

    print(
        "Relatório criado:",
        beginning_date,
        "até",
        end_date
    )

    return report

@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        user = db_session.query(User).filter(func.lower(User.email) == email).first()
        session.pop('password_reset_user_id', None)
        session.pop('password_reset_code', None)
        session.pop('password_reset_verified', None)
        if user:
            code = f"{random.randint(0, 9999):04d}"
            session['password_reset_user_id'] = user.id
            session['password_reset_code'] = code
            logger.warning('Código local de recuperação para %s: %s (nenhum email foi enviado)', email, code)
        flash('Se o email estiver cadastrado, o código local aparecerá no terminal do servidor.')
        return redirect(url_for('verification'))
    return render_template('forgot.html')


@app.route('/verification', methods=['GET', 'POST'])
def verification():
    if request.method == 'POST':
        entered = ''.join((request.form.get(f'code_{index}') or '') for index in range(1, 5))
        expected = session.get('password_reset_code')
        if expected and entered == expected and session.get('password_reset_user_id'):
            session['password_reset_verified'] = True
            return redirect(url_for('new_password'))
        return render_template('verification.html', email='', error='Código inválido ou expirado.'), 400
    return render_template('verification.html', email='', error=None)


@app.route('/new-password', methods=['GET', 'POST'])
def new_password():
    if not session.get('password_reset_verified'):
        return redirect(url_for('forgot'))
    if request.method == 'POST':
        password = request.form.get('new_password') or ''
        confirmation = request.form.get('confirm_password') or ''
        if len(password) < 6 or password != confirmation:
            return render_template('new-password.html', error='As senhas devem ser iguais e ter pelo menos 6 caracteres.'), 400
        user = db_session.query(User).filter_by(id=session.get('password_reset_user_id')).first()
        if user is None:
            session.clear()
            return redirect(url_for('forgot'))
        user.password = generate_password_hash(password)
        db_session.commit()
        session.pop('password_reset_user_id', None)
        session.pop('password_reset_code', None)
        session.pop('password_reset_verified', None)
        flash('Senha alterada. Entre com a nova senha.')
        return redirect(url_for('login'))
    return render_template('new-password.html', error=None)


@app.route('/onboarding-reason', methods=['GET', 'POST'])
def onboarding_reason():
    user, error_response = _require_user(completed=False)
    if error_response:
        return error_response

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        reason = (request.form.get('reason') or data.get('reason') or '').strip().lower()
        allowed = {'ansiedade', 'cardiovascular', 'pressao', 'outro'}
        if reason not in allowed:
            return jsonify({'error': 'Selecione um motivo válido.'}), 400
        user.onboarding_reason = reason
        db_session.commit()
        next_url = url_for('onboarding_treatment')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'next': next_url})
        return redirect(next_url)
    return render_template('onboarding-reason.html')


@app.route('/onboarding-treatment', methods=['GET', 'POST'])
def onboarding_treatment():
    user, error_response = _require_user(completed=False)
    if error_response:
        return error_response
    if not user.onboarding_reason:
        return redirect(url_for('onboarding_reason'))

    if request.method == 'POST':
        treatments = [item for item in request.form.getlist('treatment') if item]
        allowed = {'psychotherapy', 'consultation', 'medication', 'nenhum'}
        treatments = [item for item in treatments if item in allowed]
        if 'nenhum' in treatments:
            treatments = []

        accompaniment = db_session.query(Accompaniment).filter_by(user_id=user.id).first()
        if accompaniment is None:
            accompaniment = Accompaniment(user_id=user.id)
            db_session.add(accompaniment)
        accompaniment.psychotherapy = 'psychotherapy' in treatments
        accompaniment.consultation = 'consultation' in treatments
        accompaniment.medication = 'medication' in treatments
        user.onboarding_completed = True
        try:
            db_session.commit()
            _ensure_user_data(user)
        except Exception:
            db_session.rollback()
            logger.exception('Falha ao finalizar onboarding e gerar dados simulados')
            return 'Não foi possível finalizar o cadastro. Tente novamente.', 500
        return redirect(url_for('home'))

    return render_template('onboarding-treatment.html', edit_mode=False, accompaniment=None)


@app.route('/onboarding-treatment-edit', methods=['GET', 'POST'])
def onboarding_treatment_edit():
    user, error_response = _require_user(completed=True)
    if error_response:
        return error_response
    accompaniment = db_session.query(Accompaniment).filter_by(user_id=user.id).first()
    if accompaniment is None:
        accompaniment = Accompaniment(user_id=user.id, psychotherapy=False, consultation=False, medication=False)
        db_session.add(accompaniment)
        db_session.commit()
    if request.method == 'POST':
        treatments = [item for item in request.form.getlist('treatment') if item]
        if 'nenhum' in treatments:
            treatments = []
        accompaniment.psychotherapy = 'psychotherapy' in treatments
        accompaniment.consultation = 'consultation' in treatments
        accompaniment.medication = 'medication' in treatments
        db_session.commit()
        return redirect(url_for('anxiety'))
    return render_template('onboarding-treatment.html', edit_mode=True, accompaniment=accompaniment)


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect(url_for('index'))

# Módulos de Saúde e Monitoramento
from datetime import datetime, timedelta
from sqlalchemy import func

@app.route('/anxiety')
def anxiety():

    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('login'))

    user = db_session.query(User).filter_by(
        id=user_id
    ).first()

    if not user:
        return redirect(url_for('login'))

    _ensure_user_data(user)

    # =====================================================
    # ACOMPANHAMENTO
    # =====================================================

    accompaniment = db_session.query(Accompaniment).filter_by(
        user_id=user_id
    ).first()

    # =====================================================
    # TÉCNICAS USADAS
    # =====================================================

    tecnics = (
        db_session.query(Tecnic)
        .join(
            Episode_tecniques,
            Episode_tecniques.tecnic_id == Tecnic.id
        )
        .join(
            Episode_anxious,
            Episode_anxious.id == Episode_tecniques.episode_id
        )
        .filter(
            Episode_anxious.user_id == user_id
        )
        .distinct()
        .all()
    )

    # =====================================================
    # GATILHOS REGISTRADOS
    # =====================================================

    trigger_counts = (
        db_session.query(
            Trigger.name,
            func.count(Episode_trigger.id)
        )
        .join(
            Episode_trigger,
            Episode_trigger.trigger_id == Trigger.id
        )
        .join(
            Episode_anxious,
            Episode_anxious.id == Episode_trigger.episode_id
        )
        .filter(
            Episode_anxious.user_id == user_id
        )
        .group_by(
            Trigger.name
        )
        .order_by(
            func.count(Episode_trigger.id).desc()
        )
        .all()
    )

    # =====================================================
    # TODOS OS EPISÓDIOS DO USUÁRIO
    # =====================================================

    episodes = (
        db_session.query(Episode_anxious)
        .filter(Episode_anxious.user_id == user_id)
        .order_by(Episode_anxious.date_time.desc())
        .all()
    )

    # =====================================================
    # ÚLTIMOS EPISÓDIOS
    # =====================================================

    latest_episodes = (
        db_session.query(Episode_anxious)
        .filter(
            Episode_anxious.user_id == user_id
        )
        .order_by(
            Episode_anxious.date_time.desc()
        )
        .limit(5)
        .all()
    )

    print("USUÁRIO ANSIEDADE:", user.id, user.email)
    print("EPISÓDIOS:", len(episodes))

    # =====================================================
    # SEMANA ATUAL
    # 21/09 até 27/09
    # =====================================================

    hoje = datetime.now()

    inicio_semana = (
        hoje - timedelta(days=hoje.weekday())
    ).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    fim_semana = inicio_semana + timedelta(days=7)

    episodes_this_week = [
        episode
        for episode in episodes
        if inicio_semana <= episode.date_time < fim_semana
    ]

    print("EPISÓDIOS ESTA SEMANA:", len(episodes_this_week))

    # =====================================================
    # SEMANA ANTERIOR
    # 14/09 até 20/09
    # =====================================================

    inicio_semana_anterior = inicio_semana - timedelta(days=7)
    fim_semana_anterior = inicio_semana

    episodes_previous_week = [
        episode
        for episode in episodes
        if inicio_semana_anterior <= episode.date_time < fim_semana_anterior
    ]

    print(
        "EPISÓDIOS SEMANA ANTERIOR:",
        len(episodes_previous_week)
    )

    # =====================================================
    # MÉDIA DE ANSIEDADE
    # =====================================================

    anxiety_values = [
        episode.level_anxious
        for episode in episodes_this_week
        if episode.level_anxious is not None
    ]

    if anxiety_values:
        average_anxiety = sum(anxiety_values) / len(anxiety_values)
    else:
        average_anxiety = 0

    # =====================================================
    # MÉDIA DE ANSIEDADE DA SEMANA ANTERIOR
    # =====================================================

    previous_anxiety_values = [
        episode.level_anxious
        for episode in episodes_previous_week
        if episode.level_anxious is not None
    ]

    if previous_anxiety_values:
        previous_average_anxiety = (
            sum(previous_anxiety_values) /
            len(previous_anxiety_values)
        )
    else:
        previous_average_anxiety = 0

    # =====================================================
    # BPM
    # =====================================================

    bpm_values = [
        episode.cardiac_rate
        for episode in episodes_this_week
        if episode.cardiac_rate is not None
    ]

    if bpm_values:
        average_bpm = sum(bpm_values) / len(bpm_values)
        max_bpm = max(bpm_values)
    else:
        average_bpm = 0
        max_bpm = 0

    # =====================================================
    # DURAÇÃO MÉDIA
    # =====================================================

    duration_values = [
        episode.minutes
        for episode in episodes_this_week
        if episode.minutes is not None
    ]

    if duration_values:
        average_duration = sum(duration_values) / len(duration_values)
    else:
        average_duration = 0

    # =====================================================
    # EPISÓDIOS POR DIA
    # =====================================================

    dias_semana = [
        "Segunda",
        "Terça",
        "Quarta",
        "Quinta",
        "Sexta",
        "Sábado",
        "Domingo"
    ]

    episodes_by_day = []

    for i, day_name in enumerate(dias_semana):

        data = inicio_semana + timedelta(days=i)

        count = sum(
            1
            for episode in episodes_this_week
            if episode.date_time.date() == data.date()
        )

        episodes_by_day.append({
            "name": day_name,
            "count": count
        })

    # =====================================================
    # HORÁRIO MAIS FREQUENTE
    # =====================================================

    if episodes_this_week:

        hours = [
            episode.date_time.hour
            for episode in episodes_this_week
        ]

        most_common_hour = max(
            set(hours),
            key=hours.count
        )

        most_frequent_time = f"{most_common_hour}h"

    else:

        most_frequent_time = "Sem registros"

    print("MÉDIA ANSIEDADE:", average_anxiety)
    print("MÉDIA BPM:", average_bpm)
    print("BPM MÁXIMO:", max_bpm)
    tecnics = db_session.query(Tecnic).all()
    return render_template(
        'anxiety.html',
        user=user,
        accompaniment=accompaniment,
        episodes=episodes,
        episodes_this_week=episodes_this_week,
        episodes_previous_week=episodes_previous_week,
        episodes_by_day=episodes_by_day,
        average_anxiety=average_anxiety,
        average_bpm=average_bpm,
        max_bpm=max_bpm,
        average_duration=average_duration,
        most_frequent_time=most_frequent_time,
        previous_average_anxiety=previous_average_anxiety,
        tecnics=tecnics,
        latest_episodes=latest_episodes,
        trigger_counts=trigger_counts
    )

@app.route('/performance')
def performance():
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('login'))

    user = db_session.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        return redirect(url_for('login'))

    _ensure_user_data(user)

    # ==========================
    # ATIVIDADE
    # ==========================

    activity = (
        db_session.query(Activity)
        .filter(Activity.user_id == user_id)
        .order_by(Activity.date.desc())
        .first()
    )

    # ==========================
    # ZONAS CARDÍACAS
    # ==========================

    cardiac_zones = (
        db_session.query(Cardiac_zone)
        .filter(Cardiac_zone.user_id == user_id)
        .order_by(Cardiac_zone.date.desc())
        .all()
    )

    # ==========================
    # RECUPERAÇÃO
    # ==========================

    recovery = (
        db_session.query(Recovery)
        .filter(Recovery.user_id == user_id)
        .order_by(Recovery.date.desc())
        .first()
    )

    # ==========================
    # AVALIAÇÃO FÍSICA
    # ==========================

    physical_assessment = (
        db_session.query(Physical_assessment)
        .filter(Physical_assessment.user_id == user_id)
        .order_by(Physical_assessment.end_date.desc())
        .first()
    )

    # ==========================
    # META SEMANAL
    # ==========================

    weekly_goal = (
        db_session.query(Goal_weekly)
        .filter(Goal_weekly.user_id == user_id)
        .order_by(Goal_weekly.end_week.desc())
        .first()
    )

    return render_template(
        'performance.html',
        user=user,
        activity=activity,
        cardiac_zones=cardiac_zones,
        recovery=recovery,
        physical_assessment=physical_assessment,
        weekly_goal=weekly_goal,
    )

def _ensure_pressure_dashboard_data(user_id):
    """Garante dados recentes para a tela, inclusive em bancos antigos com seed parcial."""
    today = date.today()
    rng = random.Random(f"vitapulse-pressure-dashboard-{user_id}-{today.isoformat()}")

    existing = (
        db_session.query(Measurement_pressure)
        .filter(Measurement_pressure.user_id == user_id)
        .all()
    )
    existing_days = {
        row.date_time.date() for row in existing
        if row.date_time is not None
    }

    # Sempre garante ao menos uma medição em cada um dos últimos 7 dias e
    # 14 dias de dados para permitir comparar a semana atual com a anterior.
    for offset in range(13, -1, -1):
        day = today - timedelta(days=offset)
        if day in existing_days:
            continue
        stamp = datetime.combine(day, datetime.min.time()).replace(
            hour=rng.choice([8, 10, 14, 17]),
            minute=rng.choice([0, 15, 30, 45]),
        )
        row = Measurement_pressure(
            user_id=user_id,
            date_time=stamp,
            sistolica=rng.randint(110, 136),
            diastolica=rng.randint(68, 86),
            cardiac_rate=rng.randint(65, 98),
            origin="simulação",
            observation="Medição sintética para demonstração.",
        )
        db_session.add(row)
        db_session.flush()
        db_session.add(Measurement_ppg(
            user_id=user_id,
            measurement_pressure_id=row.id,
            cardiac_rate=row.cardiac_rate,
            hrv=round(rng.uniform(20, 62), 2),
            quality_sign=round(rng.uniform(75, 99), 2),
            date_time=stamp,
        ))
        existing.append(row)
        existing_days.add(day)

    # Assegura que a seção Durante atividade nunca dependa de dados de outro usuário.
    if not db_session.query(Activity).filter_by(user_id=user_id).first():
        for offset, intensity, avg, maximum, minutes in [
            (0, "Zona 2", 86, 119, 32),
            (2, "Zona 3", 94, 137, 45),
            (4, "Zona 2", 81, 112, 28),
        ]:
            db_session.add(Activity(
                user_id=user_id,
                date=today - timedelta(days=offset),
                average_rate=avg,
                maximum_rate=maximum,
                active_time=minutes,
                intensity=intensity,
                time_recovery=rng.randint(12, 30),
                quant_sessions=1,
            ))

    # Remove apenas os avisos genéricos que o seed antigo colocava na seção ALERTAS.
    db_session.query(Warning_pressure).filter(
        Warning_pressure.user_id == user_id,
        Warning_pressure.title.in_(["Dados de demonstração", "Dados simulados atualizados"]),
    ).delete(synchronize_session=False)

    # Cria um aviso útil baseado nas leituras recentes, sem apresentar o aviso genérico.
    recent_rows = sorted(
        [row for row in existing if row.date_time and row.date_time.date() >= today - timedelta(days=6)],
        key=lambda row: row.date_time,
        reverse=True,
    )
    today_alert = db_session.query(Warning_pressure).filter(
        Warning_pressure.user_id == user_id,
        Warning_pressure.data == today,
        ~Warning_pressure.title.in_(["Dados de demonstração", "Dados simulados atualizados"]),
    ).first()
    if not today_alert:
        elevated = any(
            (row.sistolica or 0) >= 130 or (row.diastolica or 0) >= 80
            for row in recent_rows
        )
        if elevated:
            title = "Variação nas medições recentes"
            message = "Algumas leituras recentes ultrapassaram os limites de referência configurados neste protótipo. Consulte o histórico para observar a variação."
            level = "atenção"
        else:
            title = "Histórico atualizado"
            message = "Há medições recentes disponíveis para acompanhar a variação ao longo dos dias."
            level = "informativo"
        db_session.add(Warning_pressure(
            user_id=user_id, data=today, title=title,
            message=message, level=level, viewed=False,
        ))

    db_session.commit()


@app.route('/pressure')
def pressure():

    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('login'))

    user = db_session.query(User).filter_by(
        id=user_id
    ).first()

    if not user:
        return redirect(url_for('login'))

    _ensure_user_data(user)
    _ensure_pressure_dashboard_data(user_id)
    _ensure_pressure_dashboard_data(user_id)

    # =========================================================
    # MEDIÇÕES DE PRESSÃO
    # =========================================================

    measurements = (
        db_session.query(Measurement_pressure)
        .filter(
            Measurement_pressure.user_id == user_id
        )
        .order_by(
            Measurement_pressure.date_time.desc()
        )
        .all()
    )

    # =========================================================
    # MEDIÇÕES PPG
    # =========================================================

    ppg_measurements = (
        db_session.query(Measurement_ppg)
        .filter(
            Measurement_ppg.user_id == user_id
        )
        .order_by(
            Measurement_ppg.date_time.desc()
        )
        .all()
    )

    # =========================================================
    # AVISOS
    # =========================================================

    warnings = (
        db_session.query(Warning_pressure)
        .filter(
            Warning_pressure.user_id == user_id
        )
        .order_by(
            Warning_pressure.data.desc()
        )
        .all()
    )

    # =========================================================
    # ÚLTIMOS 7 DIAS E 7 DIAS ANTERIORES (DATAS DINÂMICAS)
    # =========================================================

    hoje = date.today()
    inicio_semana = datetime.combine(hoje - timedelta(days=6), datetime.min.time())
    fim_semana = datetime.combine(hoje + timedelta(days=1), datetime.min.time())
    inicio_semana_anterior = inicio_semana - timedelta(days=7)
    fim_semana_anterior = inicio_semana

    measurements_this_week = [
        measurement for measurement in measurements
        if measurement.date_time is not None
        and inicio_semana <= measurement.date_time.replace(tzinfo=None) < fim_semana
    ]

    measurements_previous_week = [
        measurement for measurement in measurements
        if measurement.date_time is not None
        and inicio_semana_anterior <= measurement.date_time.replace(tzinfo=None) < fim_semana_anterior
    ]

    # =========================================================
    # MÉDIA SISTÓLICA
    # =========================================================

    sistolic_values = [
        measurement.sistolica
        for measurement in measurements_this_week
        if measurement.sistolica is not None
    ]

    if sistolic_values:
        average_sistolica = (
            sum(sistolic_values)
            / len(sistolic_values)
        )
    else:
        average_sistolica = 0

    # =========================================================
    # MÉDIA DIASTÓLICA
    # =========================================================

    diastolic_values = [
        measurement.diastolica
        for measurement in measurements_this_week
        if measurement.diastolica is not None
    ]

    if diastolic_values:
        average_diastolica = (
            sum(diastolic_values)
            / len(diastolic_values)
        )
    else:
        average_diastolica = 0

    # =========================================================
    # MÉDIA BPM
    # =========================================================

    bpm_values = [
        measurement.cardiac_rate
        for measurement in measurements_this_week
        if measurement.cardiac_rate is not None
    ]

    if bpm_values:
        average_bpm = (
            sum(bpm_values)
            / len(bpm_values)
        )
    else:
        average_bpm = 0

    # =========================================================
    # MAIOR SISTÓLICA
    # =========================================================

    if sistolic_values:
        max_sistolica = max(sistolic_values)
    else:
        max_sistolica = 0

    # =========================================================
    # MAIOR DIASTÓLICA
    # =========================================================

    if diastolic_values:
        max_diastolica = max(diastolic_values)
    else:
        max_diastolica = 0

    # =========================================================
    # UMA LINHA POR DIA, COM A MEDIÇÃO REAL MAIS RECENTE DO DIA
    # =========================================================

    dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    measurements_by_day = []
    for offset in range(7):
        day_date = (hoje - timedelta(days=6)) + timedelta(days=offset)
        day_measurements = [
            measurement for measurement in measurements_this_week
            if measurement.date_time.date() == day_date
        ]
        measurements_by_day.append({
            "name": dias_semana[day_date.weekday()],
            "date": day_date,
            "measurement": day_measurements[0] if day_measurements else None,
            "count": len(day_measurements),
        })

    # Atividades sintéticas recentes para a seção "Durante atividade".
    activities = (
        db_session.query(Activity)
        .filter(Activity.user_id == user_id)
        .order_by(Activity.date.desc())
        .limit(7)
        .all()
    )

    # Dados serializados para o gráfico usar os valores reais, não barras fixas.
    pressure_chart_data = [
        {
            "date": measurement.date_time.isoformat(),
            "sistolica": measurement.sistolica,
            "diastolica": measurement.diastolica,
            "bpm": measurement.cardiac_rate,
        }
        for measurement in measurements
        if measurement.date_time is not None
    ]

    # =========================================================
    # ÚLTIMA MEDIÇÃO
    # =========================================================

    latest_measurement = (
        measurements[0]
        if measurements
        else None
    )

    # =========================================================
    # AVISOS NÃO VISUALIZADOS
    # =========================================================

    unread_warnings = [
        warning
        for warning in warnings
        if not warning.viewed
    ]

    # =========================================================
    # DEBUG
    # =========================================================

    print(
        "USUÁRIO PRESSÃO:",
        user.id,
        user.email
    )

    print(
        "MEDIÇÕES:",
        len(measurements)
    )

    print(
        "MEDIÇÕES ESTA SEMANA:",
        len(measurements_this_week)
    )

    print(
        "MÉDIA SISTÓLICA:",
        average_sistolica
    )

    print(
        "MÉDIA DIASTÓLICA:",
        average_diastolica
    )

    print(
        "MÉDIA BPM:",
        average_bpm
    )

    # =========================================================
    # TEMPLATE
    # =========================================================

    return render_template(
        'pressure.html',

        user=user,

        measurements=measurements,
        measurements_this_week=measurements_this_week,
        measurements_previous_week=measurements_previous_week,

        ppg_measurements=ppg_measurements,

        warnings=warnings,
        unread_warnings=unread_warnings,

        measurements_by_day=measurements_by_day,
        activities=activities,
        pressure_chart_data=pressure_chart_data,

        latest_measurement=latest_measurement,

        average_sistolica=average_sistolica,
        average_diastolica=average_diastolica,

        average_bpm=average_bpm,
        max_bpm=max(bpm_values) if bpm_values else 0,

        max_sistolica=max_sistolica,
        max_diastolica=max_diastolica
    )

# =========================================================
# RELATÓRIO SEMANAL
# =========================================================

@app.route('/report')
def report():

    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('login'))

    # =========================================================
    # USUÁRIO
    # =========================================================

    user = (
        db_session.query(User)
        .filter_by(id=user_id)
        .first()
    )

    if not user:
        return redirect(url_for('login'))

    _ensure_user_data(user)

    # =========================================================
    # RELATÓRIO MAIS RECENTE
    # =========================================================

    report = (
        db_session.query(Report_weekly)
        .filter(
            Report_weekly.user_id == user_id
        )
        .order_by(
            Report_weekly.beginning_date.desc()
        )
        .first()
    )

    # Se não existir relatório, cria
    if not report:

        report = criar_dados_relatorio(user_id)

        db_session.commit()

    # =========================================================
    # PERÍODO DO RELATÓRIO
    # =========================================================

    beginning_date = report.beginning_date

    end_date = report.end_date + timedelta(days=1)

    # =========================================================
    # ANSIEDADE
    # =========================================================

    anxiety_episodes = (
        db_session.query(Episode_anxious)
        .filter(
            Episode_anxious.user_id == user_id,
            Episode_anxious.date_time >= datetime.combine(
                beginning_date,
                datetime.min.time()
            ),
            Episode_anxious.date_time < datetime.combine(
                end_date,
                datetime.min.time()
            )
        )
        .order_by(
            Episode_anxious.date_time.desc()
        )
        .all()
    )

    # Média de ansiedade

    anxiety_values = [
        episode.level_anxious
        for episode in anxiety_episodes
        if episode.level_anxious is not None
    ]

    if anxiety_values:

        average_anxiety = (
            sum(anxiety_values)
            / len(anxiety_values)
        )

    else:

        average_anxiety = 0

    # =========================================================
    # PRESSÃO
    # =========================================================

    pressure_measurements = (
        db_session.query(Measurement_pressure)
        .filter(
            Measurement_pressure.user_id == user_id,
            Measurement_pressure.date_time >= datetime.combine(
                beginning_date,
                datetime.min.time()
            ),
            Measurement_pressure.date_time < datetime.combine(
                end_date,
                datetime.min.time()
            )
        )
        .order_by(
            Measurement_pressure.date_time.desc()
        )
        .all()
    )

    # Média sistólica

    sistolic_values = [
        measurement.sistolica
        for measurement in pressure_measurements
        if measurement.sistolica is not None
    ]

    if sistolic_values:

        average_sistolica = (
            sum(sistolic_values)
            / len(sistolic_values)
        )

    else:

        average_sistolica = 0

    # Média diastólica

    diastolic_values = [
        measurement.diastolica
        for measurement in pressure_measurements
        if measurement.diastolica is not None
    ]

    if diastolic_values:

        average_diastolica = (
            sum(diastolic_values)
            / len(diastolic_values)
        )

    else:

        average_diastolica = 0

    # =========================================================
    # BPM
    # =========================================================

    bpm_values = [
        measurement.cardiac_rate
        for measurement in pressure_measurements
        if measurement.cardiac_rate is not None
    ]

    if bpm_values:

        average_bpm = (
            sum(bpm_values)
            / len(bpm_values)
        )

        max_bpm = max(bpm_values)

    else:

        average_bpm = 0
        max_bpm = 0

    # =========================================================
    # PERFORMANCE FÍSICA
    # =========================================================

    activities = (
        db_session.query(Activity)
        .filter(
            Activity.user_id == user_id
        )
        .order_by(
            Activity.date.desc()
        )
        .all()
    )

    # Filtra atividades da semana
    weekly_activities = []

    for activity in activities:
        if activity.date is None:
            continue

        activity_date = activity.date

        if beginning_date <= activity_date <= report.end_date:
            weekly_activities.append(activity)

    # =========================================================
    # TEMPO TOTAL DE ATIVIDADE
    # =========================================================

    activity_times = [
        activity.active_time
        for activity in weekly_activities
        if activity.active_time is not None
    ]

    if activity_times:

        total_activity_time = sum(activity_times)

    else:

        total_activity_time = 0

    # =========================================================
    # QUANTIDADE DE ATIVIDADES
    # =========================================================

    total_activities = len(weekly_activities)

    # =========================================================
    # GERAÇÃO DE INSIGHTS
    # =========================================================

    insights = []

    if average_anxiety > 6:

        insights.append(
            "A média de ansiedade ficou acima de 6 durante a semana."
        )

    elif average_anxiety > 0:

        insights.append(
            "A média de ansiedade permaneceu abaixo de 6 durante a semana."
        )

    if average_sistolica > 0:

        insights.append(
            f"A pressão sistólica média foi de "
            f"{round(average_sistolica)}/{round(average_diastolica)} mmHg."
        )

    if total_activities > 0:

        insights.append(
            f"Foram registradas {total_activities} "
            f"atividades físicas durante a semana."
        )

    else:

        insights.append(
            "Nenhuma atividade física foi registrada durante a semana."
        )

    # =========================================================
    # DEBUG
    # =========================================================

    print("======================================")
    print("RELATÓRIO SEMANAL")
    print("Usuário:", user.id)
    print("Período:", beginning_date, "até", report.end_date)
    print("Episódios ansiedade:", len(anxiety_episodes))
    print("Média ansiedade:", average_anxiety)
    print("Medições pressão:", len(pressure_measurements))
    print("Média pressão:", average_sistolica, "/", average_diastolica)
    print("Média BPM:", average_bpm)
    print("BPM máximo:", max_bpm)
    print("Atividades:", total_activities)
    print("Tempo atividade:", total_activity_time)
    print("======================================")

    # =========================================================
    # TEMPLATE
    # =========================================================

    return render_template(
        'report.html',

        user=user,

        report=report,

        beginning_date=beginning_date,
        end_date=report.end_date,

        anxiety_episodes=anxiety_episodes,
        average_anxiety=average_anxiety,

        pressure_measurements=pressure_measurements,
        average_sistolica=average_sistolica,
        average_diastolica=average_diastolica,

        average_bpm=average_bpm,
        max_bpm=max_bpm,

        weekly_activities=weekly_activities,
        total_activities=total_activities,
        total_activity_time=total_activity_time,

        insights=insights
    )

# USUÁRIOS
# @app.route('/api/users/<int:id>/delete', methods=['GET'])
# def delete_user(id):
#     user = db_session.query(User).filter_by(id=id).first()

#     if not user:
#         return "Usuário não encontrado", 404

#     db_session.delete(user)
#     db_session.commit()

#     return f"Usuário {id} deletado com sucesso!"

@app.route('/home')
def home():
    user, error_response = _require_user(completed=True)
    if error_response:
        return error_response

    _ensure_user_data(user)
    stats = _bpm_stats(user.id)
    recent_checkups = (
        db_session.query(Checkup)
        .filter(Checkup.user_id == user.id)
        .order_by(Checkup.date.desc())
        .limit(3)
        .all()
    )
    categories = db_session.query(Category).order_by(Category.order).all()
    current_bpm = stats['current']
    min_bpm = stats['minimum']
    max_bpm = stats['maximum']
    ia_data = stats['latest']

    return render_template(
        'home.html', user=user, recent_checkups=recent_checkups,
        categories=categories, current_bpm=current_bpm,
        min_bpm=min_bpm, max_bpm=max_bpm, ia_data=ia_data,
    )


@app.route('/api/health', methods=['GET'])
def api_health():
    return jsonify({'status': 'ok', 'service': 'VitaPulse', 'simulated_data': True})


@app.route('/api/heart-rate/live', methods=['GET'])
def api_live_heart_rate():
    user, error_response = _require_user(completed=True)
    if error_response:
        return jsonify({'error': 'Autenticação necessária.'}), 401
    try:
        _ensure_user_data(user)
        reading = create_live_reading(db_session, user.id)
        stats = _bpm_stats(user.id)
        return jsonify({
            'id': reading.id,
            'bpm': int(reading.bpm),
            'bpm_medio': float(reading.bpm_medio) if reading.bpm_medio is not None else None,
            'rr': float(reading.rr) if reading.rr is not None else None,
            'rmssd': float(reading.rmssd) if reading.rmssd is not None else None,
            'resultado_ia': reading.resultado_ia,
            'probabilidade_ia': float(reading.probabilidade_ia) if reading.probabilidade_ia is not None else None,
            'date_time': reading.date_time.isoformat() if reading.date_time else None,
            'min_bpm': stats['minimum'],
            'max_bpm': stats['maximum'],
            'average_bpm': stats['average'],
            'simulated': True,
            'source': 'simulador_ia',
        })
    except Exception:
        db_session.rollback()
        logger.exception('Falha ao gerar BPM simulado')
        return jsonify({'error': 'Não foi possível atualizar os dados simulados.'}), 500


@app.route('/api/heart-rate/history', methods=['GET'])
def api_heart_rate_history():
    user, error_response = _require_user(completed=True)
    if error_response:
        return jsonify({'error': 'Autenticação necessária.'}), 401
    limit = min(max(request.args.get('limit', default=60, type=int), 1), 200)
    rows = (db_session.query(Measurement_ia).filter_by(user_id=user.id)
            .order_by(Measurement_ia.date_time.desc()).limit(limit).all())
    return jsonify([{
        'bpm': item.bpm,
        'bpm_medio': float(item.bpm_medio) if item.bpm_medio is not None else None,
        'rmssd': float(item.rmssd) if item.rmssd is not None else None,
        'date_time': item.date_time.isoformat() if item.date_time else None,
        'simulated': True,
    } for item in rows])


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
            password=generate_password_hash(data.get("password") or "") if data.get("password") else None,
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
    
    goals = query.order_by(Goal_weekly.beginning_week.desc()).all()

    return jsonify([
        {
        "id": goal.id,
        "user_id": goal.user_id,
        "beggining_week": goal.beginning_week.isoformat() if goal.beginning_week else None,
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
        beginning_week=(date.fromisoformat(data.get("beginning_week") or data.get("beggining_week"))
                        if (data.get("beginning_week") or data.get("beggining_week")) else None),
        end_week=(date.fromisoformat(data.get("end_week")) if data.get("end_week") else None),
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
            "beggining_week": goal.beginning_week.isoformat() if goal.beginning_week else None,
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
        Episode_anxious.date_time.desc()
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
        Report_weekly.beginning_date.desc()
    ).first()

    if not report:
        return jsonify({
            "message": "Nenhum relatório semanal encontrado"
        }), 404

    # Limites inclusivos para datas e exclusivos para timestamps.
    start_dt = datetime.combine(report.beginning_date, datetime.min.time())
    end_dt = datetime.combine(report.end_date + timedelta(days=1), datetime.min.time())

    # ATIVIDADES
    activities = db_session.query(Activity).filter(
        Activity.user_id == user_id,
        Activity.date >= report.beginning_date,
        Activity.date <= report.end_date
    ).all()

    # ANSIEDADE
    anxiety_episodes = db_session.query(Episode_anxious).filter(
        Episode_anxious.user_id == user_id,
        Episode_anxious.date_time >= start_dt,
        Episode_anxious.date_time < end_dt
    ).all()

    # PRESSÃO
    pressure_measurements = db_session.query(
        Measurement_pressure
    ).filter(
        Measurement_pressure.user_id == user_id,
        Measurement_pressure.date_time >= start_dt,
        Measurement_pressure.date_time < end_dt
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
        "beggining_date": report.beginning_date,
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

print("===================================")
print("ESTE É O APP PRINCIPAL DO VITAPULSE")
print("ROTAS REGISTRADAS:")
print(app.url_map)
print("===================================")

if __name__ == "__main__":
    init_db()
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )