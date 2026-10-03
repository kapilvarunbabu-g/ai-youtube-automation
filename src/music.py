import numpy as np
import wave

from .common import OUTPUT

def make_music(seconds, sample_rate=24000):
    t = np.arange(
        int(seconds * sample_rate)
    ) / sample_rate

    beat = 60 / 98
    audio = np.zeros_like(t, dtype=np.float64)

    for i, frequency in enumerate(
        [146.83, 174.61, 220.00, 293.66]
    ):
        tremolo = (
            0.06
            + 0.04 * np.sin(
                2 * np.pi * 0.08 * t + i
            )
        )
        audio += tremolo * np.sin(
            2 * np.pi * frequency * t
        )

    pulse = (
        np.sin(
            2 * np.pi * t / beat
        ) > 0.95
    ).astype(float)

    audio += (
        0.04
        * pulse
        * np.sin(
            2 * np.pi * 90 * t
        )
    )

    fade = (
        np.clip(t / 1.5, 0, 1)
        * np.clip(
            (seconds - t) / 1.5,
            0,
            1,
        )
    )

    audio *= fade
    audio /= max(1e-9, np.max(np.abs(audio)))
    audio *= 0.06

    stereo = np.stack(
        [audio, audio],
        axis=1,
    )

    pcm = np.clip(
        stereo * 32767,
        -32768,
        32767,
    ).astype(np.int16)

    output = OUTPUT / "music.wav"

    with wave.open(str(output), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())

    return output
