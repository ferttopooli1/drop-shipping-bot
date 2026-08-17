import asyncio
from config_manager import load_config, update_config_key
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

# Estados de conversação para cadastro de configs
WAITING_API_VALUE = 1


def is_admin(user_id: int) -> bool:
  cfg = load_config()
  return str(user_id) == str(cfg.get("admin_id"))


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = update.effective_user.id
  if not is_admin(user_id):
    await update.message.reply_text(
        "⛔ Acesso não autorizado. Este bot é privado."
    )
    return

  keyboard = [
      [
          InlineKeyboardButton("⚙️ Configurar APIs", callback_data="menu_apis"),
          InlineKeyboardButton(
              "📱 Redes Sociais", callback_data="menu_social"
          ),
      ],
      [
          InlineKeyboardButton(
              "🎬 Gerar Vídeo", callback_data="menu_generate"
          ),
          InlineKeyboardButton("📊 Status da VM", callback_data="menu_status"),
      ],
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)
  await update.message.reply_text(
      "🚀 *Painel de Controle - Auto Video Bot*\n\nSelecione uma opção abaixo:",
      reply_markup=reply_markup,
      parse_mode="Markdown",
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
        [
            InlineKeyboardButton(
                f"Gemini API ({gemini_status})", callback_data="set_gemini"
            )
        ],
        [
            InlineKeyboardButton(
                f"Pexels API ({pexels_status})", callback_data="set_pexels"
            )
        ],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="menu_main")],
    ]
    await query.edit_message_text(
        "🔑 *Configuração de Chaves de API*\n\nClique para alterar ou definir:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

  elif data == "menu_social":
    yt_status = (
        "✅ Conectado"
        if cfg.get("social_accounts", {}).get("youtube_channel_id")
        else "❌ Não configurado"
    )
    tt_status = (
        "✅ Conectado"
        if cfg.get("social_accounts", {}).get("tiktok_session_id")
        else "❌ Não configurado"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                f"YouTube Shorts ({yt_status})", callback_data="set_yt"
            )
        ],
        [
            InlineKeyboardButton(
                f"TikTok ({tt_status})", callback_data="set_tiktok"
            )
        ],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="menu_main")],
    ]
    await query.edit_message_text(
        "📱 *Perfis de Postagem*\n\nConfigure onde os vídeos serão postados:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
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
        parse_mode="Markdown",
    )

  elif data == "menu_main":
    keyboard = [
        [
            InlineKeyboardButton("⚙️ Configurar APIs", callback_data="menu_apis"),
            InlineKeyboardButton(
                "📱 Redes Sociais", callback_data="menu_social"
            ),
        ],
        [
            InlineKeyboardButton(
                "🎬 Gerar Vídeo", callback_data="menu_generate"
            ),
            InlineKeyboardButton("📊 Status da VM", callback_data="menu_status"),
        ],
    ]
    await query.edit_message_text(
        "🚀 *Painel de Controle - Auto Video Bot*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# Fluxo para receber o input de texto do usuário
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
      f"Envie agora o valor para: *{names.get(field, field)}*.\n(Ou envie /cancelar para desistir)",
      parse_mode="Markdown",
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

  # Apaga a mensagem enviada pelo usuário por segurança (esconder a chave de API no chat)
  try:
    await update.message.delete()
  except Exception:
    pass

  await update.message.reply_text(
      f"✅ *{field.upper()}* salvo com sucesso!\nDigite /start para voltar ao menu principal.",
      parse_mode="Markdown",
  )
  return ConversationHandler.END


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "Operação cancelada. Digite /start para o menu."
  )
  return ConversationHandler.END


def main():
  cfg = load_config()
  token = cfg.get("bot_token")
  if not token:
    print("ERRO: bot_token não configurado em config.json")
    return

  app = ApplicationBuilder().token(token).build()

  conv_handler = ConversationHandler(
      entry_points=[
          CallbackQueryHandler(ask_api_input, pattern="^set_(gemini|pexels|yt|tiktok)$")
      ],
      states={
          WAITING_API_VALUE: [
              MessageHandler(filters.TEXT & ~filters.COMMAND, save_api_input)
          ]
      },
      fallbacks=[CommandHandler("cancelar", cancel_cmd)],
  )

  app.add_handler(CommandHandler("start", start_cmd))
  app.add_handler(conv_handler)
  app.add_handler(
      CallbackQueryHandler(menu_callback, pattern="^menu_(apis|social|status|main)$")
  )

  print("Bot em execução...")
  app.run_polling()


if __name__ == "__main__":
  main()
