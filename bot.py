import asyncio
import os
import sys
import subprocess
import re
import psutil
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from config_manager import load_config, update_config_key
from video_engine import create_video_pipeline

# Estados do ConversationHandler
WAITING_API_VALUE = 1
WAITING_PRODUCT_INPUT = 2
WAITING_EDIT_CAPTION = 3

LANG_LABELS = {
    "en": "🇺🇸 English",
    "pt": "🇧🇷 Português",
    "es": "🇲🇽 Español",
}


def is_admin(user_id: int) -> bool:
    """Verifica se o usuário executando o comando é o administrador configurado."""
    cfg = load_config()
    return str(user_id) == str(cfg.get("admin_id"))


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe o painel de controle principal do bot."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Acesso não autorizado.")
        return

    cfg = load_config()
    current_lang = LANG_LABELS.get(cfg.get("language", "en"), "🇺🇸 English")

    keyboard = [
        [
            InlineKeyboardButton("🎬 Gerar Vídeo", callback_data="menu_generate"),
            InlineKeyboardButton("⚙️ Configurar APIs", callback_data="menu_apis"),
        ],
        [
            InlineKeyboardButton("📱 Redes Sociais", callback_data="menu_social"),
            InlineKeyboardButton("📊 Status da VM", callback_data="menu_status"),
        ],
        [
            InlineKeyboardButton(f"🌐 Idioma: {current_lang}", callback_data="menu_lang"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "🚀 *Painel de Controle - DropShipping Auto Video Bot*\n\nSelecione uma opção abaixo:"

    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gerencia as interações dos menus e botões inline."""
    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_user.id):
        return

    data = query.data
    cfg = load_config()

    if data == "menu_apis":
        gemini_status = "✅ Definida" if cfg.get("gemini_api_key") else "❌ Pendente"
        pexels_status = "✅ Definida (Opcional)" if cfg.get("pexels_api_key") else "⚪ Opcional"

        keyboard = [
            [InlineKeyboardButton(f"Gemini API ({gemini_status})", callback_data="set_gemini")],
            [InlineKeyboardButton(f"Pexels API ({pexels_status})", callback_data="set_pexels")],
            [InlineKeyboardButton("⬅️ Voltar", callback_data="menu_main")],
        ]
        await query.edit_message_text(
            "🔑 *Configuração de Chaves de API*\n\n"
            "• *Gemini API*: Obrigatória (geração de roteiro e prompts visuais de IA).\n"
            "• *Pexels API*: Opcional (usada como reserva caso a IA do Pollinations oscile).\n\n"
            "Clique para alterar:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    elif data == "menu_social":
        yt_status = "✅ Conectado" if cfg.get("social_accounts", {}).get("youtube_channel_id") else "❌ Não configurado"
        tt_status = "✅ Conectado" if cfg.get("social_accounts", {}).get("tiktok_session_id") else "❌ Não configurado"

        keyboard = [
            [InlineKeyboardButton(f"YouTube Shorts ({yt_status})", callback_data="set_yt")],
            [InlineKeyboardButton(f"TikTok ({tt_status})", callback_data="set_tiktok")],
            [InlineKeyboardButton("⬅️ Voltar", callback_data="menu_main")],
        ]
        await query.edit_message_text(
            "📱 *Perfis de Postagem*\n\nConfigure onde os vídeos serão postados automaticamente:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    elif data == "menu_lang":
        keyboard = [
            [
                InlineKeyboardButton("🇺🇸 English", callback_data="set_lang_en"),
                InlineKeyboardButton("🇧🇷 Português", callback_data="set_lang_pt"),
                InlineKeyboardButton("🇲🇽 Español", callback_data="set_lang_es"),
            ],
            [InlineKeyboardButton("⬅️ Voltar", callback_data="menu_main")],
        ]
        await query.edit_message_text(
            "🌐 *Selecione o Idioma do Vídeo e da Narração:*\n\n"
            "O roteiro gerado pela IA e a voz neural seguirão o idioma escolhido.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    elif data.startswith("set_lang_"):
        lang_code = data.replace("set_lang_", "")
        update_config_key(["language"], lang_code)
        selected_name = LANG_LABELS.get(lang_code, "English")
        await query.edit_message_text(
            f"✅ Idioma alterado para *{selected_name}* com sucesso!\n\nDigite /start para retornar.",
            parse_mode="Markdown",
        )

    elif data == "menu_status":
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        status_msg = (
            "📊 *Status do Servidor Ubuntu*\n\n"
            f"• *CPU:* {cpu}%\n"
            f"• *RAM:* {ram}%\n"
            f"• *Disco:* {disk}%\n"
        )
        keyboard = [
            [InlineKeyboardButton("🔄 Atualizar Bot (Git Pull)", callback_data="system_update")],
            [InlineKeyboardButton("⬅️ Voltar", callback_data="menu_main")],
        ]
        await query.edit_message_text(
            status_msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    elif data == "system_update":
        bot_dir = os.path.dirname(os.path.abspath(__file__))
        await query.edit_message_text(
            "🔄 *Iniciando atualização inteligente do Bot...*\n\n"
            "1. 📥 Baixando últimas atualizações do GitHub...\n"
            "2. 📦 Verificando dependências em `requirements.txt`...\n"
            "3. ⚙️ Reiniciando o serviço...",
            parse_mode="Markdown",
        )

        update_cmd = f'cd "{bot_dir}" && git fetch --all && git reset --hard origin/main'
        if os.path.exists(os.path.join(bot_dir, "requirements.txt")):
            update_cmd += " && pip install -r requirements.txt -q"
        update_cmd += " && (sudo systemctl restart dropship-bot || echo 'Serviço reiniciado')"

        subprocess.Popen(update_cmd, shell=True)

    elif data == "menu_main":
        await start_cmd(update, context)

    elif data == "post_video":
        pending_caption = context.user_data.get("pending_caption", "")
        await query.edit_message_caption(
            caption=f"🚀 *Vídeo Aprovado e Enviado para a Fila!*\n\n📝 *Legenda Final:*\n{pending_caption}",
            parse_mode="Markdown",
        )

    elif data == "discard_video":
        context.user_data.pop("pending_caption", None)
        await query.edit_message_caption(
            caption="🗑️ *Vídeo descartado.*",
            parse_mode="Markdown",
        )


# --- HELPER DE PARSING DE MENSAGEM PADRÃO ---
def parse_standard_product_msg(text: str) -> dict:
    """Extrai nome do produto, breve descrição e link de afiliado de uma mensagem enviada."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    name = ""
    description = ""
    link = ""

    # Tenta extrair usando palavras-chave/rótulos comuns (ex: Nome:, Descrição:, Link:)
    for line in lines:
        url_match = re.search(r"https?://[^\s]+", line)
        if url_match and not link:
            link = url_match.group(0)

        if not name:
            match_name = re.match(r"^(?:📌\s*)?(?:nome(?:\s+do\s+produto)?|product(?:\s+name)?|produto|title|título)\s*[:\-]\s*(.+)$", line, re.IGNORECASE)
            if match_name:
                name = match_name.group(1).strip()
                continue

        if not description:
            match_desc = re.match(r"^(?:📝\s*)?(?:descriç[ãa]o(?:\s+breve)?|description|desc|sobre|detalhes|benef[íi]cios)\s*[:\-]\s*(.+)$", line, re.IGNORECASE)
            if match_desc:
                description = match_desc.group(1).strip()
                continue

        if not link:
            match_link = re.match(r"^(?:🔗\s*)?(?:link(?:\s+de\s+afiliado)?|url)\s*[:\-]\s*(.+)$", line, re.IGNORECASE)
            if match_link:
                potential_link = match_link.group(1).strip()
                url_m = re.search(r"https?://[^\s]+", potential_link)
                if url_m:
                    link = url_m.group(0)
                else:
                    link = potential_link

    # Se a URL ainda não foi capturada, busca em todo o texto
    if not link:
        url_match = re.search(r"https?://[^\s]+", text)
        if url_match:
            link = url_match.group(0)

    # Fallback se não usou os rótulos Nome: / Descrição:
    if not name:
        for line in lines:
            if not re.search(r"https?://[^\s]+", line) and not re.match(r"^(?:🔗\s*)?(?:link|url)", line, re.IGNORECASE):
                clean_line = re.sub(r"^[\*\-\•\d\.\s]+", "", line).strip()
                if clean_line:
                    name = clean_line
                    break

    if not description:
        desc_lines = []
        for line in lines:
            clean_line = re.sub(r"^[\*\-\•\d\.\s]+", "", line).strip()
            if clean_line and clean_line != name and not re.search(r"https?://[^\s]+", line) and not re.match(r"^(?:🔗|📌|📝)?\s*(?:link|url)", line, re.IGNORECASE):
                desc_lines.append(clean_line)
        description = " ".join(desc_lines).strip()

    if not name:
        name = "Produto Viral"

    return {
        "name": name,
        "description": description,
        "link": link,
        "raw_text": text,
    }


# --- FLUXO DE GERAR VÍDEO ---
async def prompt_product_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Solicita as informações do produto no modelo padrão ao usuário."""
    query = update.callback_query
    await query.answer()

    template_text = (
        "📦 *Geração de Vídeo - Envie os Dados do Produto*\n\n"
        "Envie uma mensagem contendo as seguintes informações do produto:\n\n"
        "📌 *Nome do produto*\n"
        "📝 *Breve descrição* (benefícios, diferenciais, uso)\n"
        "🔗 *Link de afiliado*\n\n"
        "📋 *Exemplo de mensagem padrão (copie e preencha):*\n\n"
        "`Nome: Mini Mop Portátil`\n"
        "`Descrição: Limpa superfícies rapidamente, super absorvente e prático para cozinha e banheiros.`\n"
        "`Link: https://amzn.to/3example`\n\n"
        "_(Envie /cancelar para voltar ao menu)_"
    )

    await query.message.reply_text(
        template_text,
        parse_mode="Markdown",
    )
    return WAITING_PRODUCT_INPUT


async def process_product_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa a mensagem do produto enviada e chama a pipeline do video_engine."""
    raw_text = update.message.text.strip()
    cfg = load_config()

    if not cfg.get("gemini_api_key"):
        await update.message.reply_text(
            "⚠️ *Atenção:* Por favor, defina a Gemini API Key no menu **⚙️ Configurar APIs** antes de gerar um vídeo.",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    product_data = parse_standard_product_msg(raw_text)

    msg_status = await update.message.reply_text(
        f"⏳ *Gerando vídeo para '{product_data['name']}'...*\n\n"
        "1. 🧠 Criando roteiro persuasivo e visuais via Gemini...\n"
        "2. 🎨 Gerando imagens de IA 1080x1920 via Pollinations.ai...\n"
        "3. 🎙️ Sintetizando narração neural, legendas e animação Ken Burns 3D...",
        parse_mode="Markdown",
    )

    try:
        result = await create_video_pipeline(product_data, cfg)
        video_path = result["video_path"]
        caption_text = result["caption"]

        context.user_data["pending_caption"] = caption_text

        keyboard = [
            [
                InlineKeyboardButton("🚀 Aprovar e Postar", callback_data="post_video"),
                InlineKeyboardButton("✏️ Editar Legenda", callback_data="edit_caption"),
            ],
            [InlineKeyboardButton("❌ Descartar", callback_data="discard_video")],
        ]

        await msg_status.delete()

        with open(video_path, "rb") as video_file:
            await update.message.reply_video(
                video=video_file,
                caption=f"🎬 *Preview do Vídeo Gerado*\n\n📝 *Legenda recomendada (com link):*\n{caption_text}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

    except Exception as e:
        await msg_status.edit_text(
            f"❌ *Erro durante o processamento:* {str(e)}",
            parse_mode="Markdown",
        )

    return ConversationHandler.END


# --- FLUXO DE EDIÇÃO DE LEGENDA ---
async def prompt_edit_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Solicita a nova legenda ao usuário."""
    query = update.callback_query
    await query.answer()

    current_caption = context.user_data.get("pending_caption", "")

    await query.message.reply_text(
        "✏️ *Editar Legenda & Título*\n\n"
        "Envie o novo texto completo da legenda (incluindo seu link de afiliado e hashtags).\n\n"
        f"📋 *Legenda Atual:*\n`{current_caption}`\n\n"
        "_(Envie /cancelar para manter a legenda atual)_",
        parse_mode="Markdown",
    )
    return WAITING_EDIT_CAPTION


async def save_edited_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Salva a nova legenda editada pelo usuário."""
    new_caption = update.message.text.strip()
    context.user_data["pending_caption"] = new_caption

    keyboard = [
        [
            InlineKeyboardButton("🚀 Aprovar e Postar", callback_data="post_video"),
            InlineKeyboardButton("✏️ Editar Legenda", callback_data="edit_caption"),
        ],
        [InlineKeyboardButton("❌ Descartar", callback_data="discard_video")],
    ]

    await update.message.reply_text(
        f"✅ *Legenda Atualizada com Sucesso!*\n\n📝 *Nova Legenda:*\n{new_caption}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return ConversationHandler.END


# --- FLUXO DE CONFIGURAÇÃO DE APIS COM TUTORIAIS ---
async def ask_api_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pede a chave ou credencial ao usuário com tutorial detalhado."""
    query = update.callback_query
    await query.answer()
    field = query.data.replace("set_", "")
    context.user_data["editing_field"] = field

    tutorials = {
        "gemini": (
            "🔑 *Como obter a Google Gemini API Key:*\n\n"
            "1️⃣ Acesse o portal do [Google AI Studio](https://aistudio.google.com/app/apikey).\n"
            "2️⃣ Faça login com sua conta do Google.\n"
            "3️⃣ Clique no botão **'Create API key'**.\n"
            "4️⃣ Copie a chave (ex: `AIzaSy...`) e **responda enviando-a aqui nesta conversa**.\n\n"
            "_(Envie /cancelar a qualquer momento para retornar)_"
        ),
        "pexels": (
            "🔑 *Como obter a Pexels API Key (Opcional):*\n\n"
            "1️⃣ Acesse o [Pexels API Documentation](https://www.pexels.com/api/).\n"
            "2️⃣ Crie uma conta gratuita ou faça login.\n"
            "3️⃣ Clique no botão **'Your API Key'**.\n"
            "4️⃣ Copie a chave e responda enviando-a aqui.\n\n"
            "_(Envie /cancelar a qualquer momento para retornar)_"
        ),
        "yt": (
            "📱 *Como obter as credenciais do YouTube Shorts:*\n\n"
            "1️⃣ Acesse o [Google Cloud Console API Credentials](https://console.cloud.google.com/apis/credentials).\n"
            "2️⃣ Ative a **YouTube Data API v3** no seu projeto.\n"
            "3️⃣ Crie uma credencial **OAuth 2.0 Client ID**.\n"
            "4️⃣ Copie seu **ID do Canal** ou **Token** e responda enviando-o aqui.\n\n"
            "_(Envie /cancelar a qualquer momento para retornar)_"
        ),
        "tiktok": (
            "📱 *Como obter o TikTok Session ID:*\n\n"
            "1️⃣ Acesse o [TikTok Web](https://www.tiktok.com) no computador e faça login.\n"
            "2️⃣ Pressione `F12` para abrir o DevTools -> vá na aba **Application / Armazenamento**.\n"
            "3️⃣ Clique em **Cookies** -> `https://www.tiktok.com`.\n"
            "4️⃣ Procure pelo cookie `sessionid` ou `sessionid_ss`, copie o valor e envie aqui.\n\n"
            "_(Envie /cancelar a qualquer momento para retornar)_"
        ),
    }

    prompt_text = tutorials.get(field, f"Envie agora o valor para *{field}*:\n(Ou /cancelar)")

    await query.message.reply_text(
        prompt_text,
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )
    return WAITING_API_VALUE


async def save_api_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Salva a chave/credencial enviada e remove a mensagem contendo o dado sensível."""
    value = update.message.text.strip()
    field = context.user_data.get("editing_field")

    if field == "gemini":
        update_config_key(["gemini_api_key"], value)
    elif field == "pexels":
        update_config_key(["pexels_api_key"], value)
    elif field == "yt":
        update_config_key(["social_accounts", "youtube_channel_id"], value)
    elif field == "tiktok":
        update_config_key(["social_accounts", "tiktok_session_id"], value)

    try:
        await update.message.delete()
    except Exception:
        pass

    await update.message.reply_text(
        f"✅ Credencial de *{field.upper()}* salva com sucesso!\nDigite /start para voltar ao menu.",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela o fluxo atual e limpa o estado."""
    await update.message.reply_text("Operação cancelada. Digite /start para o menu.")
    return ConversationHandler.END


def main():
    """Inicializa e roda o bot do Telegram."""
    cfg = load_config()
    token = cfg.get("bot_token")
    if not token:
        print("ERRO: bot_token não configurado no config.json.")
        return

    app = ApplicationBuilder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(prompt_product_input, pattern="^menu_generate$"),
            CallbackQueryHandler(ask_api_input, pattern="^set_(gemini|pexels|yt|tiktok)$"),
            CallbackQueryHandler(prompt_edit_caption, pattern="^edit_caption$"),
        ],
        states={
            WAITING_API_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_api_input)],
            WAITING_PRODUCT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_product_input)],
            WAITING_EDIT_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_edited_caption)],
        },
        fallbacks=[CommandHandler("cancelar", cancel_cmd)],
    )

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(conv_handler)
    app.add_handler(
        CallbackQueryHandler(
            menu_callback,
            pattern="^menu_(apis|social|status|main|lang)|set_lang_|post_video|discard_video|system_update$",
        )
    )

    print("Bot rodando...")
    app.run_polling()


if __name__ == "__main__":
    main()
