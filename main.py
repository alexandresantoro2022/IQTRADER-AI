import os
import sys
import time
import datetime
import requests
import joblib
import numpy as np
from iqoptionapi.stable_api import IQ_Option

# ========== CONFIGURAÇÕES ==========
EMAIL = "alexandresantoroalves@hotmail.com"
SENHA = "A1l2e3-*@"
ATIVOS = ["EURGBP", "EURUSD", "GBPUSD", "USDJPY"]
TIPO_CONTA = "REAL"
VALOR_INICIAL = 5           # Valor de entrada em BRL
EXPIRACAO = 1               # minutos
PERIODO_CANDLE = 60         # Duração do candle em segundos
GALE_MAX = 1
# Parâmetros de EMAs clássicos
PERIOD_EMAA = 5
PERIOD_EMAB = 13
PERIOD_EMAC = 34
PERIOD_EMAD = 89

# ========== TELEGRAM ==========
TELEGRAM_TOKEN = "6658940055:AAF33sglHPsVkKeqJuyckctjq__Wf5oSGeg"
CHAT_ID = "-1002664609130"

def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        resp = requests.post(url, json=data)
        print(f"[TELEGRAM_STATUS] {resp.status_code}")
    except Exception as e:
        print("Erro ao enviar telegram:", e)

# ========== UTILITÁRIOS ==========
def media_exponencial(valores, periodo):
    pesos = [2/(periodo+1)*(1-2/(periodo+1))**i for i in range(periodo)]
    pesos.reverse()
    return sum(a*b for a,b in zip(valores[-periodo:], pesos))

# ========== ANÁLISE ==========
def analisar_sinais(api, ativo):
    candles = api.get_candles(ativo, PERIODO_CANDLE, 100, time.time())
    candles.reverse()
    closes = [c['close'] for c in candles]
    opens = [c['open'] for c in candles]
    highs = [c['max'] for c in candles]
    lows = [c['min'] for c in candles]
    hlc3 = [(c['max']+c['min']+c['close'])/3 for c in candles]

    EMAA = media_exponencial(closes, PERIOD_EMAA)
    EMAB = media_exponencial(closes, PERIOD_EMAB)
    EMAC = media_exponencial(hlc3, PERIOD_EMAC)
    EMAD = media_exponencial(hlc3, PERIOD_EMAD)

    close = closes[-1]
    open_ = opens[-1]
    close_1, open_1 = closes[-2], opens[-2]
    close_2, open_2 = closes[-3], opens[-3]
    close_3 = closes[-4]
    high_1, low_1 = highs[-2], lows[-2]

    bull = (close_1<open_1 and close>open_ and close>high_1 and close_2>=open_2)
    bear = (close_1>open_1 and close<open_ and close<low_1 and close_2<=open_2)
    if bull:
        return "call"
    if bear:
        return "put"
    return None

# ========== RESULTADO ==========
def verificar_resultado(api, ativo, direcao):
    time.sleep(EXPIRACAO*60)
    c = api.get_candles(ativo, PERIODO_CANDLE, 1, time.time())[0]
    return "win" if (direcao=="call" and c['close']>c['open']) or (direcao=="put" and c['close']<c['open']) else "loss"

# ========== ENTRADA ==========
def enviar_sinal(api, ativo, direcao, gale):
    hora = (datetime.datetime.now()+datetime.timedelta(minutes=1)).strftime("%H:%M")
    tag = "🟢 ENTRADA" if gale==0 else f"🔁 GALE {gale}"
    enviar_telegram(f"{tag}\n🎯 Ativo: `{ativo}`\n📈 Direção: *{direcao.upper()}*\n🕒 Entrada: {hora}\n🌀 Expiração: {EXPIRACAO}min")
    for t in range(3):
        ok, resp = api.buy_digital_spot(ativo, VALOR_INICIAL, direcao, EXPIRACAO)
        if ok:
            enviar_telegram(f"🎫 Ordem ID: `{resp}`")
            break
        time.sleep(1)
    else:
        enviar_telegram("⚠️ Falha ao executar ordem")
        return False

    res = verificar_resultado(api, ativo, direcao)
    enviar_telegram("✅ WIN" if res=="win" else "❌ LOSS")
    return res=="win"

# ========== FLUXO PRINCIPAL ==========
def processar_sinal(api, ativo, direcao):
    win = enviar_sinal(api, ativo, direcao, 0)
    if win:
        enviar_telegram("✅ *SINAL FINALIZADO COM WIN*")
    else:
        enviar_telegram("❌ *SINAL FINALIZADO COM LOSS TOTAL*")

# ========== MAIN ==========
def main():
    api = IQ_Option(EMAIL, SENHA)
    api.connect()
    if not api.check_connect():
        enviar_telegram("❌ Erro ao conectar")
        return
    api.change_balance(TIPO_CONTA)
    enviar_telegram(f"✅ Sala de Sinais Iniciada - {TIPO_CONTA}")
    while True:
        for ativo in ATIVOS:
            direcao = analisar_sinais(api, ativo)
            if direcao:
                processar_sinal(api, ativo, direcao)
            time.sleep(3)

if __name__ == "__main__":
    main()
