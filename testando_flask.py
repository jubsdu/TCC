from flask import Flask, jsonify, request

import numpy as np
import os
import random
from datetime import datetime

import IA_calculos
import joblib
import requests

import threading
import time


# ============================================================
# CONFIGURAÇÕES
# ============================================================

URL_BACKEND_PRINCIPAL = "http://127.0.0.1:5000"

MAX_PONTOS = 100
LIMITE_BPM = 100

app = Flask(__name__)

usuarios_ativos = set()
monitores = {}
atividades = {}

# ============================================================
# CARREGAR MODELO
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

modelo = joblib.load(
    os.path.join(BASE_DIR, "modelo_ia.joblib")
)

# ============================================================
# MONITOR INDIVIDUAL POR USUÁRIO
# ============================================================

def obter_monitor(user_id):

    if user_id not in monitores:

        (
            horarios,
            batimentos,
            intervalos_rr,
            calcular_rmssd,
            analisar_batimento
        ) = IA_calculos.criar_monitor(
            MAX_PONTOS,
            LIMITE_BPM,
            modelo,
            teste=1.5
        )

        monitores[user_id] = {
            "horarios": horarios,
            "batimentos": batimentos,
            "intervalos_rr": intervalos_rr,
            "calcular_rmssd": calcular_rmssd,
            "analisar_batimento": analisar_batimento,
            "rmssd": None,
            "bpm_medio": None,
            "resultado_ia": None,
            "probabilidade_ia": None
        }

    return monitores[user_id]

# ============================================================
# PROCESSAR BPM
# ============================================================

def processar_bpm(user_id, bpm):

    monitor = obter_monitor(user_id)

    horarios = monitor["horarios"]
    batimentos = monitor["batimentos"]
    intervalos_rr = monitor["intervalos_rr"]

    calcular_rmssd = monitor["calcular_rmssd"]
    analisar_batimento = monitor["analisar_batimento"]

    horario_recebimento = datetime.now()

    # -----------------------------------------
    # BPM → RR
    # -----------------------------------------

    rr_atual = 60000 / bpm

    horarios.append(horario_recebimento)
    batimentos.append(bpm)
    intervalos_rr.append(rr_atual)

    # -----------------------------------------
    # RMSSD
    # -----------------------------------------

    rmssd = calcular_rmssd(intervalos_rr)

    # -----------------------------------------
    # MÉDIA BPM
    # -----------------------------------------

    bpm_medio = float(np.mean(batimentos))

    # -----------------------------------------
    # IA
    # -----------------------------------------

    resultado_ia = None
    probabilidade_ia = None

    if rmssd is not None:

        resultado_ia, probabilidade_ia = analisar_batimento(
            bpm,
            rmssd
        )

        if resultado_ia is not None:
            resultado_ia = int(resultado_ia)

        if probabilidade_ia is not None:
            probabilidade_ia = float(probabilidade_ia)

    # -----------------------------------------
    # ATUALIZAR MONITOR
    # -----------------------------------------

    monitor["rmssd"] = rmssd
    monitor["bpm_medio"] = bpm_medio
    monitor["resultado_ia"] = resultado_ia
    monitor["probabilidade_ia"] = probabilidade_ia

    # -----------------------------------------
    # ANSIEDADE
    # -----------------------------------------

    processar_ansiedade(
        user_id,
        bpm,
        resultado_ia,
        probabilidade_ia
    )

    # -----------------------------------------
    # ENVIAR PARA O BACKEND PRINCIPAL
    # -----------------------------------------

    dados_para_backend = {
        "user_id": int(user_id),
        "bpm": float(bpm),
        "rr": float(rr_atual),
        "rmssd": float(rmssd) if rmssd is not None else None,
        "bpm_medio": float(bpm_medio),
        "resultado_ia": int(resultado_ia)
        if resultado_ia is not None else None,
        "probabilidade_ia": float(probabilidade_ia)
        if probabilidade_ia is not None else None,
        "horario": horario_recebimento.isoformat()

    }
    dados_performance = {
        "user_id": int(user_id),
        "bpm": float(bpm),
        "horario": horario_recebimento.isoformat()
    }

    try:
        resposta_ia = requests.post(
            f"{URL_BACKEND_PRINCIPAL}/api/ia-data",
            json=dados_para_backend,
            timeout=3
        )

        print(
            "IA:",
            user_id,
            resposta_ia.status_code
        )

    except Exception as e:

        print(
            "ERRO AO ENVIAR IA:",
            e
        )

    try:

        resposta_performance = requests.post(
            f"{URL_BACKEND_PRINCIPAL}/api/ia-performance",
            json=dados_performance,
            timeout=3
        )

        print(
            "PERFORMANCE:",
            user_id,
            resposta_performance.status_code
        )

    except Exception as e:

        print(
            "ERRO AO ENVIAR PERFORMANCE:",
            e
        )

# ============================================================
# PROCESSAR ANSIEDADE
# ============================================================

def processar_ansiedade(
    user_id,
    bpm,
    resultado_ia,
    probabilidade_ia
):

    if probabilidade_ia is None:
        return

    # --------------------------------------------------------
    # PROBABILIDADE → NÍVEL DE ANSIEDADE
    #
    # Escala simulada para o TCC:
    # 0%   - 20%  = nível 1
    # 20%  - 40%  = nível 2
    # 40%  - 60%  = nível 3
    # 60%  - 80%  = nível 4
    # 80% - 100%  = nível 5
    # --------------------------------------------------------

    probabilidade = float(probabilidade_ia)

    if probabilidade < 0.20:
        nivel_ansiedade = 1

    elif probabilidade < 0.40:
        nivel_ansiedade = 2

    elif probabilidade < 0.60:
        nivel_ansiedade = 3

    elif probabilidade < 0.80:
        nivel_ansiedade = 4

    else:
        nivel_ansiedade = 5

    dados_ansiedade = {
        "user_id": int(user_id),
        "level_anxious": nivel_ansiedade,
        "cardiac_rate": float(bpm),

        # Cada registro representa uma medição
        # simulada de ansiedade.
        "minutes": 1,

        "resultado_ia": int(resultado_ia)
        if resultado_ia is not None else None,

        "probabilidade_ia": probabilidade,

        "horario": datetime.now().isoformat()
    }

    try:

        resposta = requests.post(
            f"{URL_BACKEND_PRINCIPAL}/api/ia-anxiety",
            json=dados_ansiedade,
            timeout=3
        )

        print(
            "ANSIEDADE:",
            user_id,
            resposta.status_code,
            "NÍVEL:",
            nivel_ansiedade
        )

    except Exception as e:

        print(
            "ERRO AO ENVIAR ANSIEDADE:",
            e
        )

# ============================================================
# ATIVAR MONITOR
# ============================================================

@app.route("/ativar-monitor", methods=["POST"])
def ativar_monitor():

    data = request.get_json()

    if not data or not data.get("user_id"):
        return jsonify({
            "erro": "user_id não informado"
        }), 400

    user_id = int(data["user_id"])

    obter_monitor(user_id)

    usuarios_ativos.add(user_id)

    print("================================")
    print("MONITOR ATIVADO")
    print("USER ID:", user_id)
    print("USUÁRIOS ATIVOS:", usuarios_ativos)
    print("================================")

    return jsonify({
        "status": "ok",
        "mensagem": "Monitor ativado",
        "user_id": user_id
    }), 200

# ============================================================
# GERAR DADOS AUTOMATICAMENTE
# ============================================================
def gerar_dados_automaticamente():

    while True:

        print("=== CICLO DA IA ===")
        print("USUÁRIOS ATIVOS:", usuarios_ativos)

        for user_id in list(usuarios_ativos):

            bpm = random.gauss(82, 5)
            bpm = max(65, min(100, bpm))
            bpm = round(bpm, 1)

            print("BPM GERADO:", bpm)

            try:
                processar_bpm(user_id, bpm)
                print("PROCESSAMENTO TERMINOU")

            except Exception as e:
                print(
                    "ERRO NO PROCESSAMENTO:",
                    repr(e)
                )

        print("AGUARDANDO 3 SEGUNDOS...")
        time.sleep(3)

# ============================================================
# INICIAR GERADOR AUTOMÁTICO
# ============================================================

threading.Thread(
    target=gerar_dados_automaticamente,
    daemon=True
).start()


# ============================================================
# CONSULTAR ÚLTIMOS DADOS
# ============================================================

@app.route("/dados")
def dados():

    user_id = request.args.get(
        "user_id",
        type=int
    )

    if not user_id:
        return jsonify({
            "erro": "user_id não informado"
        }), 400

    monitor = obter_monitor(user_id)

    return jsonify({
        "user_id": user_id,
        "bpm": monitor["batimentos"][-1]
        if monitor["batimentos"] else None,

        "rr": monitor["intervalos_rr"][-1]
        if monitor["intervalos_rr"] else None,

        "rmssd": monitor["rmssd"],

        "bpm_medio": monitor["bpm_medio"],

        "resultado_ia": monitor["resultado_ia"],

        "probabilidade_ia":
            monitor["probabilidade_ia"]
    })

# ============================================================
# EXECUTAR
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True,
        use_reloader=False
    )