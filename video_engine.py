import asyncio
import json
import os
import re
import random
import subprocess
import urllib.parse
import requests

VOICE_MAPPING = {
    "en": "en-US-ChristopherNeural",
    "pt": "pt-BR-AntonioNeural",
    "es": "es-MX-JorgeNeural",
}

LANG_NAMES = {
    "en": "English",
    "pt": "Portuguese (Brazil)",
    "es": "Spanish",
}


def resolve_url(url: str) -> str:
    """Resolve URLs encurtadas (ex: amzn.to) para obter a URL final com o nome do produto."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
        return res.url
    except Exception:
        return url


def extract_url(text: str) -> str:
    """Extrai uma URL (se houver) do texto de entrada."""
    match = re.search(r"https?://[^\s]+", text)
    return match.group(0) if match else ""


def extract_product_keywords(text_or_url: str) -> str:
    """Extrai um nome amigável do produto a partir de um link ou texto."""
    url = extract_url(text_or_url)
    if url:
        final_url = resolve_url(url)
        clean_text = re.sub(r"https?://[^/]+/", "", final_url)
        clean_text = re.sub(r"[?#/].*", "", clean_text)
        clean_text = clean_text.replace("-", " ").replace("_", " ")
        return clean_text if clean_text.strip() else "viral product"
    return text_or_url


async def generate_script_and_keywords(product_text: str, gemini_api_key: str, lang: str = "en") -> dict:
    """Usa a API do Gemini 3.5 Flash para gerar roteiro, palavras-chave e prompts visuais para a IA."""
    product_name = extract_product_keywords(product_text)
    target_lang = LANG_NAMES.get(lang, "English")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={gemini_api_key}"

    prompt = f"""
    You are an expert short-form video copywriter for TikTok and Instagram Reels UGC (User Generated Content) ads.
    Create a viral 30-second script in {target_lang} for this exact product: "{product_name}".

    Respond STRICTLY with a JSON object in this exact format (no markdown, no code blocks, just raw JSON):
    {{
        "hook": "Hook sentence (0-3s)",
        "script": "Full script to be read aloud (30s)",
        "keywords": ["simple_single_word1", "simple_single_word2", "simple_single_word3"],
        "visual_prompts": [
            "A happy everyday person (man or woman) in casual clothes holding and actively demonstrating this product: {product_name}, real UGC style, 8k resolution, authentic TikTok video screenshot",
            "Close up of hands of an everyday person using and showing how {product_name} works, bright natural home lighting, realistic product demonstration",
            "An excited customer (young adult) smiling while using {product_name} in a realistic lifestyle home environment, authentic UGC product review aesthetic"
        ],
        "caption": "TikTok caption with hashtags"
    }}

    IMPORTANT for "visual_prompts": Every single visual prompt MUST feature a real person (man or woman) actively holding, demonstrating, or using the "{product_name}". Never show an empty background or abstract scene.
    IMPORTANT for "keywords": Use single, common English search terms (e.g., "person", "lifestyle", "gadget", "home", "technology").
    """

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    return json.loads(raw_text)


async def generate_audio(text: str, output_path: str, voice: str = "en-US-ChristopherNeural"):
    """Gera áudio neural usando edge-tts."""
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def download_pollinations_images(visual_prompts: list, output_dir: str) -> list:
    """Gera e baixa imagens em HD 9:16 (1080x1920) gratuitamente via Pollinations.ai."""
    os.makedirs(output_dir, exist_ok=True)
    downloaded_images = []

    for idx, prompt_text in enumerate(visual_prompts):
        encoded_prompt = urllib.parse.quote(prompt_text)
        seed = random.randint(1000, 999999)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&nologo=true&seed={seed}"

        img_path = os.path.join(output_dir, f"ai_img_{idx}.jpg")
        try:
            res = requests.get(image_url, timeout=25)
            if res.status_code == 200 and len(res.content) > 5000:
                with open(img_path, "wb") as f:
                    f.write(res.content)
                downloaded_images.append(img_path)
        except Exception:
            continue

    return downloaded_images


def convert_images_to_kenburns_clips(image_paths: list, clip_duration: float, output_dir: str) -> list:
    """Converte imagens estáticas em clipes de vídeo verticais com movimento Ken Burns (Zoom/Pan 3D)."""
    os.makedirs(output_dir, exist_ok=True)
    video_clips = []

    for idx, img_path in enumerate(image_paths):
        out_clip = os.path.join(output_dir, f"kb_clip_{idx}.mp4")

        # Filtro de Zoom/Pan dinâmico no FFmpeg
        vf = (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "zoompan=z='min(zoom+0.0015,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=125:s=1080x1920:fps=25"
        )

        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            img_path,
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-t",
            str(clip_duration),
            "-pix_fmt",
            "yuv420p",
            out_clip,
        ]

        try:
            subprocess.run(ffmpeg_cmd, check=True)
            if os.path.exists(out_clip):
                video_clips.append(out_clip)
        except Exception:
            continue

    return video_clips


def download_broll_clips(keywords: list, pexels_api_key: str, output_dir: str) -> list:
    """Busca e baixa clipes de vídeo verticais no Pexels com lista de reserva em caso de falha."""
    headers = {"Authorization": pexels_api_key}
    downloaded_files = []

    os.makedirs(output_dir, exist_ok=True)
    search_queries = list(keywords) + ["gadget", "technology", "shopping", "home"]

    clip_index = 0
    for kw in search_queries:
        if len(downloaded_files) >= 3:
            break

        url = f"https://api.pexels.com/videos/search?query={kw}&orientation=portrait&per_page=3"
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                vdata = res.json()
                videos = vdata.get("videos", [])
                for v in videos:
                    video_files = v.get("video_files", [])
                    hd_file = next(
                        (f for f in video_files if f.get("width", 0) >= 720 and f.get("link", "").endswith(".mp4")),
                        None,
                    )
                    if not hd_file and video_files:
                        hd_file = video_files[0]

                    if hd_file:
                        v_url = hd_file.get("link")
                        v_path = os.path.join(output_dir, f"clip_{clip_index}.mp4")
                        v_res = requests.get(v_url, stream=True, timeout=30)
                        if v_res.status_code == 200:
                            with open(v_path, "wb") as f:
                                for chunk in v_res.iter_content(chunk_size=1024 * 1024):
                                    f.write(chunk)
                            downloaded_files.append(v_path)
                            clip_index += 1
                            if len(downloaded_files) >= 3:
                                break
        except Exception:
            continue

    return downloaded_files


def create_srt_subtitles(script_text: str, duration: float, output_srt_path: str):
    """Gera um arquivo de legenda SRT sincronizado com base no texto do roteiro."""
    words = script_text.split()
    if not words:
        return

    chunk_size = 4
    chunks = [" ".join(words[i : i + chunk_size]) for i in range(0, len(words), chunk_size)]
    time_per_chunk = duration / max(len(chunks), 1)

    def format_time(seconds: float) -> str:
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

    with open(output_srt_path, "w", encoding="utf-8") as f:
        for idx, chunk in enumerate(chunks, 1):
            start_t = format_time((idx - 1) * time_per_chunk)
            end_t = format_time(idx * time_per_chunk)
            f.write(f"{idx}\n{start_t} --> {end_t}\n{chunk}\n\n")


def render_final_video(audio_path: str, video_clips: list, output_mp4: str, srt_path: str = None) -> bool:
    """Usa o FFmpeg para unir os clipes no formato 9:16 (1080x1920) e sincronizar o áudio com legendas."""
    if not video_clips:
        return False

    duration_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    audio_duration = float(subprocess.check_output(duration_cmd).decode().strip())

    work_dir = os.path.dirname(output_mp4)
    concat_list_path = os.path.join(work_dir, "concat.txt")
    with open(concat_list_path, "w") as f:
        for clip in video_clips:
            f.write(f"file '{os.path.abspath(clip)}'\n")

    vf_filter = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"

    if srt_path and os.path.exists(srt_path):
        clean_srt_name = os.path.basename(srt_path)
        vf_filter += f",subtitles={clean_srt_name}:force_style='FontSize=22,PrimaryColour=&H00FFFF,OutlineColour=&H000000,BorderStyle=1,Outline=2,Alignment=2,MarginV=140'"

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        concat_list_path,
        "-i",
        audio_path,
        "-vf",
        vf_filter,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-t",
        str(audio_duration),
        "-shortest",
        output_mp4,
    ]

    subprocess.run(ffmpeg_cmd, check=True, cwd=work_dir)
    return os.path.exists(output_mp4)


async def create_video_pipeline(product_text: str, config: dict, work_dir: str = "/tmp/video_work"):
    """Orquestra o pipeline completo de geração de vídeo com Pollinations.ai."""
    os.makedirs(work_dir, exist_ok=True)

    gemini_key = config.get("gemini_api_key")
    pexels_key = config.get("pexels_api_key")
    lang = config.get("language", "en")

    if not gemini_key:
        raise ValueError("Chave da Gemini API é obrigatória em /start -> Configurar APIs.")

    affiliate_url = extract_url(product_text)

    # 1. Roteiro, palavras-chave e prompts visuais da IA
    script_data = await generate_script_and_keywords(product_text, gemini_key, lang=lang)

    # 2. Gera áudio
    audio_path = os.path.join(work_dir, "narration.mp3")
    voice = VOICE_MAPPING.get(lang, "en-US-ChristopherNeural")
    await generate_audio(script_data["script"], audio_path, voice=voice)

    # 3. Mede duração para legendas e animação
    duration_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    audio_duration = float(subprocess.check_output(duration_cmd).decode().strip())

    # 4. Gera legendas SRT
    srt_path = os.path.join(work_dir, "subtitles.srt")
    create_srt_subtitles(script_data["script"], audio_duration, srt_path)

    # 5. Tenta gerar visuais com IA Pollinations.ai
    video_clips = []
    visual_prompts = script_data.get("visual_prompts", [])

    if visual_prompts:
        img_dir = os.path.join(work_dir, "ai_images")
        ai_images = download_pollinations_images(visual_prompts, img_dir)
        if ai_images:
            clip_dur = audio_duration / len(ai_images)
            kb_dir = os.path.join(work_dir, "kb_clips")
            video_clips = convert_images_to_kenburns_clips(ai_images, clip_dur, kb_dir)

    # Fallback para Pexels se Pollinations falhar
    if not video_clips and pexels_key:
        clips_dir = os.path.join(work_dir, "clips")
        video_clips = download_broll_clips(script_data.get("keywords", []), pexels_key, clips_dir)

    if not video_clips:
        raise RuntimeError("Não foi possível gerar visuais com a IA nem baixar clipes de apoio.")

    # 6. Renderiza vídeo
    output_mp4 = os.path.join(work_dir, "final_render.mp4")
    success = render_final_video(audio_path, video_clips, output_mp4, srt_path=srt_path)

    if not success:
        raise RuntimeError("Falha ao renderizar com o FFmpeg.")

    # 7. Formata legenda com link de afiliado se houver
    caption_text = script_data.get("caption", "")
    if affiliate_url:
        link_label = "🛒 Buy here:" if lang == "en" else "🛒 Compre aqui:"
        caption_text = f"{caption_text}\n\n{link_label} {affiliate_url}"

    return {
        "video_path": output_mp4,
        "caption": caption_text,
        "script": script_data.get("script", ""),
        "affiliate_url": affiliate_url,
    }
