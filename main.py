import requests
import time
from flask import Flask
import threading
import os

# Pegando variáveis do ambiente
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def enviar_alerta_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': mensagem}
    resposta = requests.post(url, data=payload)
    if resposta.status_code != 200:
        print("Erro ao enviar alerta:", resposta.text)

def buscar_jogos_ao_vivo():
    url = "https://api.sofascore.com/api/v1/sport/football/events/live"
    resposta = requests.get(url)
    if resposta.status_code == 200:
        return resposta.json().get('events', [])
    else:
        print(f"Erro ao buscar jogos: {resposta.status_code}")
        return []

def mandante_favorito(event_id):
    try:
        url = f"https://api.sofascore.com/api/v1/event/{event_id}/odds/1/all"
        r = requests.get(url)
        if r.status_code != 200:
            return None
        dados = r.json()

        for casa_apostas in dados.get('markets', []):
            if casa_apostas.get('marketName') == 'Match Winner':
                opcoes = casa_apostas.get('outcomes', [])
                odd_mandante = next((o['odds'] for o in opcoes if o['label'] == '1'), None)
                odd_visitante = next((o['odds'] for o in opcoes if o['label'] == '2'), None)

                if odd_mandante is not None and odd_visitante is not None:
                    return odd_mandante < odd_visitante
        return None
    except Exception as e:
        print(f"Erro ao buscar odds para {event_id}: {e}")
        return None

def analisar_jogos(jogos_alertados):
    jogos = buscar_jogos_ao_vivo()
    for jogo in jogos:
        try:
            mandante = jogo["homeTeam"]["name"]
            visitante = jogo["awayTeam"]["name"]
            placar_mandante = jogo["homeScore"]["current"]
            placar_visitante = jogo["awayScore"]["current"]
            jogo_id = jogo["id"]

            if (placar_mandante - placar_visitante) >= 2 and jogo_id not in jogos_alertados:
                favorito = mandante_favorito(jogo_id)
                if favorito:
                    link = f"https://www.sofascore.com/{mandante.lower().replace(' ', '-')}-vs-{visitante.lower().replace(' ', '-')}/{jogo['customId']}"
                    mensagem = f"{mandante} {placar_mandante} x {placar_visitante} {visitante} — Mandante abriu 2 gols de vantagem (e era favorito)\n{link}"
                    print("Enviando alerta:", mensagem)
                    enviar_alerta_telegram(mensagem)
                    jogos_alertados.add(jogo_id)
                else:
                    print(f"{mandante} x {visitante}: mandante não era favorito.")
        except Exception as e:
            print("Erro ao processar jogo:", e)

def monitorar():
    jogos_alertados = set()
    print("Monitoramento iniciado. Verificando a cada 1 minuto...")
    while True:
        analisar_jogos(jogos_alertados)
        time.sleep(60)

# ---------------------------
# Parte para manter o bot ativo no Render
# ---------------------------
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot está rodando no Render!"

def iniciar_flask():
    app.run(host="0.0.0.0", port=10000)

# Iniciar o Flask em segundo plano
threading.Thread(target=iniciar_flask).start()

# Iniciar o monitoramento
monitorar()
