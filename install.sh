#!/bin/bash
set -e

echo "=============================================="
echo "   Instalador Automático - Video Generator Bot "
echo "=============================================="

# 1. Instalação de dependências do sistema
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ffmpeg git curl

# 2. Diretório de instalação
INSTALL_DIR="/opt/dropship-bot"
sudo mkdir -p $INSTALL_DIR
sudo chown -R $USER:$USER $INSTALL_DIR

# Copia ou clona os arquivos do projeto para o diretório
cp -r ./* $INSTALL_DIR/ || true
cd $INSTALL_DIR

# 3. Criação do ambiente virtual Python
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install python-telegram-bot edge-tts requests pydantic psutil

# 4. Configuração inicial do Telegram (Token e Admin ID)
echo ""
echo "--- Configuração Inicial do Telegram ---"
read -p "Cole o Token do seu Bot do Telegram (@BotFather): " BOT_TOKEN
read -p "Digite o seu Chat ID do Telegram (para ser o Admin único): " ADMIN_ID

# Salva arquivo base de configuração
cat <<EOF > $INSTALL_DIR/config.json
{
  "bot_token": "$BOT_TOKEN",
  "admin_id": "$ADMIN_ID",
  "gemini_api_key": "",
  "pexels_api_key": "",
  "social_accounts": {
    "youtube_channel_id": "",
    "tiktok_session_id": "",
    "instagram_access_token": ""
  }
}
EOF

# 5. Criação do serviço systemd para rodar 24/7
SERVICE_FILE="/etc/systemd/system/dropship-bot.service"
sudo bash -c "cat <<EOF > $SERVICE_FILE
[Unit]
Description=Dropship Auto Video Generator Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF"

# 6. Ativação do serviço
sudo systemctl daemon-reload
sudo systemctl enable dropship-bot
sudo systemctl restart dropship-bot

echo "=============================================="
echo "✅ Instalação concluída com sucesso!"
echo "Abra o Telegram e mande /start para configurar suas APIs."
echo "=============================================="
