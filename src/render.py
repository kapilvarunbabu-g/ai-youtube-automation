from pathlib import Path
import subprocess
import textwrap

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .common import OUTPUT
from .music import make_music

W, H = 1080, 1920

def get_font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def make_scene(scene, index, total):
    image = Image.new("RGB", (W, H), (7, 11, 25))
    draw = ImageDraw.Draw(image)

    accents = [
        (64, 190, 255),
        (130, 105, 255),
        (0, 220, 165),
        (255, 170, 70),
    ]
    accent = accents[index % len(accents)]

    # Background
    for y in range(H):
        k = y / H
        draw.line(
            [(0, y), (W, y)],
            fill=(
                int(7 + 13 * k),
                int(11 + 12 * (1 - k)),
                int(25 + 28 * k)
            )
        )

    # Soft glow
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    ImageDraw.Draw(glow).ellipse(
        (
            W * 0.15 + index * 20,
            0,
            W * 1.05,
            H * 0.55
        ),
        fill=(*accent, 65)
    )

    glow = glow.filter(ImageFilter.GaussianBlur(100))

    image = Image.alpha_composite(
        image.convert("RGBA"),
        glow
    ).convert("RGB")

    draw = ImageDraw.Draw(image)

    # Fonts
    small = get_font(30)
    title = get_font(68, True)
    footer = get_font(27)

    # Header
    draw.text(
        (64, 55),
        f"AI TECH DAILY • తెలుగు  {index + 1:02d}/{total:02d}",
        font=small,
        fill=(215, 226, 242)
    )

    # Progress bar
    progress = 940 * ((index + 1) / total)

    draw.rounded_rectangle(
        (64, 115, 1004, 133),
        9,
        fill=(45, 55, 78)
    )

    draw.rounded_rectangle(
        (64, 115, 64 + progress, 133),
        9,
        fill=accent
    )

    # Main headline only
    headline = str(
        scene.get(
            "on_screen_text",
            "ఇది ఎందుకు ముఖ్యమంటే?"
        )
    ).strip()

    headline = textwrap.fill(
        headline,
        width=17
    )

    draw.multiline_text(
        (64, 220),
        headline,
        font=title,
        fill="white",
        spacing=10,
        stroke_width=2,
        stroke_fill=(8, 12, 25)
    )

    # Main visual panel
    panel = (65, 700, 1015, 1450)

    draw.rounded_rectangle(
        panel,
        38,
        fill=(11, 19, 38),
        outline=accent,
        width=4
    )

    # Clean abstract technology visual
    center_x = 540
    center_y = 1070

    # Central AI chip
    draw.rounded_rectangle(
        (
            center_x - 190,
            center_y - 160,
            center_x + 190,
            center_y + 160
        ),
        40,
        fill=(16, 28, 55),
        outline=accent,
        width=6
    )

    # Connection lines
    for y in range(center_y - 110, center_y + 111, 55):
        draw.line(
            (
                center_x - 250,
                y,
                center_x - 190,
                y
            ),
            fill=accent,
            width=8
        )

        draw.line(
            (
                center_x + 190,
                y,
                center_x + 250,
                y
            ),
            fill=accent,
            width=8
        )

    # AI label
    draw.text(
        (
            center_x - 75,
            center_y - 80
        ),
        "AI",
        font=get_font(120, True),
        fill="white"
    )

    # Small visual indicators
    for i in range(5):
        x = 180 + i * 180

        draw.ellipse(
            (
                x - 18,
                1280,
                x + 18,
                1316
            ),
            fill=accent
        )

    # Footer
    draw.text(
        (64, 1775),
        "Original commentary • Sources in description",
        font=footer,
        fill=(165, 180, 205)
    )

    output = OUTPUT / f"scene_{index:02d}.png"

    image.save(output)

    return output

def probe_duration(path):
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], capture_output=True, text=True, check=True)
    return float(result.stdout.strip())

def ass_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:05.2f}"

def escape_ass(text):
    return str(text).replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")

def render_short(story, voice_path):
    duration = probe_duration(voice_path)
    music = make_music(max(60, int(duration) + 3))
    scenes = story.get("scenes", [])
    if len(scenes) < 8:
        raise RuntimeError("The editor must provide 8 scenes.")
    scenes = scenes[:8]
    images = [make_scene(scene, i, len(scenes)) for i, scene in enumerate(scenes)]
    each = duration / len(images)

    concat = OUTPUT / "concat.txt"
    with concat.open("w", encoding="utf-8") as f:
        for i, image in enumerate(images):
            f.write(f"file '{image.as_posix()}'\n")
            if i < len(images) - 1:
                f.write(f"duration {each:.3f}\n")
        f.write(f"file '{images[-1].as_posix()}'\n")

    ass = OUTPUT / "captions.ass"
    with ass.open("w", encoding="utf-8") as f:
        f.write(
            "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Alignment, MarginL, MarginR, MarginV, Encoding\n"
           Style: Default,Noto Sans Telugu,52,&H00FFFFFF,&H00FFFFFF,&H00101010,&H90101010,-1,0,2,80,80,150,1
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )
        for i, scene in enumerate(scenes):
            start, end = i * each, min(duration, (i + 1) * each)
            caption = escape_ass(scene.get("caption", scene.get("on_screen_text", "")))
            f.write(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{caption}\n")

    subtitle_path = ass.as_posix().replace(":", r"\:")
    output = OUTPUT / "video.mp4"
    command = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat),
        "-i", str(voice_path), "-i", str(music),
        "-filter_complex",
        f"[0:v]scale=1080:1920,zoompan=z='min(zoom+0.0008,1.025)':d=1:s=1080x1920:fps=30,format=yuv420p,subtitles={subtitle_path}[v];"
        f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[voice];"
        f"[2:a]volume=0.16,atrim=0:{duration}[bg];"
        "[voice][bg]amix=inputs=2:duration=first:dropout_transition=2[a]",
        "-map", "[v]", "-map", "[a]", "-t", str(duration), "-r", "30",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output),
    ]
    subprocess.run(command, check=True)
    return output
