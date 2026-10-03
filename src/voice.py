import base64
from google import genai

from .common import env, OUTPUT

def generate_voice(script, style):
    client = genai.Client(
        api_key=env("GEMINI_API_KEY", required=True)
    )

    interaction = client.interactions.create(
        model=env(
            "GEMINI_TTS_MODEL",
            "gemini-3.8-flash-lite-tts",
        ),
        input=[{
            "type": "user_input",
            "content": [{
                "type": "text",
                "text": script,
                "annotations": [{
                    "type": "speech_metadata",
                    "style": style,
                }],
            }],
        }],
        response_format={
            "type": "audio",
            "mime_type": "audio/wav",
            "sample_rate": 24000,
        },
        generation_config={
            "speech_config": [{
                "voice": env("TTS_VOICE", "Kore")
            }]
        },
    )

    data = base64.b64decode(
        interaction.output_audio.data
    )

    output = OUTPUT / "voice.wav"
    output.write_bytes(data)
    return output
