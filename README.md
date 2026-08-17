# 🚀 DropShipping Auto Video Generator Bot

Sistema 100% automatizado e autônomo para geração de vídeos curtos (TikTok, Reels, Shorts) e vendas para Dropshipping Global. Desenvolvido para rodar 24/7 em servidores de baixo custo (incluindo instâncias gratuitas **Ubuntu ARM64/x86_64**) e controlado inteiramente pelo seu smartphone via **Telegram**.

---

## ⚡ Principais Funcionalidades

- **Controle Total via Telegram:** Configure chaves de API, conecte perfis de redes sociais e solicite novos vídeos sem tocar no terminal.
- **Roteiros & Copywriting com IA:** Integração com LLMs (Google Gemini / Groq) para criar roteiros virais em inglês voltados ao público americano.
- **Voz Neural Ultra-Realista:** Síntese de voz com `edge-tts` (Microsoft Neural Voices) — zero custos de API de áudio.
- **Renderização Automatizada:** Pipeline com FFmpeg e legendas dinâmicas em formato 9:16 (1080x1920) otimizado para ARM64.
- **Gerenciamento de Recursos:** Monitoramento em tempo real de CPU, RAM e disco diretamente pelo bot.
- **Instalador One-Line:** Configuração completa com criação de ambiente virtual Python e serviço `systemd` em minutos.

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologia / Ferramenta |
| :--- | :--- |
| **Linguagem & Framework** | Python 3.10+ / `python-telegram-bot` v20+ |
| **Renderização & Áudio** | FFmpeg / `edge-tts` |
| **Banco de Mídia B-Roll** | Pexels API |
| **LLM & Copywriting** | Google Gemini API / Groq API |
| **Sistema & Deploy** | Ubuntu Linux (ARM64 / x86_64) + `systemd` |

---

## 📦 Instalação Rápida (One-Line)

Para instalar o bot em qualquer servidor Ubuntu recém-criado (ou PC local), execute o comando abaixo no terminal:

```bash
curl -sSL [https://raw.githubusercontent.com/ferttopooli1/drop-shipping-bot/main/install.sh](https://raw.githubusercontent.com/ferttopooli1/drop-shipping-bot/main/install.sh) | bash
