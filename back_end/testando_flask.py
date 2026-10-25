"""Serviço opcional para testar a inferência do modelo local.

O aplicativo principal já gera e persiste dados sintéticos em SQLite; este serviço
não é necessário para executar o VitaPulse. Rode em outra janela apenas para testar
as respostas da IA em http://127.0.0.1:5001.
"""
from __future__ import annotations

import random
from collections import deque
from flask import Flask, jsonify, request

from simulador_ia import predict_synthetic_sample

app = Flask(__name__)
monitors = {}
MAX_POINTS = 100


def get_monitor(user_id: int):
    if user_id not in monitors:
        monitors[user_id] = {
            "history": deque(maxlen=MAX_POINTS),
            "bpm": random.randint(68, 84),
            "active": False,
        }
    return monitors[user_id]


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "VitaPulse IA de demonstração"})


@app.post("/ativar-monitor")
def activate_monitor():
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        return jsonify({"error": "user_id precisa ser um inteiro positivo."}), 400
    monitor = get_monitor(user_id)
    monitor["active"] = True
    return jsonify({"status": "ok", "user_id": user_id, "active": True})


@app.get("/dados")
def get_data():
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"error": "user_id não informado."}), 400
    monitor = get_monitor(user_id)
    if not monitor["active"]:
        return jsonify({"error": "Ative o monitor primeiro em /ativar-monitor."}), 409

    last_bpm = monitor["bpm"]
    variation = random.choice([-4, -3, -2, -1, 0, 1, 2, 3, 4, 9, -9])
    bpm = max(55, min(120, last_bpm + variation))
    rmssd = round(random.uniform(18, 68), 2)
    result, probability = predict_synthetic_sample(bpm, rmssd)
    monitor["bpm"] = bpm
    monitor["history"].append(bpm)
    avg = round(sum(monitor["history"]) / len(monitor["history"]), 2)
    return jsonify({
        "user_id": user_id,
        "bpm": bpm,
        "rr": round(60000 / bpm, 2),
        "rmssd": rmssd,
        "bpm_medio": avg,
        "resultado_ia": result,
        "probabilidade_ia": probability,
        "simulated": True,
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=False)
