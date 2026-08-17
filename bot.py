import asyncio
import os
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

# Estados do ConversationHandler
WAITING_API_VALUE = 1
WAITING_PRODUCT_INPUT = 2

def is_admin(user_id: int) -> bool:
    cfg = load_config()
    return str(user_id) == str(cfg.get("admin_id"))

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Acesso não autorizado.")
        return

    keyboard = [
        [
            InlineKeyboardButton("🎬 Gerar Vídeo", callback_data="menu_generate"),
            InlineKeyboardButton("⚙️ Configurar APIs", callback_data="menu_apis"),
        ],
        [
            InlineKeyboardButton("📱 Redes Sociais", callback_data="menu_social"),
            InlineKeyboardButton("📊 Status da VM", callback_data="menu_status"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Suporta chamada tanto por comando /start quanto por callback de botão "Voltar"
    if update.message:
        await update.message.reply_text(
            "🚀 *Painel de Controle - Secret Cart Finds*\n\nSelecione uma opção abaixo:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            "🚀 *Painel de Controle - Secret Cart Finds*\n\nSelecione uma opção abaixo:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_user.id):
        return

    data = query.data
    cfg = load_config()

    if data == "menu_apis":
        gemini_status = "✅ Definida" if cfg.get("gemini_api_key") else "❌ Pendente"
        pexels_status = "✅ Definida" if cfg.get("pexels_api_key") else "❌ Pendente"

        keyboard = [
            [InlineKeyboardButton(f"Gemini API ({gemini_status})", callback_data="set_gemini")],
            [InlineKeyboardButton(f"Pexels API ({pexels_status})", callback_data="set_pexels")],
            [InlineKeyboardButton("⬅️ Voltar", callback_data="menu_main")],
        ]
        await query.edit_message_text(
            "🔑 *Configuração de Chaves de API*\n\nClique para alterar ou cadastrar:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
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
            "📱 *Perfis de Postagem*\n\nConfigure onde os vídeos serão postados:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data == "menu_status":
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        status_msg = (
            "📊 *Status do Servidor Ubuntu ARM*\n\n"
            f"• *CPU:* {cpu}%\n"
            f"• *RAM:* {ram}%\n"
            f"• *Disco:* {disk}%\n"
        )
        keyboard = [[InlineKeyboardButton("⬅️ Voltar", callback_data="menu_main")]]
        await query.edit_message_text(
            status_msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data == "menu_main":
        await start_cmd(update, context)

# --- FLUXO DE GERAR VÍDEO ---
async def prompt_product_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.message.reply_text(
        "📦 *Envie o Produto*\n\n"
        "Envie o **link da Amazon/AliExpress** ou digite o **nome do produto** com uma breve descrição.\n\n"
        "_(Envie /cancelar para voltar ao menu)_",
        parse_mode="Markdown"
    )
    return WAITING_PRODUCT_INPUT

async def process_product_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    product_text = update.message.text.strip()
    
    msg_status = await update.message.reply_text(
        "⏳ *Processando produto...*\n\n1. 🧠 Gerando roteiro em inglês com IA...\n2. 🎙️ Criando voz neural...\n3. 🎬 Renderizando com FFmpeg...",
        parse_mode="Markdown"
    )

    # Aqui é chamada a função do motor (ex: video_engine.generate_video(product_text))
    # Exemplo simulado de resposta:
    await asyncio.sleep(2)
    
    await msg_status.edit_text(
        f"✅ *Vídeo gerado para o produto:*\n`{product_text}`\n\n"
        "🚀 Pronto para postar!",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# --- FLUXO DE CONFIGURAÇÃO DE APIS ---
async def ask_api_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    field = query.data.replace("set_", "")
    context.user_data["editing_field"] = field

    names = {
        "gemini": "Google Gemini API Key",
        "pexels": "Pexels API Key",
        "yt": "YouTube Channel ID / Token",
        "tiktok": "TikTok Session ID",
    }
    await query.message.reply_text(
        f"Envie agora o valor para: *{names.get(field, field)}*.\n(Ou /cancelar)",
        parse_mode="Markdown"
    )
    return WAITING_API_VALUE

async def save_api_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        f"✅ *{field.upper()}* salvo com sucesso!\nDigite /start para voltar ao menu.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operação cancelada. Digite /start para o menu.")
    return ConversationHandler.END

def main():
    cfg = load_config()
    token = cfg.get("bot_token")
    if not token:
        print("ERRO: bot_token não configurado.")
        return

    app = ApplicationBuilder().token(token).build()

    # Handler unificado para geração de vídeo e preenchimento de APIs
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(prompt_product_input, pattern="^menu_generate$"),
            CallbackQueryHandler(ask_api_input, pattern="^set_(gemini|pexels|yt|tiktok)$")
        ],
        states={
            WAITING_API_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_api_input)],
            WAITING_PRODUCT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_product_input)],
        },
        fallbacks=[CommandHandler("cancelar", cancel_cmd)],
    )

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu_(apis|social|status|main)$"))

    print("Bot rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
