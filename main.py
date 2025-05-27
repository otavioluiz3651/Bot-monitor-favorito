import requests
import time
from flask import Flask
import threading
import os

# Variáveis de ambiente (configure no Render)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Envia mensagens para o Telegram
def enviar_alerta_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': mensagem}
    resposta = requests.post(url, data=payload)
    if resposta.status_code != 200:
        print("Erro ao enviar alerta:", resposta.text)

# Busca jogos ao vivo da API da SofaScore
def buscar_jogos_ao_vivo():
    url = "https://api.sofascore.com/api/v1/sport/football/events/live"
    resposta = requests.get(url)
    if resposta.status_code == 200:
        return resposta.json().get('events', [])
    else:
        print(f"Erro ao buscar jogos: {resposta.status_code}")
        return []

# Verifica se o mandante é favorito com base nas odds
def mandante_favorito(event_id):
    try:
        url = f"https://api.sofascore.com/api/v1/event/{event_id}/odds/1/all"
        r = requests.get(url)
        if r.status_code != 200:
            return None
        dados = r.json()

        for mercado in dados.get('markets', []):
            if mercado.get('marketName') == 'Match Winner':
                opcoes = mercado.get('outcomes', [])
                print(f"Odds para o jogo {event_id}:", opcoes)  # Debug

                odd_mandante = next((o['odds'] for o in opcoes if o.get('label') in ['1', 'home']), None)
                odd_visitante = next((o['odds'] for o in opcoes if o.get('label') in ['2', 'away']), None)

                if odd_mandante is not None and odd_visitante is not None:
                    return odd_mandante < odd_visitante
        return None
    except Exception as e:
        print(f"Erro ao buscar odds para {event_id}: {e}")
        return None

# Verifica se algum jogo atende aos critérios e envia alerta
def analisar_jogos(jogos_alertados):
    jogos = buscar_jogos_ao_vivo()
    for jogo in jogos:
        try:
            mandante = jogo["homeTeam"]["name"]
            visitante = jogo["awayTeam"]["name"]
            placar_mandante = jogo["homeScore"]["current"]
            placar_visitante = jogo["awayScore"]["current"]
            jogo_id = jogo["id"]

            if (placar_mandante - placar_visitante) >= 2:
                if jogo_id not in jogos_alertados:
                    favorito = mandante_favorito(jogo_id)
                    if favorito:
                        link = f"https://www.sofascore.com/{mandante.lower().replace(' ', '-')}-vs-{visitante.lower().replace(' ', '-')}/{jogo['customId']}"
                        mensagem = f"⚠️ Alerta de Jogo com {placar_mandante}x{placar_visitante}!\n{mandante} está vencendo com 2 gols de vantagem e era o favorito.\n\nVer ao vivo: {link}"
                        print("Enviando alerta:", mensagem)
                        enviar_alerta_telegram(mensagem)
                        jogos_alertados.add(jogo_id)
                    else:
                        print(f"{mandante} x {visitante}: mandante não era favorito.")
        except Exception as e:
            print("Erro ao processar jogo:", e)

# Loop contínuo de monitoramento
def monitorar():
    jogos_alertados = set()
    print("Monitoramento iniciado. Verificando a cada 1 minuto...")
    while True:
        analisar_jogos(jogos_alertados)
        time.sleep(60)

# Servidor Flask (para manter Render acordado)
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot está rodando no Render!"

# Iniciar monitoramento em segundo plano
threading.Thread(target=monitorar, daemon=True).start()

# Iniciar Flask (fica como processo principal)
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
