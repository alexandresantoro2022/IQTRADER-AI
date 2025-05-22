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
ATIVOS = ["EURGBP-OTC", "EURUSD-OTC", "GBPUSD-OTC", "USDJPY-OTC"]
TIPO_CONTA = "REAL"
VALOR_INICIAL = 5           # Valor de entrada em BRL
EXPIRACAO = 1               # Expiração em minutos
PERIODO_CANDLE = 60         # Duração do candle em segundos
GALE_MAX = 1
# Parâmetros de EMAs
PERIOD_EMAA = 5
PERIOD_EMAB = 13
PERIOD_EMAC = 34
PERIOD_EMAD = 89

# ========== TELEGRAM ==========
TELEGRAM_TOKEN = "6658940055:AAF33sglHPsVkKeqJuyckctjq__Wf5oSGeg"
CHAT_ID = "-1002110710539"

# ========== MODELO DE IA ==========
try:
    model = joblib.load('model.pkl')
    ia_ativa = True
    print("✅ IA carregada com sucesso.")
except FileNotFoundError:
    ia_ativa = False
    print("⚠️ model.pkl não encontrado; IA desativada.")
    class DummyModel:
        def predict(self, feats):
            return [None]
    model = DummyModel()

# ========== ESTATÍSTICAS ==========
estatisticas = {"wins":0, "losses":0, "sequencia_wins":0, "maior_sequencia":0}

# ========== UTILITÁRIOS ==========
def enviar_telegram(msg):
    print(f"[TELEGRAM] {msg}")  # log no console
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        resp = requests.post(url, json=data)
        print(f"[TELEGRAM_STATUS] {resp.status_code}")
    except Exception as e:
        print("Erro ao enviar telegram:", e)

# Checa se ativo está aberto

def esta_aberto(api, ativo):
    try:
        all_times = api.get_all_open_time()
        now = int(time.time())
        for item in all_times.get('result', []):
            if item.get('name') == ativo:
                for session in item.get('sessions', []):
                    start, end = session.get('start_timestamp'), session.get('end_timestamp')
                    if start <= now <= end:
                        return True
    except Exception as e:
        print("Erro checando horário aberto:", e)
    return False

# Extrai 4 features para IA: EMAA, EMAB em close e EMAC, EMAD em HLC3
def extrair_features(candles):
    closes = np.array([c['close'] for c in candles])
    hlc3 = np.array([(c['max'] + c['min'] + c['close'])/3 for c in candles])
    def ema(arr, period):
        w = 2/(period+1)
        weights = w * (1-w)**np.arange(period)[::-1]
        return np.dot(arr[-period:], weights)
    f1 = ema(closes, PERIOD_EMAA)
    f2 = ema(closes, PERIOD_EMAB)
    f3 = ema(hlc3, PERIOD_EMAC)
    f4 = ema(hlc3, PERIOD_EMAD)
    print(f"[FEATURES] f1={f1:.4f}, f2={f2:.4f}, f3={f3:.4f}, f4={f4:.4f}")
    return np.array([f1, f2, f3, f4]).reshape(1, -1)

# Analisa sinal com IA ou fallback simples
def analisar_sinais(api, ativo):
    candles = api.get_candles(ativo, PERIODO_CANDLE, 100, time.time())
    candles.reverse()
    if ia_ativa:
        feats = extrair_features(candles)
        pred = model.predict(feats)[0]
        print(f"[PREDICTION] {ativo} -> {pred}")
        return pred
    last = candles[-1]
    fallback = "call" if last['close'] > last['open'] else "put"
    print(f"[FALLBACK] {ativo} -> {fallback}")
    return fallback

# Verifica resultado após expiração
def verificar_resultado(api, ativo, direcao):
    print(f"[RESULT] esperando expiração de {EXPIRACAO}m para {ativo} {direcao}")
    time.sleep(EXPIRACAO*60)
    candle = api.get_candles(ativo, PERIODO_CANDLE, 1, time.time())[0]
    result = "win" if (direcao=="call" and candle['close']>candle['open']) or (direcao=="put" and candle['close']<candle['open']) else "loss"
    print(f"[RESULT] {ativo} {direcao} -> {result}")
    return result

# Envia sinal e executa ordem via API
def enviar_sinal(api, ativo, direcao, gale):
    if not esta_aberto(api, ativo):
        enviar_telegram(f"⏰ {ativo} fechado; pulando.")
        return None
    now_ts = datetime.datetime.now()
    hora = (now_ts + datetime.timedelta(minutes=1)).strftime("%H:%M")
    tag = "🟢 ENTRADA" if gale==0 else f"🔁 GALE {gale}"
    enviar_telegram(f"{tag}\n🎯 Ativo: `{ativo}`\n📈 Direção: *{direcao.upper()}*\n🕒 Entrada: {hora}\n🌀 Expiração: {EXPIRACAO}min")
    for t in range(3):
        ok, resp = api.buy_digital_spot(ativo, VALOR_INICIAL, direcao, EXPIRACAO)
        msg = resp.get('message','') if isinstance(resp, dict) else ''
        print(f"[ORDER] tentativa {t+1}, ok={ok}, msg={msg or resp}")
        if ok:
            enviar_telegram(f"🎫 Ordem ID: `{resp}`")
            break
        if 'rejected' in msg.lower():
            enviar_telegram(f"🚫 Risco: {msg}")
            return None
        enviar_telegram(f"⏱️ Timeout {t+1}/3")
        time.sleep(1)
    else:
        enviar_telegram(f"⚠️ Falha ordem: {msg or resp}")
        return False
    resultado = verificar_resultado(api, ativo, direcao)
    enviar_telegram("✅ WIN" if resultado=="win" else "❌ LOSS")
    return resultado=="win"

# Processa sinal principal e gales
def processar_sinal(api, ativo, direcao):
    print(f"[PROCESS] iniciando para {ativo} {direcao}")
    r = enviar_sinal(api, ativo, direcao, 0)
    if r is None: return
    if r:
        estatisticas['wins']+=1; estatisticas['sequencia_wins']+=1
        estatisticas['maior_sequencia']=max(estatisticas['maior_sequencia'],estatisticas['sequencia_wins'])
        enviar_telegram("✅ *SINAL FINALIZADO COM WIN*")
    else:
        estatisticas['losses']+=1; estatisticas['sequencia_wins']=0
        for g in range(1,GALE_MAX+1):
            r2=enviar_sinal(api, ativo, direcao, g)
            if r2 is None: return
            if r2:
                estatisticas['wins']+=1; estatisticas['sequencia_wins']+=1
                enviar_telegram("✅ *SINAL FINALIZADO COM WIN*")
                break
            else:
                estatisticas['losses']+=1; estatisticas['sequencia_wins']=0
                if g==GALE_MAX: enviar_telegram("❌ *SINAL FINALIZADO COM LOSS TOTAL*")
    st = (
        f"📊 *ESTATÍSTICAS*\n"
        f"✅ Wins: {estatisticas['wins']}\n"
        f"❌ Losses: {estatisticas['losses']}\n"
        f"🔥 Seq: {estatisticas['sequencia_wins']}\n"
        f"🏆 Max Seq: {estatisticas['maior_sequencia']}"
    )
    enviar_telegram(st)

# Main
def main():
    print(f"▶️ Iniciando bot em {datetime.datetime.now().isoformat()}")
    api = IQ_Option(EMAIL, SENHA)
    print("[API] Conectando...")
    api.connect()
    if not api.check_connect():
        enviar_telegram("❌ Erro conexão")
        return
    api.change_balance(TIPO_CONTA)
    enviar_telegram(f"✅ Sala AI Iniciada - {TIPO_CONTA}")
    while True:
        for ativo in ATIVOS:
            direcao = analisar_sinais(api, ativo)
            if direcao:
                processar_sinal(api, ativo, direcao)
            time.sleep(3)

if __name__ == "__main__":
    main()
