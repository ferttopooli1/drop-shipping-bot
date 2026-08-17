#!/bin/bash
set -e

INSTALL_DIR="/opt/dropship-bot"

echo "=============================================="
echo " 🚀 DropShip Bot - Smart Installer / Updater"
echo "=============================================="

# SE JÁ ESTIVER INSTALADO -> MODO UPDATE
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "🔄 Bot detectado em $INSTALL_DIR! Iniciando atualização inteligente..."
    
    cd $INSTALL_DIR
    
    # 1. Backup de segurança do config.json
    if [ -f "config.json" ]; then
        cp config.json config.json.bak
    fi

    # 2. Atualiza o código via Git limpando alterações locais temporárias
    echo "📥 Baixando últimas atualizações do GitHub..."
    git fetch --all
    git reset --hard origin/main

    # 3. Restaura o config.json
    if [ -f "config.json.bak" ]; then
        mv config.json.bak config.json
    fi

    # 4. Atualiza dependências do Python
    echo "📦 Atualizando dependências Python..."
    source venv/bin/activate
    pip install --upgrade pip -q
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt -q
    fi

    # 5. Reinicia o serviço
    echo "🔄 Reiniciando o serviço no systemd..."
    sudo systemctl daemon-reload
    sudo systemctl restart dropship-bot

    echo ""
    echo "=============================================="
    echo "✅ Bot ATUALIZADO com sucesso!"
    echo "=============================================="
    exit 0
fi

# SE NÃO ESTIVER INSTALADO -> MODO INSTALAÇÃO DO ZERO
echo "⚙️ Primeira instalação detectada. Instalando pacotes do sistema..."

sudo apt update
sudo apt install -y python3 python3-pip python3-venv ffmpeg git curl

sudo mkdir -p $INSTALL_DIR
sudo chown -R $USER:$USER $INSTALL_DIR

# Copia os arquivos do repositório clonado
cp -rf ./* $INSTALL_DIR/
cd $INSTALL_DIR

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt -q
else
    pip install python-telegram-bot edge-tts requests pydantic psutil -q
fi

echo ""
echo "--- Configuração Inicial do Telegram ---"
read -p "Cole o Token do seu Bot do Telegram (@BotFather): " BOT_TOKEN
read -p "Digite o seu Chat ID do Telegram (Admin): " ADMIN_ID

cat <<EOF > $INSTALL_DIR/config.json
{
  "bot_token": "$BOT_TOKEN",
  "admin_id": "$ADMIN_ID",
  "language": "en",
  "gemini_api_key": "",
  "pexels_api_key": "",
  "social_accounts": {
    "youtube_channel_id": "",
    "tiktok_session_id": "",
    "instagram_access_token": ""
  }
}
EOF

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

sudo systemctl daemon-reload
sudo systemctl enable dropship-bot
sudo systemctl restart dropship-bot

echo ""
echo "=============================================="
echo "✅ Instalação concluída com sucesso!"
echo "Abra o Telegram e mande /start para começar."
echo "=============================================="
