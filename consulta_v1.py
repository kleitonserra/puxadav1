import os
import re
import requests
import telebot
from datetime import datetime
from flask import Flask, request

# 🔹 Token do bot
TELEGRAM_BOT_TOKEN = "7722623166:AAFKoGOqwAWrK6K6c46wdPgjyF8lMW9RSoo"
CHAT_LOGS_ID = "-1002456631135"  # ID do chat/grupo onde os logs serão enviados
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# 🔹 Remover Webhook se existir
bot.remove_webhook()
print("Webhook removido com sucesso!")

# 🔹 Função para obter token de acesso (a mesma do código anterior)
def obter_token():
    url = "https://servicos-cloud.saude.gov.br/pni-bff/v1/autenticacao/tokenAcesso"
    headers = {
        "accept": "application/json",
        "Referer": "https://si-pni.saude.gov.br/",
        "sec-ch-ua": "\"Not_A Brand\";v=\"99\", \"Google Chrome\";v=\"109\", \"Chromium\";v=\"109\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        "X-Authorization": "Basic Y2FybGluaG9zLmVkdS4xMEBob3RtYWlsLmNvbTojRXNwMjEwNDAw"
    }
    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        token = re.search(r'"accessToken":"(.*?)"', response.text)
        if token:
            return token.group(1)
    return None

# 🔹 Função para calcular signo (a mesma do código anterior)
def calcular_signo(data_nascimento):
    signos = [
        (1, 20, 'Aquário'), (2, 19, 'Peixes'), (3, 21, 'Áries'), (4, 20, 'Touro'),
        (5, 21, 'Gêmeos'), (6, 21, 'Câncer'), (7, 23, 'Leão'), (8, 23, 'Virgem'),
        (9, 23, 'Libra'), (10, 23, 'Escorpião'), (11, 22, 'Sagitário'), (12, 22, 'Capricórnio')
    ]
    try:
        nascimento = datetime.strptime(data_nascimento, "%Y-%m-%d")
        dia, mes = nascimento.day, nascimento.month
        for m, dia_limite, signo in signos:
            if (mes == m and dia <= dia_limite) or (mes < m):
                return signo
    except ValueError:
        return "Data inválida"
    return 'Capricórnio'

# 🔹 Função para salvar consulta em arquivo (a mesma do código anterior)
def salvar_em_arquivo(identificador, dados):
    filename = f"{identificador}.txt"
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(dados)
    return filename

# 🔹 Função para extrair dados e formatar a resposta (a mesma do código anterior)
def extrair_dados_cpf(response_json, user):
    if not response_json or 'records' not in response_json:
        return "Nenhum dado encontrado para o CPF."
    record = response_json["records"][0]
    nome = record.get("nome", "Sem informação")
    cpf = record.get("cpf", "Sem informação")
    data_nascimento = record.get("dataNascimento", "Sem informação")
    signo = calcular_signo(data_nascimento)
    mensagem = f"""🔍 *CONSULTA DE CPF* 🔍\n
*🆔 CPF:* {cpf}\n*👤 NOME:* {nome}\n*🎂 NASCIMENTO:* {data_nascimento}\n*🔮 SIGNO:* {signo}\n
👤 *USUÁRIO:* @{user}\n🤖 *BOT:* [Clique aqui](https://t.me/baldwinclientes)\n"""
    return cpf, mensagem

# 🔹 Função para consultar CPF via API (a mesma do código anterior)
def consultar_cpf_api(cpf, token):
    url = f"https://servicos-cloud.saude.gov.br/pni-bff/v1/cidadao/cpf/{cpf}"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Authorization": f"Bearer {token}",
        "Referer": "https://si-pni.saude.gov.br/",
        "sec-ch-ua": "\"Not_A Brand\";v=\"99\", \"Google Chrome\";v=\"109\", \"Chromium\";v=\"109\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

# 🔹 Função para consultar CNPJ via API (a mesma do código anterior)
def consultar_cnpj_api(cnpj):
    url = f"https://receitaws.com.br/v1/cnpj/{cnpj}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

# 🔹 Comando /cpf
@bot.message_handler(commands=['cpf'])
def consultar_cpf(message):
    try:
        cpf = message.text.split()[1]
        user = message.from_user.username if message.from_user.username else "Usuário Desconhecido"
        token = obter_token()  # Obtendo o token
        if token is None:
            bot.reply_to(message, "❌ *Erro ao obter token de acesso.*", parse_mode='Markdown')
            return
        dados = consultar_cpf_api(cpf, token)  # Consultando CPF via API
        if not dados:
            bot.reply_to(message, "❌ *Erro ao buscar os dados do CPF. Tente novamente mais tarde.*", parse_mode='Markdown')
            return
        identificador, resultado = extrair_dados_cpf(dados, user)
        bot.reply_to(message, resultado, parse_mode='Markdown', disable_web_page_preview=True)
        filename = salvar_em_arquivo(identificador, resultado)
        with open(filename, 'rb') as file:
            bot.send_document(message.chat.id, file)
        os.remove(filename)
        # 🔹 Log de sucesso no grupo
        bot.send_message(CHAT_LOGS_ID, f"✅ Consulta de CPF realizada por @{user}.")
    except IndexError:
        bot.reply_to(message, "❗ *Por favor, forneça um CPF após o comando.*\nExemplo: `/cpf 00865889155`", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, "❌ *Erro ao buscar os dados. Tente novamente mais tarde.*", parse_mode='Markdown')

# 🔹 Webhook com Flask
app = Flask(__name__)

@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return '', 200

if __name__ == "__main__":
    # 🔹 Configurar o webhook
    bot.set_webhook(url="https://497e-179-0-119-232.ngrok-free.app/{TELEGRAM_BOT_TOKEN}")
    app.run(host="0.0.0.0", port=5000)
