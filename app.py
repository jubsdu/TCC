import os
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_cors import CORS
from database import SessionLocal, init_db
from models import Measurement_ia, User, Category, Checkup, Activity, Cardiac_zone, Recovery, Physical_assessment, Goal_weekly, Measurement_bpm, Episode_anxious, Trigger, Episode_trigger, Tecnic, Episode_tecniques, Accompaniment, Measurement_pressure, Measurement_ppg, Warning_pressure, Report_weekly, Assessment_anxious
import requests
from sqlalchemy import func

app = Flask(__name__)
app.secret_key = "sua-chave-secreta"
CORS(app)

db_session = SessionLocal()

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

@app.route('/api/anxiety-data')
def anxiety_data():

    user_id = session.get('user_id')

    if not user_id:
        return jsonify({
            "tem_dados": False
        }), 401

    episodes = (
        db_session.query(Episode_anxious)
        .filter(
            Episode_anxious.user_id == user_id
        )
        .order_by(
            Episode_anxious.date_time.desc()
        )
        .all()
    )

    if not episodes:
        return jsonify({
            "tem_dados": False,
            "average_anxiety": 0,
            "average_bpm": 0,
            "max_bpm": 0
        })

    # =========================================
    # ANSIEDADE
    # =========================================

    anxiety_values = [
        episode.level_anxious
        for episode in episodes
        if episode.level_anxious is not None
    ]

    average_anxiety = (
        sum(anxiety_values) /
        len(anxiety_values)
        if anxiety_values
        else 0
    )

    # =========================================
    # BPM
    # =========================================

    bpm_values = [
        episode.cardiac_rate
        for episode in episodes
        if episode.cardiac_rate is not None
    ]

    average_bpm = (
        sum(bpm_values) /
        len(bpm_values)
        if bpm_values
        else 0
    )

    max_bpm = (
        max(bpm_values)
        if bpm_values
        else 0
    )

    # =========================================
    # ÚLTIMO EPISÓDIO
    # =========================================

    ultimo = episodes[0]

    return jsonify({
        "tem_dados": True,

        "average_anxiety":
            float(average_anxiety),

        "average_bpm":
            float(average_bpm),

        "max_bpm":
            int(max_bpm),

        "last_anxiety":
            ultimo.level_anxious,

        "last_bpm":
            ultimo.cardiac_rate,

        "last_date_time":
            ultimo.date_time.isoformat()
            if ultimo.date_time else None
    })

@app.route('/api/ia-anxiety', methods=['POST'])
def receber_ansiedade_ia():

    data = request.get_json()

    if not data:
        return jsonify({
            "erro": "Nenhum dado recebido"
        }), 400

    user_id = data.get("user_id")
    level_anxious = data.get("level_anxious")
    cardiac_rate = data.get("cardiac_rate")
    minutes = data.get("minutes")
    tecnic_id = data.get("tecnic_id")

    if not user_id:
        return jsonify({
            "erro": "user_id não informado"
        }), 400

    if level_anxious is None:
        return jsonify({
            "erro": "level_anxious não informado"
        }), 400

    if cardiac_rate is None:
        return jsonify({
            "erro": "cardiac_rate não informado"
        }), 400

    user = (
        db_session.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        return jsonify({
            "erro": "Usuário não encontrado"
        }), 404

    try:

        episodio = Episode_anxious(
            user_id=user_id,
            level_anxious=int(level_anxious),
            cardiac_rate=int(float(cardiac_rate)),
            minutes=int(minutes or 1),
            date_time=datetime.now(timezone.utc)
        )

        db_session.add(episodio)

        # Garante que o ID do episódio esteja disponível
        db_session.flush()

        # =========================================
        # TÉCNICA UTILIZADA
        # =========================================

        if tecnic_id:

            tecnica = (
                db_session.query(Tecnic)
                .filter(Tecnic.id == tecnic_id)
                .first()
            )

            if tecnica:

                relacao = Episode_tecniques(
                    episode_id=episodio.id,
                    tecnic_id=tecnica.id
                )

                db_session.add(relacao)

        db_session.commit()

        return jsonify({
            "status": "ok",
            "mensagem": "Dados de ansiedade salvos",
            "episode_id": episodio.id,
            "level_anxious": episodio.level_anxious,
            "cardiac_rate": episodio.cardiac_rate,
            "minutes": episodio.minutes,
            "tecnic_id": tecnic_id
        }), 201

    except Exception as e:

        db_session.rollback()

        print(
            "ERRO AO SALVAR ANSIEDADE DA IA:",
            e
        )

        return jsonify({
            "erro": "Erro ao salvar dados de ansiedade"
        }), 500

@app.route('/api/ia-assessment', methods=['POST'])
def atualizar_avaliacao_ia():

    data = request.get_json()

    if not data:
        return jsonify({
            "erro": "Nenhum dado recebido"
        }), 400

    user_id = data.get("user_id")

    if not user_id:
        return jsonify({
            "erro": "user_id não informado"
        }), 400

    hoje = datetime.now(timezone.utc).date()

    inicio = hoje - timedelta(days=6)

    atividades = (
        db_session.query(Activity)
        .filter(
            Activity.user_id == user_id,
            Activity.date >= inicio,
            Activity.date <= hoje
        )
        .all()
    )

    if not atividades:
        return jsonify({
            "mensagem": "Ainda não existem atividades"
        }), 200

    fc = [
        atividade.average_rate
        for atividade in atividades
        if atividade.average_rate is not None
    ]

    tempo = sum(
        atividade.active_time or 0
        for atividade in atividades
    )

    sessoes = sum(
        atividade.quant_sessions or 0
        for atividade in atividades
    )

    media_fc = (
        int(sum(fc) / len(fc))
        if fc
        else 0
    )

    assessment = (
        db_session.query(Physical_assessment)
        .filter(
            Physical_assessment.user_id == user_id
        )
        .order_by(
            Physical_assessment.end_date.desc()
        )
        .first()
    )

    if not assessment:

        assessment = Physical_assessment(
            user_id=user_id,
            beggining_date=inicio,
            end_date=hoje,
            average_fc=media_fc,
            active_time=tempo,
            quant_sessions=sessoes
        )

        db_session.add(assessment)

    else:

        assessment.beggining_date = inicio
        assessment.end_date = hoje
        assessment.average_fc = media_fc
        assessment.active_time = tempo
        assessment.quant_sessions = sessoes

    db_session.commit()

    return jsonify({
        "status": "ok",
        "average_fc": media_fc,
        "active_time": tempo,
        "quant_sessions": sessoes
    }), 201

@app.route('/api/ia-recovery', methods=['POST'])
def gerar_recuperacao_ia():

    data = request.get_json()

    if not data:
        return jsonify({
            "erro": "Nenhum dado recebido"
        }), 400

    user_id = data.get("user_id")
    final_bpm = data.get("final_bpm")

    if not user_id or final_bpm is None:
        return jsonify({
            "erro": "Dados incompletos"
        }), 400

    hoje = datetime.now(timezone.utc).date()

    bpm_1_min = max(
        50,
        int(final_bpm - random.randint(10, 20))
    )

    bpm_2_min = max(
        45,
        int(bpm_1_min - random.randint(8, 18))
    )

    queda_2_min = int(
        final_bpm - bpm_2_min
    )

    recovery = Recovery(
        user_id=user_id,
        date=hoje,
        final_bpm=int(final_bpm),
        bpm_1_min=bpm_1_min,
        bpm_2_min=bpm_2_min,
        queda_2_min=queda_2_min
    )

    db_session.add(recovery)
    db_session.commit()

    return jsonify({
        "status": "ok",
        "final_bpm": final_bpm,
        "bpm_1_min": bpm_1_min,
        "bpm_2_min": bpm_2_min,
        "queda_2_min": queda_2_min
    }), 201

@app.route('/api/ia-performance', methods=['POST'])
def receber_performance_ia():

    data = request.get_json()

    if not data:
        return jsonify({
            "erro": "Nenhum dado recebido"
        }), 400

    user_id = data.get("user_id")
    bpm = data.get("bpm")

    if not user_id:
        return jsonify({
            "erro": "user_id não informado"
        }), 400

    if bpm is None:
        return jsonify({
            "erro": "bpm não informado"
        }), 400

    user = (
        db_session.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        return jsonify({
            "erro": "Usuário não encontrado"
        }), 404

    try:

        # ==========================================
        # ATIVIDADE DO USUÁRIO
        # ==========================================

        atividade = (
            db_session.query(Activity)
            .filter(Activity.user_id == user_id)
            .order_by(Activity.date.desc())
            .first()
        )

        hoje = datetime.now(timezone.utc).date()

        if not atividade or atividade.date != hoje:

            atividade = Activity(
                user_id=user_id,
                date=hoje,
                average_rate=int(bpm),
                maximum_rate=int(bpm),
                active_time=0,
                intensity="Leve",
                time_recovery=0,
                quant_sessions=1
            )

            db_session.add(atividade)
            db_session.flush()

        else:

            # ==========================================
            # ATUALIZAR MÉDIA
            # ==========================================

            media_anterior = atividade.average_rate or 0

            atividade.average_rate = int(
                (media_anterior + float(bpm)) / 2
            )

            # ==========================================
            # MAIOR BPM
            # ==========================================

            if not atividade.maximum_rate:
                atividade.maximum_rate = int(bpm)

            else:
                atividade.maximum_rate = max(
                    atividade.maximum_rate,
                    int(bpm)
                )

            # Cada chamada representa aproximadamente
            # 3 segundos de atividade
            atividade.active_time = (
                atividade.active_time or 0
            ) + 3

        # ==========================================
        # INTENSIDADE
        # ==========================================

        if bpm < 100:
            atividade.intensity = "Leve"

        elif bpm < 120:
            atividade.intensity = "Moderada"

        elif bpm < 140:
            atividade.intensity = "Intensa"

        else:
            atividade.intensity = "Muito intensa"

        # ==========================================
        # MEDIÇÃO INDIVIDUAL
        # ==========================================

        medicao = Measurement_bpm(
            user_id=user_id,
            activity_id=atividade.id,
            bpm=int(bpm)
        )

        db_session.add(medicao)

        # ==========================================
        # ZONA CARDÍACA
        # ==========================================

        if bpm < 100:
            zona = "Zona 1"
            intensidade = "Leve"

        elif bpm < 120:
            zona = "Zona 2"
            intensidade = "Moderada"

        elif bpm < 140:
            zona = "Zona 3"
            intensidade = "Intensa"

        elif bpm < 160:
            zona = "Zona 4"
            intensidade = "Muito intensa"

        else:
            zona = "Zona 5"
            intensidade = "Máxima"

        zona_existente = (
            db_session.query(Cardiac_zone)
            .filter(
                Cardiac_zone.user_id == user_id,
                Cardiac_zone.date == hoje,
                Cardiac_zone.zone == zona
            )
            .first()
        )

        if zona_existente:

            zona_existente.minutes = (
                zona_existente.minutes or 0
            ) + 1

        else:

            zona_existente = Cardiac_zone(
                user_id=user_id,
                date=hoje,
                zone=zona,
                intensity=intensidade,
                minutes=1
            )

            db_session.add(zona_existente)

        # ==========================================
        # META SEMANAL
        # ==========================================

        inicio_semana = hoje - timedelta(
            days=hoje.weekday()
        )

        fim_semana = inicio_semana + timedelta(days=6)

        meta = (
            db_session.query(Goal_weekly)
            .filter(
                Goal_weekly.user_id == user_id,
                Goal_weekly.beginning_week == inicio_semana
            )
            .first()
        )

        if not meta:

            meta = Goal_weekly(
                user_id=user_id,
                beginning_week=inicio_semana,
                end_week=fim_semana,
                goal_activity=150,
                activity_completed=0,
                goal_intensity=75,
                intensity_completed=0,
                goal_sessions=5,
                sessions_completed=1
            )

            db_session.add(meta)

        else:

            meta.activity_completed = (
                meta.activity_completed or 0
            ) + 3

            if intensidade in [
                "Moderada",
                "Intensa",
                "Muito intensa",
                "Máxima"
            ]:

                meta.intensity_completed = (
                    meta.intensity_completed or 0
                ) + 1

        # ==========================================
        # SALVAR
        # ==========================================

        db_session.commit()

        return jsonify({
            "status": "ok",
            "mensagem": "Performance atualizada",
            "activity_id": atividade.id,
            "bpm": bpm,
            "zona": zona
        }), 201

    except Exception as e:

        db_session.rollback()

        print(
            "ERRO AO SALVAR PERFORMANCE DA IA:",
            e
        )

        return jsonify({
            "erro": "Erro ao salvar performance"
        }), 500
    
@app.route('/api/performance-data')
def performance_data():

    user_id = session.get('user_id')

    if not user_id:
        return jsonify({
            "tem_dados": False
        }), 401

    dados = (
        db_session.query(Measurement_ia)
        .filter(
            Measurement_ia.user_id == user_id
        )
        .order_by(
            Measurement_ia.date_time.desc()
        )
        .first()
    )

    if not dados:
        return jsonify({
            "tem_dados": False,
            "average_bpm": 0,
            "bpm": 0,
            "rmssd": 0,
            "resultado_ia": None,
            "probabilidade_ia": None
        })

    return jsonify({
        "tem_dados": True,
        "bpm": dados.bpm,
        "average_bpm": float(dados.bpm_medio)
            if dados.bpm_medio is not None else 0,
        "rmssd": float(dados.rmssd)
            if dados.rmssd is not None else 0,
        "resultado_ia": dados.resultado_ia,
        "probabilidade_ia": float(dados.probabilidade_ia)
            if dados.probabilidade_ia is not None else 0,
        "date_time": dados.date_time.isoformat()
            if dados.date_time else None
    })

@app.route('/api/ia-data', methods=['POST'])
def receber_dados_ia():

    data = request.get_json()

    if not data:
        return jsonify({
            "erro": "Nenhum dado recebido"
        }), 400

    user_id = data.get("user_id")

    if not user_id:
        return jsonify({
            "erro": "user_id não informado"
        }), 400

    user = (
        db_session.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        return jsonify({
            "erro": "Usuário não encontrado"
        }), 404

    try:

        # --------------------------------
        # HORÁRIO
        # --------------------------------

        horario = data.get("horario")

        if horario:
            horario = datetime.fromisoformat(horario)
        else:
            horario = datetime.now(timezone.utc)

        # --------------------------------
        # SALVA MEDIÇÃO DA IA
        # --------------------------------

        medicao = Measurement_ia(
            user_id=user_id,
            bpm=data.get("bpm"),
            rr=data.get("rr"),
            rmssd=data.get("rmssd"),
            bpm_medio=data.get("bpm_medio"),
            resultado_ia=data.get("resultado_ia"),
            probabilidade_ia=data.get("probabilidade_ia"),
            date_time=horario
        )

        db_session.add(medicao)
        db_session.commit()
        db_session.refresh(medicao)

        # --------------------------------
        # CHECKUP DO DIA
        # --------------------------------

        hoje = horario.date()

        checkup = (
            db_session.query(Checkup)
            .filter(
                Checkup.user_id == user_id,
                Checkup.date == hoje
            )
            .first()
        )

        if not checkup:

            checkup = Checkup(
                user_id=user_id,
                type="Monitoramento cardíaco",
                created_at=horario,
                date=hoje,
                current_bpm=data.get("bpm"),
                observation="Checkup gerado a partir do monitoramento da IA."
            )

            db_session.add(checkup)

        else:

            if data.get("bpm") is not None:
                checkup.current_bpm = data.get("bpm")

        db_session.commit()

        # --------------------------------
        # SE NÃO EXISTIR, CRIA
        # --------------------------------

        if not checkup:

            checkup = Checkup(
                user_id=user_id,
                type="Monitoramento cardíaco",
                created_at=horario,
                date=hoje,
                average_bpm=data.get("bpm_medio"),
                observation="Checkup gerado a partir do monitoramento da IA."
            )

            db_session.add(checkup)

        else:

            # Atualiza a média com a nova medição
            if data.get("bpm_medio") is not None:
                checkup.average_bpm = data.get("bpm_medio")


        db_session.commit()

        print(
            "MEDIÇÃO IA SALVA:",
            medicao.id,
            "| CHECKUP:",
            checkup.id
        )


        return jsonify({
            "status": "ok",
            "mensagem": "Dados da IA recebidos com sucesso",
            "id": medicao.id,
            "checkup_id": checkup.id
        }), 201


    except Exception as e:

        db_session.rollback()

        print(
            "ERRO AO SALVAR DADOS DA IA:",
            e
        )

        return jsonify({
            "erro": "Erro ao salvar dados da IA"
        }), 500

@app.route('/api/ia-data', methods=['GET'])
def obter_dados_ia():

    user_id = request.args.get("user_id", type=int)

    query = db_session.query(Measurement_ia)

    if user_id:
        query = query.filter(
            Measurement_ia.user_id == user_id
        )

    dados = query.order_by(
        Measurement_ia.date_time.desc()
    ).all()

    return jsonify([
        {
            "id": item.id,
            "user_id": item.user_id,
            "bpm": item.bpm,
            "rr": float(item.rr) if item.rr is not None else None,
            "rmssd": float(item.rmssd) if item.rmssd is not None else None,
            "bpm_medio": float(item.bpm_medio)
                if item.bpm_medio is not None else None,
            "resultado_ia": item.resultado_ia,
            "probabilidade_ia": float(item.probabilidade_ia)
                if item.probabilidade_ia is not None else None,
            "date_time": item.date_time.isoformat()
                if item.date_time else None
        }
        for item in dados
    ])

# Autenticação e Conta
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form.get('email')
        password = request.form.get('password')

        print("LOGIN RECEBIDO:", email)

        user = db_session.query(User).filter_by(
            email=email
        ).first()

        if not user:
            return "Usuário não encontrado.", 401

        if user.password != password:
            return "Senha incorreta.", 401

        # Guarda o ID do usuário existente
        session['user_id'] = user.id
        try:

            resposta_ia = requests.post(
                "http://127.0.0.1:5001/ativar-monitor",
                json={
                    "user_id": user.id
                },
                timeout=3
            )

            print(
                "ATIVAÇÃO DA IA:",
                resposta_ia.status_code
            )

        except Exception as e:

            print(
                "ERRO AO ATIVAR MONITOR DA IA:",
                e
            )

        return redirect(url_for('home'))

    # ==========================================
    # SALVA ACOMPANHAMENTO ESCOLHIDO
    # ==========================================

        treatments = session.get('treatments', [])

        if treatments:

            accompaniment = (
                db_session.query(Accompaniment)
                .filter_by(user_id=user.id)
                .first()
            )

            if not accompaniment:

                accompaniment = Accompaniment(
                    user_id=user.id,
                    psychotherapy=False,
                    consultation=False,
                    medication=False
                )

                db_session.add(accompaniment)

            if "nenhum" in treatments:

                accompaniment.psychotherapy = False
                accompaniment.consultation = False
                accompaniment.medication = False

            else:

                accompaniment.psychotherapy = (
                    "psychotherapy" in treatments
                )

                accompaniment.consultation = (
                    "consultation" in treatments
                )

                accompaniment.medication = (
                    "medication" in treatments
                )

            db_session.commit()

            print("ACOMPANHAMENTO SALVO:", treatments)

            session.pop('treatments', None)

        print("LOGIN CORRETO - ID:", user.id)
        print("SESSION:", dict(session))

        return redirect(url_for('home'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        password = request.form.get('password')

        # ==========================================
        # VERIFICA SE O EMAIL JÁ EXISTE
        # ==========================================

        existing_user = (
            db_session.query(User)
            .filter_by(email=email)
            .first()
        )

        if existing_user:
            return "Este email já está cadastrado.", 400

        # ==========================================
        # CRIA O USUÁRIO
        # ==========================================

        user = User(
            name=name,
            phone=phone,
            email=email,
            password=password
        )

        db_session.add(user)
        db_session.commit()

        print("USUÁRIO CRIADO:", user.id, user.email)

        # ==========================================
        # LOGIN AUTOMÁTICO
        # ==========================================

        session['user_id'] = user.id

        print("USUÁRIO CRIADO - ID:", user.id)

        # ==========================================
        # RECUPERA ACOMPANHAMENTOS ESCOLHIDOS
        # ==========================================

        treatments = session.get('treatments', [])

        print("ACOMPANHAMENTOS RECEBIDOS:", treatments)

        # ==========================================
        # CRIA O ACOMPANHAMENTO
        # ==========================================

        accompaniment = (
            db_session.query(Accompaniment)
            .filter_by(user_id=user.id)
            .first()
        )

        if not accompaniment:

            accompaniment = Accompaniment(
                user_id=user.id,
                psychotherapy=False,
                consultation=False,
                medication=False
            )

            db_session.add(accompaniment)

        # ==========================================
        # SALVA AS OPÇÕES
        # ==========================================

        if "nenhum" in treatments:

            accompaniment.psychotherapy = False
            accompaniment.consultation = False
            accompaniment.medication = False

        else:

            accompaniment.psychotherapy = (
                "psychotherapy" in treatments
            )

            accompaniment.consultation = (
                "consultation" in treatments
            )

            accompaniment.medication = (
                "medication" in treatments
            )

        db_session.commit()

        print(
            "ACOMPANHAMENTO SALVO - ID:",
            accompaniment.id
        )

        print(
            "Psicoterapia:",
            accompaniment.psychotherapy
        )

        print(
            "Consulta:",
            accompaniment.consultation
        )

        print(
            "Medicação:",
            accompaniment.medication
        )

        # ==========================================
        # LIMPA A SESSÃO
        # ==========================================

        session.pop('treatments', None)

        # ==========================================
        # VAI PARA A PRÓXIMA ETAPA
        # ==========================================

        return redirect(url_for('onboarding_reason'))

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

        treatments = request.form.getlist('treatment')

        if not treatments:
            return "Nenhum acompanhamento foi selecionado.", 400

        print("ACOMPANHAMENTOS ESCOLHIDOS:", treatments)

        session['treatments'] = treatments

        return redirect(url_for('login'))

    return render_template(
        'onboarding-treatment.html'
    )

# =====================================================
# ALTERAR / ADICIONAR ACOMPANHAMENTO
# =====================================================

@app.route('/onboarding-treatment-edit', methods=['GET', 'POST'])
def onboarding_treatment_edit():

    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('login'))


    accompaniment = (
        db_session.query(Accompaniment)
        .filter_by(user_id=user_id)
        .first()
    )


    if not accompaniment:

        accompaniment = Accompaniment(
            user_id=user_id,
            psychotherapy=False,
            consultation=False,
            medication=False
        )

        db_session.add(accompaniment)
        db_session.flush()


    if request.method == 'POST':

        treatments = request.form.getlist('treatment')


        if not treatments:
            return "Nenhum acompanhamento foi selecionado.", 400


        # =========================
        # NENHUM
        # =========================

        if "nenhum" in treatments:

            accompaniment.psychotherapy = False
            accompaniment.consultation = False
            accompaniment.medication = False


        # =========================
        # ACOMPANHAMENTOS
        # =========================

        else:

            accompaniment.psychotherapy = (
                "psychotherapy" in treatments
            )

            accompaniment.consultation = (
                "consultation" in treatments
            )

            accompaniment.medication = (
                "medication" in treatments
            )


        db_session.commit()

        return redirect(url_for('home'))


    return render_template(
        'onboarding-treatment.html',
        edit_mode=True,
        accompaniment=accompaniment
    )

# Módulos de Saúde e Monitoramento
from datetime import datetime, timedelta
from sqlalchemy import func

@app.route('/anxiety')
def anxiety():

    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('login'))

    user = (
        db_session.query(User)
        .filter_by(id=user_id)
        .first()
    )

    if not user:
        return redirect(url_for('login'))

    # =====================================================
    # ACOMPANHAMENTO
    # =====================================================

    accompaniment = (
        db_session.query(Accompaniment)
        .filter_by(user_id=user_id)
        .first()
    )

    # =====================================================
    # TODOS OS EPISÓDIOS
    # =====================================================

    episodes = (
        db_session.query(Episode_anxious)
        .filter(
            Episode_anxious.user_id == user_id
        )
        .order_by(
            Episode_anxious.date_time.desc()
        )
        .all()
    )

    # =====================================================
    # ÚLTIMOS 5 EPISÓDIOS
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
    # SEMANA ATUAL
    # =====================================================

    hoje = datetime.now()

    inicio_semana = (hoje - timedelta(days=hoje.weekday())).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    fim_semana = inicio_semana + timedelta(days=7)

    episodes_this_week = [
        episode
        for episode in episodes
        if episode.date_time
        and inicio_semana <= episode.date_time < fim_semana
    ]

    # =====================================================
    # SEMANA ANTERIOR
    # =====================================================

    inicio_semana_anterior = (
        inicio_semana - timedelta(days=7)
    )

    fim_semana_anterior = inicio_semana

    episodes_previous_week = [
        episode
        for episode in episodes
        if episode.date_time
        and inicio_semana_anterior
        <= episode.date_time
        < fim_semana_anterior
    ]

    # =====================================================
    # MÉDIA DE ANSIEDADE
    # =====================================================

    anxiety_values = [
        episode.level_anxious
        for episode in episodes_this_week
        if episode.level_anxious is not None
    ]

    average_anxiety = (
        sum(anxiety_values) / len(anxiety_values)
        if anxiety_values
        else 0
    )

    # =====================================================
    # MÉDIA DE ANSIEDADE DA SEMANA ANTERIOR
    # =====================================================

    previous_anxiety_values = [
        episode.level_anxious
        for episode in episodes_previous_week
        if episode.level_anxious is not None
    ]

    previous_average_anxiety = (
        sum(previous_anxiety_values)
        / len(previous_anxiety_values)
        if previous_anxiety_values
        else 0
    )

    # =====================================================
    # BPM
    # =====================================================

    bpm_values = [
        episode.cardiac_rate
        for episode in episodes_this_week
        if episode.cardiac_rate is not None
    ]

    average_bpm = (
        sum(bpm_values) / len(bpm_values)
        if bpm_values
        else 0
    )

    max_bpm = (
        max(bpm_values)
        if bpm_values
        else 0
    )

    # =====================================================
    # DURAÇÃO MÉDIA
    # =====================================================

    duration_values = [
        episode.minutes
        for episode in episodes_this_week
        if episode.minutes is not None
    ]

    average_duration = (
        sum(duration_values) / len(duration_values)
        if duration_values
        else 0
    )

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
            if episode.date_time
            and episode.date_time.date() == data.date()
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
            if episode.date_time
        ]

        if hours:
            most_common_hour = max(
                set(hours),
                key=hours.count
            )

            most_frequent_time = (
                f"{most_common_hour:02d}h"
            )
        else:
            most_frequent_time = "Sem registros"

    else:
        most_frequent_time = "Sem registros"

    # =====================================================
    # DEBUG
    # =====================================================
    print("\n========== DEBUG TÉCNICAS ==========")

    print("USUÁRIO:", user_id)

    print(
        "TODAS AS TÉCNICAS:",
        [
            (t.id, t.name, t.icon)
            for t in db_session.query(Tecnic).all()
        ]
    )

    print(
        "TODAS AS RELAÇÕES:",
        [
            (r.id, r.episode_id, r.tecnic_id)
            for r in db_session.query(Episode_tecniques).all()
        ]
    )

    print(
        "TÉCNICAS DESTE USUÁRIO:",
        [
            (t.id, t.name, t.icon)
            for t in tecnics
        ]
    )

    print("====================================\n")

    return render_template(
        'anxiety.html',

        user=user,

        accompaniment=accompaniment,

        episodes=episodes,
        latest_episodes=latest_episodes,

        episodes_this_week=episodes_this_week,
        episodes_previous_week=episodes_previous_week,

        episodes_by_day=episodes_by_day,

        average_anxiety=average_anxiety,
        previous_average_anxiety=previous_average_anxiety,

        average_bpm=average_bpm,
        max_bpm=max_bpm,

        average_duration=average_duration,

        most_frequent_time=most_frequent_time,

        tecnics=tecnics
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

    agora = datetime.now(timezone.utc)
    inicio_semana = agora - timedelta(days=7)

    bpm_ia_semana = (
        db_session.query(Measurement_ia)
        .filter(
            Measurement_ia.user_id == user_id,
            Measurement_ia.date_time >= inicio_semana
        )
        .all()
    )

    bpm_valores = [
        float(item.bpm)
        for item in bpm_ia_semana
        if item.bpm is not None
    ]

    bpm_semana = (
        sum(bpm_valores) / len(bpm_valores)
        if bpm_valores
        else None
    )

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
        bpm_semana=bpm_semana
    )

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

    # ==========================
    # DADOS DA IA
    # ==========================

    ia_measurements = (
        db_session.query(Measurement_ia)
        .filter(Measurement_ia.user_id == user_id)
        .order_by(Measurement_ia.date_time.desc())
        .all()
    )

    # ==========================
    # DADOS DA SEMANA
    # ==========================

    hoje = datetime.now(timezone.utc).date()

    inicio_semana = hoje - timedelta(days=hoje.weekday())

    ia_semana = [
        measurement
        for measurement in ia_measurements
        if measurement.date_time
        and measurement.date_time.date() >= inicio_semana
        and measurement.date_time.date() <= hoje
    ]

    bpm_semana = [
        measurement.bpm
        for measurement in ia_semana
        if measurement.bpm is not None
    ]

    if bpm_semana:
        average_bpm_semana = sum(bpm_semana) / len(bpm_semana)
    else:
        average_bpm_semana = 0

    # ==========================
    # FREQUÊNCIA MÉDIA
    # ==========================

    bpm_values = [
        measurement.bpm
        for measurement in ia_measurements
        if measurement.bpm is not None
    ]

    if bpm_values:
        average_bpm = sum(bpm_values) / len(bpm_values)
        current_bpm = bpm_values[0]
        min_bpm = min(bpm_values)
        max_bpm = max(bpm_values)
    else:
        average_bpm = 0
        current_bpm = 0
        min_bpm = 0
        max_bpm = 0

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
    # SEMANA ATUAL
    # =========================================================

    inicio_semana = datetime(
        2026, 9, 21, 0, 0, 0
    )

    fim_semana = inicio_semana + timedelta(days=7)

    measurements_this_week = [
        measurement
        for measurement in measurements
        if inicio_semana
        <= measurement.date_time
        < fim_semana
    ]

    # =========================================================
    # SEMANA ANTERIOR
    # =========================================================

    inicio_semana_anterior = (
        inicio_semana - timedelta(days=7)
    )

    fim_semana_anterior = inicio_semana

    measurements_previous_week = [
        measurement
        for measurement in measurements
        if inicio_semana_anterior
        <= measurement.date_time
        < fim_semana_anterior
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
    # MEDIÇÕES POR DIA
    # =========================================================

    dias_semana = [
        "Segunda",
        "Terça",
        "Quarta",
        "Quinta",
        "Sexta",
        "Sábado",
        "Domingo"
    ]

    measurements_by_day = []

    for i, day_name in enumerate(dias_semana):

        data = inicio_semana + timedelta(days=i)

        count = sum(
            1
            for measurement in measurements_this_week
            if measurement.date_time.date()
            == data.date()
        )

        measurements_by_day.append({
            "name": day_name,
            "count": count
        })

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

        latest_measurement=latest_measurement,

        average_sistolica=average_sistolica,
        average_diastolica=average_diastolica,

        max_sistolica=max_sistolica,
        max_diastolica=max_diastolica,

        average_bpm=average_bpm,
        current_bpm=current_bpm,
        min_bpm=min_bpm,
        max_bpm=max_bpm,

        bpm_semana=average_bpm_semana
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

    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('login'))

    user = (
        db_session.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        return redirect(url_for('login'))

    recent_checkups = (
        db_session.query(Checkup)
        .filter(Checkup.user_id == user_id)
        .order_by(Checkup.date.desc())
        .limit(2)
        .all()
    )

    categories = (
        db_session.query(Category)
        .order_by(Category.order)
        .all()
    )

    all_checkups = (
        db_session.query(Checkup)
        .filter(Checkup.user_id == user_id)
        .order_by(Checkup.date.desc())
        .all()
    )

    bpm_values = [
        checkup.current_bpm
        for checkup in all_checkups
        if checkup.current_bpm is not None
    ]

    current_bpm = bpm_values[0] if bpm_values else 0

    min_bpm = min(bpm_values) if bpm_values else 0

    max_bpm = max(bpm_values) if bpm_values else 0

    ia_data = (
        db_session.query(Measurement_ia)
        .filter(
            Measurement_ia.user_id == user_id
        )
        .order_by(
            Measurement_ia.date_time.desc()
        )
        .first()
    )

    print(
        "USUÁRIO LOGADO:",
        user.id,
        user.email
    )

    print(
        "DADO MAIS RECENTE DA IA:",
        ia_data
    )

    return render_template(
        'home.html',
        user=user,
        recent_checkups=recent_checkups,
        categories=categories,
        current_bpm=current_bpm,
        min_bpm=min_bpm,
        max_bpm=max_bpm,
        ia_data=ia_data
    )

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
    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )
    print("Sucesso!")