"""Gera vídeos verticais 1080x1920 a partir de roteiros.py.
Uso: python3 -I gerar_videos.py <pasta_saida>
"""
import os, sys, re, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFont
from roteiros import VIDEOS

W, H, FPS = 1080, 1920, 30
BG = (11, 52, 64)          # #0B3440
BG2 = (7, 38, 48)          # #072630
ORANGE = (242, 138, 46)    # #F28A2E
LIGHT = (220, 235, 231)    # #DCEBE7
WHITE = (255, 255, 255)
FD = "/usr/share/fonts/opentype/inter/"
SLIDE_S, CTA_S, ANIM_S = 3.2, 4.5, 0.45


def font(name, size):
    return ImageFont.truetype(FD + name, size)


def tokens(text):
    out = []
    for part in re.split(r"(\*[^*]+\*)", text):
        if not part:
            continue
        hi = part.startswith("*")
        for w in part.strip("*").split():
            out.append((w, hi))
    return out


def wrap(toks, f, maxw):
    lines, cur = [], []
    sp = f.getlength(" ")
    for w, hi in toks:
        test = cur + [(w, hi)]
        width = sum(f.getlength(t) for t, _ in test) + sp * (len(test) - 1)
        if cur and width > maxw:
            lines.append(cur)
            cur = [(w, hi)]
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def text_layer(text):
    toks = tokens(text)
    for size in (104, 96, 88, 80, 72):
        f = font("InterDisplay-ExtraBold.otf", size)
        lines = wrap(toks, f, W - 180)
        if len(lines) <= 6:
            break
    lh = int(size * 1.22)
    layer = Image.new("RGBA", (W, lh * len(lines) + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    sp = f.getlength(" ")
    for i, line in enumerate(lines):
        x = 90
        for w, hi in line:
            d.text((x, i * lh), w, font=f, fill=ORANGE if hi else WHITE)
            x += f.getlength(w) + sp
    return layer


def cta_layer():
    layer = Image.new("RGBA", (W, 900), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((70, 0, W - 70, 900), radius=48, fill=LIGHT)
    f1 = font("InterDisplay-ExtraBold.otf", 84)
    f2 = font("Inter-SemiBold.otf", 50)
    f3 = font("InterDisplay-Black.otf", 120)
    y = 70
    for line in ["Kit Sair das", "Dívidas em 90 Dias"]:
        d.text((130, y), line, font=f1, fill=BG)
        y += 104
    y += 30
    d.text((130, y), "R$ 47", font=f3, fill=ORANGE)
    y += 160
    d.text((130, y), "E-book + planilha automática", font=f2, fill=BG)
    y += 68
    d.text((130, y), "7 dias de garantia (Hotmart)", font=f2, fill=BG)
    y += 120
    d.rounded_rectangle((130, y, W - 130, y + 120), radius=60, fill=ORANGE)
    f4 = font("InterDisplay-ExtraBold.otf", 58)
    t = "LINK NA BIO"
    d.text(((W - f4.getlength(t)) / 2, y + 26), t, font=f4, fill=WHITE)
    return layer


def base_frame():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.ellipse((W - 420, -300, W + 300, 420), fill=BG2)
    d.ellipse((-360, H - 380, 360, H + 340), fill=BG2)
    d.text((90, 150), "BOLSO EM DIA", font=font("Inter-Bold.otf", 44), fill=ORANGE)
    d.rectangle((90, 215, 190, 223), fill=ORANGE)
    return img


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def render(video, out_path):
    base = base_frame()
    scenes = [(text_layer(s), SLIDE_S) for s in video["slides"]] + [(cta_layer(), CTA_S)]
    total = sum(d for _, d in scenes)
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
           "-shortest", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out_path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    elapsed = 0.0
    for layer, dur in scenes:
        n = int(dur * FPS)
        cy = (H - layer.height) // 2 + 40
        for i in range(n):
            t = i / FPS
            a = ease(t / ANIM_S)
            fr = base.copy()
            lay = layer
            if a < 1:
                lay = layer.copy()
                lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
            fr.paste(lay, (0, int(cy + (1 - a) * 80)), lay)
            prog = (elapsed + t) / total
            ImageDraw.Draw(fr).rectangle((0, H - 18, int(W * prog), H), fill=ORANGE)
            p.stdin.write(fr.tobytes())
        elapsed += dur
    p.stdin.close()
    p.wait()
    # thumbnail
    return total


if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for v in VIDEOS:
        path = os.path.join(out, v["slug"] + ".mp4")
        dur = render(v, path)
        print(v["slug"], f"{dur:.1f}s", os.path.getsize(path) // 1024, "KB")
