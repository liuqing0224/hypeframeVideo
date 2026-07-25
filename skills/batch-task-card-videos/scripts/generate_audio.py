#!/usr/bin/env python3
import argparse
import asyncio
import json
import math
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np


RATE = 48000
INTRO_PAD = 0.45
TOTAL_PAD = 1.2


def write_wav(path: Path, samples: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(samples * 32767, -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(pcm.tobytes())


def probe(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    stream = payload["streams"][0]
    return {
        "path": path.as_posix(),
        "codec": stream.get("codec_name"),
        "sampleRate": int(stream.get("sample_rate", 0)),
        "channels": int(stream.get("channels", 0)),
        "duration": float(payload["format"].get("duration", 0)),
    }


async def edge_segment(text: str, config: dict, target: Path) -> list[dict]:
    try:
        import edge_tts
    except ImportError as error:
        raise RuntimeError("edge-tts is required for provider=edge") from error
    communicate = edge_tts.Communicate(
        text,
        config["voice"],
        rate=config.get("rate", "-4%"),
        pitch=config.get("pitch", "+0Hz"),
        boundary="WordBoundary",
    )
    words = []
    with target.open("wb") as output:
        async for event in communicate.stream():
            if event["type"] == "audio":
                output.write(event["data"])
            elif event["type"] == "WordBoundary":
                words.append(
                    {
                        "text": event["text"],
                        "start": event["offset"] / 10_000_000,
                        "duration": event["duration"] / 10_000_000,
                    }
                )
    return words


def silent_segment(text: str, target: Path) -> list[dict]:
    duration = max(2.8, len(text) / 5.2)
    write_wav(target, np.zeros(round(duration * RATE), dtype=np.float64))
    return [{"text": text, "start": 0.0, "duration": duration}]


def f5_segment(text: str, config: dict, production: Path, target: Path, temp: Path) -> list[dict]:
    command = config.get("f5_command")
    reference = production / config.get("reference_audio", "")
    if not isinstance(command, list) or not command or not reference.is_file():
        raise ValueError("provider=f5 requires f5_command and an existing authorized reference_audio")
    text_file = temp / f"{target.stem}.txt"
    text_file.write_text(text, encoding="utf-8")
    replacements = {
        "{text_file}": str(text_file),
        "{reference_audio}": str(reference),
        "{output}": str(target),
    }
    subprocess.run([replacements.get(part, part) for part in command], check=True)
    if not target.is_file():
        raise FileNotFoundError(target)
    duration = probe(target)["duration"]
    return [{"text": text, "start": 0.0, "duration": duration}]


def quantized_scene_duration(raw_duration: float) -> float:
    return math.ceil(max(4.0, raw_duration + TOTAL_PAD) * 2) / 2


def normalize_with_padding(source: Path, target: Path, duration: float) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    delay_ms = round(INTRO_PAD * 1000)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(source),
            "-af",
            f"adelay={delay_ms},apad=pad_dur={duration},atrim=0:{duration}",
            "-ar",
            str(RATE),
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(target),
        ],
        check=True,
    )


def concat_wavs(sources: list[Path], target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(target), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(RATE)
        for source in sources:
            with wave.open(str(source), "rb") as segment:
                if (
                    segment.getnchannels() != 1
                    or segment.getsampwidth() != 2
                    or segment.getframerate() != RATE
                ):
                    raise ValueError(f"incompatible segment: {source}")
                output.writeframes(segment.readframes(segment.getnframes()))


def make_music(path: Path, seconds: float, style_key: str) -> None:
    note_sets = {
        "science": [220.0, 277.18, 329.63, 440.0, 369.99, 277.18],
        "fantasy": [196.0, 246.94, 293.66, 392.0, 329.63, 246.94],
        "history": [174.61, 220.0, 261.63, 293.66, 261.63, 220.0],
        "field-trip": [220.0, 277.18, 329.63, 369.99, 329.63, 277.18],
    }
    notes = note_sets[style_key]
    count = round(seconds * RATE)
    t = np.arange(count, dtype=np.float64) / RATE
    music = np.zeros(count, dtype=np.float64)
    step = 1.45 if style_key in {"science", "field-trip"} else 1.75
    index = 0
    while index * step < seconds:
        freq = notes[index % len(notes)]
        start = round(index * step * RATE)
        size = min(round(2.8 * RATE), count - start)
        local = np.arange(size, dtype=np.float64) / RATE
        pluck = (
            np.sin(2 * np.pi * freq * local)
            + 0.28 * np.sin(4 * np.pi * freq * local)
            + 0.12 * np.sin(6 * np.pi * freq * local)
        ) * np.exp(-local * 1.25)
        music[start : start + size] += pluck * 0.085
        index += 1
    bass = 55.0 if style_key == "science" else 65.4
    music += np.sin(2 * np.pi * bass * t) * 0.012
    write_wav(path, music)


def make_sfx(audio_dir: Path) -> dict[str, Path]:
    impact = audio_dir / "sfx-impact.wav"
    whoosh = audio_dir / "sfx-whoosh.wav"
    chime = audio_dir / "sfx-chime.wav"
    t = np.arange(round(1.0 * RATE), dtype=np.float64) / RATE
    impact_samples = (
        np.sin(2 * np.pi * 70 * t) * 0.42 + np.sin(2 * np.pi * 140 * t) * 0.14
    ) * np.exp(-t * 3.0)
    write_wav(impact, impact_samples)
    rng = np.random.default_rng(17)
    noise = rng.normal(0, 1, len(t))
    envelope = np.sin(np.pi * np.clip(t / 0.9, 0, 1)) ** 2
    write_wav(whoosh, noise * envelope * 0.065)
    chime_samples = (
        np.sin(2 * np.pi * 523.25 * t) + 0.45 * np.sin(2 * np.pi * 783.99 * t)
    ) * np.exp(-t * 2.5) * 0.16
    write_wav(chime, chime_samples)
    return {"impact": impact, "whoosh": whoosh, "chime": chime}


def write_storyboard(production: Path, plan: dict, scenes: list[dict]) -> None:
    timed = {scene["id"]: scene for scene in scenes}
    meta = plan["metadata"]
    rows = [
        "---",
        "format: 1920x1080",
        f'message: "{meta["directorIntent"]}"',
        "arc: Start -> Challenge -> Resolution",
        "audience: primary-and-middle-school-students",
        "---",
        "",
    ]
    for scene in plan["scenes"]:
        timing = timed[scene["id"]]
        rows.extend(
            [
                f"## Frame {scene['index']} - {scene['title']}",
                "",
                "- status: timed",
                f"- src: compositions/{scene['id']}.html",
                f"- duration: {timing['durationSeconds']:.3f}s",
                f"- transition_in: {scene['transitionIn']}",
                f"- scene: {scene['shot']['architecture']}；{scene['shot']['primary']}",
                f"- voiceover: {scene['narration']}",
                f"- motion: {', '.join(scene['motionRules'])}",
                "- sfx: scene-impact",
                "",
                f"{scene['title']}承担故事的 {scene['beat']} 节点。主角先出现，环境和配角随后补齐纵深。",
                "",
            ]
        )
    (production / "STORYBOARD.md").write_text("\n".join(rows), encoding="utf-8")


def build_manifest(plan: dict, timed_scenes: list[dict]) -> dict:
    total = sum(scene["durationSeconds"] for scene in timed_scenes)
    fps = plan["metadata"]["fps"]
    return {
        "schemaVersion": 1,
        "metadata": {
            **plan["metadata"],
            "durationSeconds": round(total, 6),
            "durationInFrames": round(total * fps),
        },
        "style": plan["style"],
        "audio": {
            **plan["audio"],
            "narrationPath": "assets/audio/narration.wav",
            "musicPath": "assets/audio/music.wav",
            "impactPath": "assets/audio/sfx-impact.wav",
            "whooshPath": "assets/audio/sfx-whoosh.wav",
            "chimePath": "assets/audio/sfx-chime.wav",
        },
        "scenes": timed_scenes,
        "deliverables": {
            "preview": f"renders/{plan['metadata']['id']}-preview.mp4",
            "final": f"renders/{plan['metadata']['id']}.mp4",
            "qaReport": "qa/verification.json",
        },
    }


def update_status(production: Path, evidence: list[str]) -> None:
    path = production / "run-status.json"
    status = json.loads(path.read_text(encoding="utf-8"))
    status["stages"]["audio"] = {"status": "complete", "evidence": evidence}
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


async def generate(production: Path, provider_override: str | None) -> None:
    plan = json.loads((production / "story-plan.json").read_text(encoding="utf-8"))
    config = dict(plan["audio"])
    provider = provider_override or config.get("provider", "edge")
    audio_dir = production / "assets/audio"
    segment_dir = audio_dir / "segments"
    segment_dir.mkdir(parents=True, exist_ok=True)
    (production / "tmp").mkdir(parents=True, exist_ok=True)
    reports = []
    normalized_paths = []
    timed_scenes = []
    cursor = 0.0

    with tempfile.TemporaryDirectory(dir=production / "tmp") as temp_name:
        temp = Path(temp_name)
        for scene in plan["scenes"]:
            extension = "mp3" if provider == "edge" else "wav"
            raw = temp / f"{scene['id']}-raw.{extension}"
            if provider == "edge":
                words = await edge_segment(scene["narration"], config, raw)
            elif provider == "silent":
                words = silent_segment(scene["narration"], raw)
            elif provider == "f5":
                words = f5_segment(scene["narration"], config, production, raw, temp)
            else:
                raise ValueError(f"unsupported provider: {provider}")
            raw_duration = probe(raw)["duration"]
            duration = quantized_scene_duration(raw_duration)
            normalized = segment_dir / f"{scene['id']}.wav"
            normalize_with_padding(raw, normalized, duration)
            normalized_paths.append(normalized)
            shifted_words = [
                {
                    **word,
                    "start": round(cursor + INTRO_PAD + word["start"], 6),
                    "duration": round(word["duration"], 6),
                }
                for word in words
            ]
            timed_scene = {
                **scene,
                "startSeconds": round(cursor, 6),
                "durationSeconds": round(duration, 6),
                "startFrame": round(cursor * plan["metadata"]["fps"]),
                "durationInFrames": round(duration * plan["metadata"]["fps"]),
                "narrationPath": normalized.relative_to(production).as_posix(),
                "captionFrom": round(cursor + INTRO_PAD, 6),
                "captionTo": round(cursor + duration - 0.35, 6),
                "words": shifted_words,
            }
            timed_scenes.append(timed_scene)
            reports.append(
                {
                    "sceneId": scene["id"],
                    "text": scene["narration"],
                    "rawDuration": round(raw_duration, 6),
                    "durationSeconds": round(duration, 6),
                    "path": normalized.relative_to(production).as_posix(),
                    "words": shifted_words,
                }
            )
            cursor += duration

    narration = audio_dir / "narration.wav"
    concat_wavs(normalized_paths, narration)
    music = audio_dir / "music.wav"
    make_music(music, cursor, plan["style"]["key"])
    sfx = make_sfx(audio_dir)
    probes = [
        probe(narration),
        probe(music),
        *(probe(path) for path in sfx.values()),
    ]
    passed = (
        abs(probes[0]["duration"] - cursor) <= 0.03
        and all(item["sampleRate"] == RATE and item["channels"] == 1 for item in probes)
    )
    if not passed:
        raise ValueError("audio probes failed")

    audio_meta = {
        "provider": provider,
        "voice": config.get("voice"),
        "voices": reports,
        "bgm": {"path": music.relative_to(production).as_posix(), "duration": round(cursor, 6)},
        "sfx": [
            {"id": key, "path": path.relative_to(production).as_posix()}
            for key, path in sfx.items()
        ],
        "total_duration_s": round(cursor, 6),
    }
    (production / "audio_meta.json").write_text(
        json.dumps(audio_meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest = build_manifest(plan, timed_scenes)
    (production / "production-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_storyboard(production, plan, timed_scenes)
    report_path = production / "qa/audio.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps({"pass": passed, "audio": probes, "segments": reports}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    update_status(
        production,
        [
            "audio_meta.json",
            "production-manifest.json",
            report_path.relative_to(production).as_posix(),
            narration.relative_to(production).as_posix(),
            music.relative_to(production).as_posix(),
        ],
    )
    print(json.dumps(audio_meta, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production", required=True)
    parser.add_argument("--provider", choices=["edge", "f5", "silent"])
    args = parser.parse_args()
    asyncio.run(generate(Path(args.production).resolve(), args.provider))


if __name__ == "__main__":
    main()
