from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from moviepy import VideoFileClip
from PIL import Image
import requests
import os
import uuid
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

app = Flask(__name__)


def baixar_video(url, destino):
    resposta = requests.get(url)
    with open(destino, "wb") as f:
        f.write(resposta.content)


def converter_para_figurinha(video_path, saida_path):
    """
    Converte vídeo em figurinha (webp) seguindo as regras do WhatsApp:
    - Duração máxima: 8 segundos (vamos cortar pra 6 por segurança)
    - Tamanho: 512x512
    """
    clip = VideoFileClip(video_path)

    # corta pra no máximo 6 segundos
    if clip.duration > 6:
        clip = clip.subclip(0, 6)

    # redimensiona mantendo proporção e centralizando em 512x512
    clip_resized = clip.resized(height=512) if clip.h < clip.w else clip.resized(width=512)

    # exporta como frames e monta o webp animado
    frames = []
    for frame in clip_resized.iter_frames(fps=10):
        img = Image.fromarray(frame)
        # centraliza em um quadro 512x512
        fundo = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        pos_x = (512 - img.width) // 2
        pos_y = (512 - img.height) // 2
        fundo.paste(img, (pos_x, pos_y))
        frames.append(fundo)

    frames[0].save(
        saida_path,
        format="WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=100,  # ms por frame
        loop=0,
    )

    clip.close()
    clip_resized.close()


@app.route("/webhook", methods=["POST"])
def webhook():
    media_url = request.form.get("MediaUrl0")
    resp = MessagingResponse()

    if media_url:
        try:
            id_unico = str(uuid.uuid4())
            video_path = f"/tmp/{id_unico}.mp4"
            sticker_path = f"/tmp/{id_unico}.webp"

            baixar_video(media_url, video_path)
            converter_para_figurinha(video_path, sticker_path)

            # sobe a figurinha pro Cloudinary e pega a URL pública
            upload_resultado = cloudinary.uploader.upload(
                sticker_path,
                resource_type="image",
                format="webp"
            )
            url_figurinha = upload_resultado["secure_url"]

            resp.message("Aqui está sua figurinha! 🎉").media(url_figurinha)

            os.remove(video_path)
            os.remove(sticker_path)

        except Exception as e:
            resp.message(f"Deu erro ao converter: {str(e)}")
    else:
        resp.message(
            "Oi! Me manda um vídeo curtinho (até 6 segundos) que eu transformo em figurinha 🎬➡️🎨"
        )

    return str(resp)


@app.route("/", methods=["GET"])
def home():
    return "Bot de figurinhas rodando! 🚀"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
