import requests
import time

TELEGRAM_TOKEN = '8186161874:AAE_7I2Zw9eWKOkkttsXuuv6UX04ctIINHg'
CHAT_ID = '306517061'

def enviar_alerta_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': mensagem}
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        print("Erro ao enviar alerta:", response.text)

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
        data = r.json()

        for bookmaker in data.get('markets', []):
            if bookmaker.get('marketName') == 'Match Winner':
                outcomes = bookmaker.get('outcomes', [])
                home_odd = next((o['odds'] for o in outcomes if o['label'] == '1'), None)
                away_odd = next((o['odds'] for o in outcomes if o['label'] == '2'), None)

                if home_odd is not None and away_odd is not None:
                    return home_odd < away_odd  # True se mandante é favorito
        return None
    except Exception as e:
        print(f"Erro ao buscar odds para {event_id}: {e}")
        return None

def analisar_jogos(jogos_alertados):
    jogos = buscar_jogos_ao_vivo()
    for jogo in jogos:
        try:
            home = jogo["homeTeam"]["name"]
            away = jogo["awayTeam"]["name"]
            home_score = jogo["homeScore"]["current"]
            away_score = jogo["awayScore"]["current"]
            game_id = jogo["id"]

            if (home_score - away_score) >= 2 and game_id not in jogos_alertados:
                favorito = mandante_favorito(game_id)
                if favorito:
                    link = f"https://www.sofascore.com/{home.lower().replace(' ', '-')}-vs-{away.lower().replace(' ', '-')}/{jogo['customId']}"
                    mensagem = f"{home} {home_score} x {away_score} {away} — Mandante abriu 2 gols de vantagem (e era favorito)\n{link}"
                    print("Enviando alerta:", mensagem)
                    enviar_alerta_telegram(mensagem)
                    jogos_alertados.add(game_id)
                else:
                    print(f"{home} x {away}: mandante não era favorito.")
        except Exception as e:
            print("Erro ao processar jogo:", e)

def monitorar():
    jogos_alertados = set()
    print("Monitoramento iniciado. Verificando a cada 1 minuto...")
    while True:
        analisar_jogos(jogos_alertados)
        time.sleep(60)

# Iniciar
monitorar()
