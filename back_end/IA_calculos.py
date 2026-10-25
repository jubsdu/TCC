import numpy as np
import pandas as pd

from collections import deque

def criar_monitor(MAX_PONTOS, LIMITE_BPM, modelo, teste):

    # quantidade máxima de medições armazenadas
    extra = int(MAX_PONTOS / teste)

    # guarda os horários das medições
    horarios = deque(maxlen=extra)

    # guarda os valores de BPM
    batimentos = deque(maxlen=extra)

    # guarda os intervalos RR
    intervalos_rr = deque(maxlen=extra)

    # calculo de RMSSD
    def calcular_rmssd(rr):
        # precisa de pelo menos dois intervalos
        if len(rr) < 2:
            return None

        # transforma os valores em um array
        rr = np.array(
            rr,
            dtype=float
        )

        # calcula a diferença entre os intervalos
        diferencas = np.diff(rr)

        # eleva as diferenças ao quadrado
        quadrados = diferencas ** 2

        # calcula o RMSSD
        rmssd = np.sqrt(
            np.mean(quadrados)
        )

        return rmssd

    # analise do batimento
    def analisar_batimento(bpm, hrv):

        # cria uma tabela com os dados atuais
        nova_medicao = pd.DataFrame([
            {
                "heart_rate": bpm,
                "hrv_rmssd": hrv
            }
        ])

        # faz a previsão
        resultado = modelo.predict(
            nova_medicao
        )[0]

        # calcula as probabilidades
        probabilidades = modelo.predict_proba(
            nova_medicao
        )[0]

        # encontra a posição da classe 1
        indice_classe_1 = list(
            modelo.classes_
        ).index(1)

        # pega a probabilidade da classe 1
        probabilidade = probabilidades[
            indice_classe_1
        ]

        return resultado, probabilidade

    # retorna somente as funções necessárias
    return (
        horarios,
        batimentos,
        intervalos_rr,
        calcular_rmssd,
        analisar_batimento
    )

def obter_ultimos_valores(
    horarios,
    batimentos,
    intervalos_rr,
    rmssd,
    bpm_medio,
    resultado_ia,
    probabilidade_ia
):
    
    # pega o último horário
    ultimo_horario = (
        horarios[-1]
        if len(horarios) > 0
        else None
    )

    # pega o último BPM
    ultimo_bpm = (
        batimentos[-1]
        if len(batimentos) > 0
        else None
    )

    # pega o último intervalo RR
    ultimo_rr = (
        intervalos_rr[-1]
        if len(intervalos_rr) > 0
        else None
    )

    # retorna os últimos valores
    return {
        "horario": ultimo_horario,
        "bpm": ultimo_bpm,
        "rr": ultimo_rr,
        "rmssd": rmssd,
        "bpm_medio": bpm_medio,
        "resultado_ia": resultado_ia,
        "probabilidade_ia": probabilidade_ia
    }
