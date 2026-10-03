from pathlib import Path
import re
import subprocess
import textwrap

from PIL import Image, ImageDraw, ImageFont

from .common import OUTPUT
from .music import make_music
from .stock_video import search_and_download

W, H = 1080, 1920


def get_font(size, bold=False):
    candidates = [
        (
            "/usr/share/fonts/opentype/noto/"
            "NotoSansTelugu-Bold.ttf"
            if bold
            else
            "/usr/share/fonts/opentype/noto/"
            "NotoSansTelugu-Regular.ttf"
        ),
        (
            "/usr/share/fonts/truetype/noto/"
            "NotoSansTelugu-Bold.ttf"
            if bold
            else
            "/usr/share/fonts/truetype/noto/"
            "NotoSansTelugu-Regular.ttf"
        ),
        (
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans-Bold.ttf"
            if bold
            else
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans.ttf"
        ),
    ]

    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)

    result = subprocess.run(
        ["fc-match", "-f", "%{file}", "Noto Sans Telugu"],
        capture_output=True,
        text=True,
        check=False,
    )

    path = result.stdout.strip()

    if path and Path(path).exists():
        return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def probe_duration(path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    return float(result.stdout.strip())


def ass_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60

    return f"{hours}:{minutes:02d}:{secs:05.2f}"


def escape_ass(text):
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
    )


def split_caption_text(text, max_words=8):
    words = str(text).split()

    if len(words) <= max_words:
        return str(text).strip()

    lines = []

    for i in range(0, len(words), max_words):
        lines.append(" ".join(words[i:i + max_words]))

    return "\\N".join(lines[:3])


def subtitle_segments(script, total_duration):
    clean = " ".join(str(script).split())

    # Split according to Telugu/English sentence punctuation.
    sentences = [
        p.strip()
        for p in re.split(
            r"(?<=[.!?।])\s+",
            clean,
        )
        if p.strip()
    ]

    if not sentences:
        return [(0.0, total_duration, clean)]

    # Approximate speech timing from word count.
    # This keeps subtitles synchronized with narration much better
    # than assigning one caption to every video scene.
    weights = [
        max(1, len(sentence.split()))
        for sentence in sentences
    ]

    total_weight = sum(weights)

    segments = []
    cursor = 0.0

    for index, (sentence, weight) in enumerate(
        zip(sentences, weights)
    ):
        if index == len(sentences) - 1:
            end = total_duration
        else:
            duration = (
                total_duration
                * weight
                / total_weight
            )

            end = min(
                total_duration,
                cursor + duration,
            )

        segments.append(
            (
                cursor,
                end,
                split_caption_text(sentence),
            )
        )

        cursor = end

    return segments


def render_stock_clip(
    input_path,
    output_path,
    seconds,
):
    # Convert any landscape/portrait stock footage
    # into a vertical 9:16 frame while preserving the
    # important central area.
    command = [
        "ffmpeg",
        "-y",
        "-stream_loop",
        "-1",
        "-i",
        str(input_path),
        "-t",
        f"{seconds:.3f}",
        "-vf",
        (
            "scale=1080:1920:"
            "force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "fps=30,"
            "format=yuv420p"
        ),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "21",
        str(output_path),
    ]

    subprocess.run(
        command,
        check=True,
    )


def get_real_stock_video(scene, topic, index):
    queries = []

    primary = scene.get("stock_search_query")

    if primary:
        queries.append(primary)

    visual = scene.get("visual_concept")

    if visual:
        queries.append(visual)
    if topic:
          queries.append(
            f"{primary or visual or topic} {topic}"
        )

# Do not fall back to unrelated generic AI footage.
# Every attempt should remain tied to the current scene.

    already_tried = set()

    for query in queries:
        query = " ".join(
            str(query).split()
        ).strip()

        if not query:
            continue

        if query.lower() in already_tried:
            continue

        already_tried.add(query.lower())

        try:
            video_path, attribution = (
                search_and_download(
                    query,
                    index,
                )
            )

            return video_path, attribution

        except Exception as exc:
            print(
                f"Stock search failed for "
                f"'{query}': {exc}"
            )

    raise RuntimeError(
        "Unable to obtain a real stock video "
        f"for scene {index + 1}."
    )


def render_short(story, voice_path):
    duration = probe_duration(
        voice_path
    )

    scenes = story.get(
        "scenes",
        [],
    )

    if len(scenes) < 8:
        raise RuntimeError(
            "The editor must provide 8 scenes."
        )

    scenes = scenes[:8]

    each_duration = (
        duration / len(scenes)
    )

    clip_paths = []
    stock_sources = []

    topic = story.get(
        "topic",
        "technology",
    )

    # Download and prepare real video footage
    # for every scene.
    for index, scene in enumerate(scenes):
        source_path, attribution = (
            get_real_stock_video(
                scene,
                topic,
                index,
            )
        )

        normalized_path = (
            OUTPUT
            / f"real_clip_{index:02d}.mp4"
        )

        render_stock_clip(
            source_path,
            normalized_path,
            each_duration,
        )

        clip_paths.append(
            normalized_path
        )

        stock_sources.append(
            attribution
        )

        print(
            f"Scene {index + 1}/"
            f"{len(scenes)} ready."
        )

    # Combine all real video clips.
    concat = OUTPUT / "concat.txt"

    with concat.open(
        "w",
        encoding="utf-8",
    ) as file:
        for clip in clip_paths:
            file.write(
                f"file '{clip.as_posix()}'\n"
            )

    # Create speech-timed Telugu subtitles.
    ass = OUTPUT / "captions.ass"

    with ass.open(
        "w",
        encoding="utf-8",
    ) as file:
        file.write(
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            "PlayResX: 1080\n"
            "PlayResY: 1920\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, "
            "PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, "
            "Italic, Alignment, MarginL, MarginR, "
            "MarginV, Encoding\n"
            "Style: Telugu,Noto Sans Telugu,60,"
            "&H00FFFFFF,&H00FFFFFF,&H00000000,"
            "&H30000000,-1,0,8,70,70,250,1\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, "
            "Name, MarginL, MarginR, MarginV, "
            "Effect, Text\n"
        )

        segments = subtitle_segments(
            story.get(
                "script",
                "",
            ),
            duration,
        )

        for start, end, caption in segments:
            file.write(
                "Dialogue: 0,"
                f"{ass_time(start)},"
                f"{ass_time(end)},"
                "Telugu,,0,0,0,,"
                "{\\q2\\bord3\\shad1}"
                f"{escape_ass(caption)}\n"
            )

    subtitle_path = (
        ass.as_posix()
        .replace(":", r"\:")
    )

    music = make_music(
        max(
            60,
            int(duration) + 3,
        )
    )

    output = (
        OUTPUT
        / "video.mp4"
    )

    # Video + Telugu subtitles + voice + music.
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat),
        "-i",
        str(voice_path),
        "-i",
        str(music),
        "-filter_complex",
        (
            f"[0:v]"
            f"subtitles={subtitle_path}"
            f"[v];"
            f"[1:a]"
            f"loudnorm="
            f"I=-16:TP=-1.5:LRA=11"
            f"[voice];"
            f"[2:a]"
            f"volume=0.08,"
            f"atrim=0:{duration}"
            f"[bg];"
            f"[voice][bg]"
            f"amix=inputs=2:"
            f"duration=first:"
            f"dropout_transition=2"
            f"[a]"
        ),
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-t",
        f"{duration:.3f}",
        "-r",
        "30",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-movflags",
        "+faststart",
        str(output),
    ]

    subprocess.run(
        command,
        check=True,
    )

    # Keep footage credits for YouTube description.
    story["stock_sources"] = (
        stock_sources
    )

    return output
