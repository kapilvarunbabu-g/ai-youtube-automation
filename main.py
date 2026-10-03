from src.research import build_research_pack
from src.editor import choose_and_write_story
from src.sheet import update_workbook
from src.voice import generate_voice
from src.render import render_short
from src.upload import upload_video
import json
from pathlib import Path

def main():
    pack = build_research_pack()
    story = choose_and_write_story(pack)

    update_workbook(
        research_rows=pack["candidates"],
        selected_story=story,
        published=None,
    )

    voice_path = generate_voice(
        story["script"],
        story.get("voice_style", "natural, energetic, conversational"),
    )

video_id, url = upload_video(story, video_path)

published = {
    "video_id": video_id,
    "url": url,
    "title": story["title"]
}

Path("output").mkdir(parents=True, exist_ok=True)

Path("output/published.json").write_text(
    json.dumps(published, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

update_workbook(
    research_rows=[],
    selected_story=story,
    published={"video_id": video_id, "url": url}
)

print("Published:", url)
if __name__ == "__main__":
    main()
