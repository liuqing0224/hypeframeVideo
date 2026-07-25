#!/usr/bin/env python3
import argparse
import asyncio
import json
import math
import re
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np


RATE = 48000
INTRO_PAD = 0.45
TOTAL_PAD = 1.2
CAPTION_MAX_CHARS = 14
MIN_SHOT_SECONDS = 0.5


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
    tokens = re.findall(r"[A-Za-z0-9]+|[\u3400-\u9fff]{1,4}|[^\s]", text)
    if not tokens:
        return []
    weights = [max(1, len(token)) for token in tokens]
    total_weight = sum(weights)
    cursor = 0.0
    words = []
    for index, (token, weight) in enumerate(zip(tokens, weights)):
        token_duration = duration * weight / total_weight
        words.append(
            {
                "text": token,
                "start": round(cursor, 6),
                "duration": round(
                    duration - cursor if index == len(tokens) - 1 else token_duration,
                    6,
                ),
            }
        )
        cursor += token_duration
    return words


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


def scene_lines(scene: dict) -> list[dict]:
    configured = scene.get("script")
    if not configured:
        configured = [
            {
                "speaker": "旁白",
                "role": "narrator",
                "kind": "narration",
                "text": scene["narration"],
            }
        ]
    lines = []
    for index, item in enumerate(configured):
        text = str(item.get("text", "")).strip()
        if not text:
            raise ValueError(f"{scene['id']}: script line {index + 1} is empty")
        lines.append(
            {
                **item,
                "id": item.get("id") or f"{scene['id']}-line-{index + 1}",
                "speaker": item.get("speaker") or "旁白",
                "role": item.get("role") or "narrator",
                "kind": item.get("kind") or "narration",
                "text": text,
            }
        )
    return lines


def line_voice_config(config: dict, line: dict) -> dict:
    resolved = dict(config)
    profile = config.get("voiceCast", {}).get(line.get("role"))
    if isinstance(profile, str):
        resolved["voice"] = profile
    elif isinstance(profile, dict):
        resolved.update(profile)
    return resolved


def line_pause_seconds(line: dict, next_line: dict | None) -> float:
    if next_line is None:
        return 0.0
    pause = 0.18
    if line.get("speaker") != next_line.get("speaker"):
        pause += 0.12
    if re.search(r"[。！？!?]$", line["text"]):
        pause += 0.12
    elif re.search(r"[，；、,;]$", line["text"]):
        pause += 0.06
    return round(pause, 3)


def normalize_audio(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(source),
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


def assemble_scene_wav(
    sources: list[Path],
    pauses: list[float],
    target: Path,
    duration: float,
) -> None:
    if len(sources) != len(pauses):
        raise ValueError("each line source requires a trailing pause value")
    target.parent.mkdir(parents=True, exist_ok=True)
    expected_frames = round(duration * RATE)
    written_frames = 0
    with wave.open(str(target), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(RATE)

        intro_frames = round(INTRO_PAD * RATE)
        output.writeframes(b"\0\0" * intro_frames)
        written_frames += intro_frames

        for source, pause in zip(sources, pauses):
            with wave.open(str(source), "rb") as segment:
                if (
                    segment.getnchannels() != 1
                    or segment.getsampwidth() != 2
                    or segment.getframerate() != RATE
                ):
                    raise ValueError(f"incompatible line segment: {source}")
                frames = segment.readframes(segment.getnframes())
                output.writeframes(frames)
                written_frames += len(frames) // 2
            pause_frames = round(pause * RATE)
            output.writeframes(b"\0\0" * pause_frames)
            written_frames += pause_frames

        if written_frames > expected_frames:
            raise ValueError(
                f"scene audio exceeds declared duration by "
                f"{(written_frames - expected_frames) / RATE:.3f}s"
            )
        output.writeframes(b"\0\0" * (expected_frames - written_frames))


def short_caption_chunks(text: str, max_chars: int = CAPTION_MAX_CHARS) -> list[str]:
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    clauses = [
        part
        for part in re.findall(r".+?[，。！？；、,.!?;:]|.+$", text)
        if part
    ]
    chunks = []
    current = ""
    for clause in clauses:
        pieces = [
            clause[index : index + max_chars]
            for index in range(0, len(clause), max_chars)
        ]
        for piece in pieces:
            if current and len(current) + len(piece) > max_chars:
                chunks.append(current)
                current = ""
            if len(piece) == max_chars:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.append(piece)
            else:
                current += piece
    if current:
        chunks.append(current)
    if len(chunks) >= 2 and len(chunks[-1]) < 4:
        combined = chunks[-2] + chunks[-1]
        split_at = max(1, len(combined) // 2)
        chunks[-2:] = [combined[:split_at], combined[split_at:]]
    return chunks or [text]


def caption_cues_for_line(
    scene_id: str,
    line: dict,
    line_index: int,
    shot_id: str,
    start_seconds: float,
    duration_seconds: float,
) -> list[dict]:
    chunks = short_caption_chunks(line["text"])
    weights = [max(1, len(re.sub(r"\s", "", chunk))) for chunk in chunks]
    total_weight = sum(weights)
    cursor = start_seconds
    end_seconds = start_seconds + duration_seconds
    cues = []
    for index, (chunk, weight) in enumerate(zip(chunks, weights)):
        duration = duration_seconds * weight / total_weight
        cue_end = (
            end_seconds
            if index == len(chunks) - 1
            else min(end_seconds, cursor + duration)
        )
        cues.append(
            {
                "id": f"{line['id']}-caption-{index + 1}",
                "sceneId": scene_id,
                "lineId": line["id"],
                "shotId": shot_id,
                "speaker": line["speaker"],
                "role": line["role"],
                "kind": line["kind"],
                "text": chunk,
                "startSeconds": round(cursor, 6),
                "endSeconds": round(cue_end, 6),
            }
        )
        cursor = cue_end
    return cues


def build_shot_timings(
    scene: dict,
    line_timings: list[dict],
    duration: float,
) -> list[dict]:
    shots = scene.get("shots") or []
    if len(shots) != 3:
        shots = [
            {
                "id": f"{scene['id']}-shot-{index + 1}",
                "index": index + 1,
                "purpose": purpose,
                "framing": framing,
                "focusRole": focus,
                "lineIndex": min(index, max(0, len(line_timings) - 1)),
            }
            for index, (purpose, framing, focus) in enumerate(
                (
                    ("establish", "wide", "ensemble"),
                    ("action", "medium", "primary"),
                    ("reaction", "close", "primary"),
                )
            )
        ]

    if len(line_timings) >= 3:
        cut_one = line_timings[1]["localStart"]
        cut_two = line_timings[2]["localStart"]
    elif len(line_timings) == 2:
        cut_one = line_timings[1]["localStart"]
        cut_two = max(duration * 0.72, cut_one + line_timings[1]["duration"] * 0.62)
    else:
        cut_one = duration * 0.31
        cut_two = duration * 0.68

    cut_one = min(max(cut_one, MIN_SHOT_SECONDS), duration - 2 * MIN_SHOT_SECONDS)
    cut_two = min(
        max(cut_two, cut_one + MIN_SHOT_SECONDS),
        duration - MIN_SHOT_SECONDS,
    )
    starts = [0.0, cut_one, cut_two]
    ends = [cut_one, cut_two, duration]
    return [
        {
            **shot,
            "startSeconds": round(start, 6),
            "durationSeconds": round(end - start, 6),
        }
        for shot, start, end in zip(shots, starts, ends)
    ]


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


def make_ambience(path: Path, seconds: float, style_key: str) -> None:
    count = round(seconds * RATE)
    t = np.arange(count, dtype=np.float64) / RATE
    seed = {
        "science": 101,
        "fantasy": 211,
        "history": 307,
        "field-trip": 401,
    }[style_key]
    rng = np.random.default_rng(seed)
    texture = rng.normal(0, 0.0032, count)
    movement = (
        np.sin(2 * np.pi * 0.09 * t) * 0.0025
        + np.sin(2 * np.pi * 0.17 * t + 1.1) * 0.0018
    )
    fade = np.minimum(1.0, np.minimum(t / 0.8, (seconds - t) / 0.8))
    write_wav(path, (texture + movement) * np.clip(fade, 0, 1))


def make_sfx(audio_dir: Path) -> dict[str, Path]:
    impact = audio_dir / "sfx-impact.wav"
    whoosh = audio_dir / "sfx-whoosh.wav"
    chime = audio_dir / "sfx-chime.wav"
    cut = audio_dir / "sfx-cut.wav"
    rustle = audio_dir / "sfx-rustle.wav"
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
    cut_samples = (
        rng.normal(0, 1, len(t))
        * np.exp(-t * 12.0)
        * np.sin(np.pi * np.clip(t / 0.14, 0, 1))
        * 0.11
    )
    write_wav(cut, cut_samples)
    rustle_envelope = (
        np.sin(np.pi * np.clip(t / 0.72, 0, 1)) ** 2
        * np.exp(-t * 0.9)
    )
    write_wav(rustle, rng.normal(0, 1, len(t)) * rustle_envelope * 0.035)
    return {
        "impact": impact,
        "whoosh": whoosh,
        "chime": chime,
        "cut": cut,
        "rustle": rustle,
    }


def build_audio_clips(
    production: Path,
    timed_scenes: list[dict],
    total_duration: float,
    sfx: dict[str, Path],
    sfx_durations: dict[str, float],
) -> list[dict]:
    clips = [
        {
            "id": "narration",
            "src": "assets/audio/narration.wav",
            "startSeconds": 0.0,
            "durationSeconds": round(total_duration, 6),
            "trackIndex": 950,
            "volume": 1.0,
            "bus": "dialogue",
        },
        {
            "id": "music",
            "src": "assets/audio/music.wav",
            "startSeconds": 0.0,
            "durationSeconds": round(total_duration, 6),
            "trackIndex": 951,
            "volume": 0.24,
            "bus": "music",
        },
        {
            "id": "ambience",
            "src": "assets/audio/ambience.wav",
            "startSeconds": 0.0,
            "durationSeconds": round(total_duration, 6),
            "trackIndex": 952,
            "volume": 0.42,
            "bus": "ambience",
        },
    ]
    first_shot_keys = ("impact", "whoosh", "chime")
    followup_keys = ("cut", "rustle")
    track_index = 953
    for scene_index, scene in enumerate(timed_scenes):
        for shot_index, shot in enumerate(scene["shots"]):
            key = (
                first_shot_keys[scene_index % len(first_shot_keys)]
                if shot_index == 0
                else followup_keys[(shot_index - 1) % len(followup_keys)]
            )
            start = scene["startSeconds"] + shot["startSeconds"]
            if shot_index == 0:
                start += 0.08
            available = max(0.0, total_duration - start)
            duration = min(sfx_durations[key], available)
            clips.append(
                {
                    "id": (
                        f"sfx-{scene_index + 1}"
                        if shot_index == 0
                        else f"sfx-{scene['id']}-shot-{shot_index + 1}"
                    ),
                    "src": sfx[key].relative_to(production).as_posix(),
                    "startSeconds": round(start, 6),
                    "durationSeconds": round(duration, 6),
                    "trackIndex": track_index,
                    "volume": 0.72 if shot_index == 0 else 0.44,
                    "bus": "sfx",
                    "sceneId": scene["id"],
                    "shotId": shot["id"],
                    "cue": key,
                }
            )
            track_index += 1
    return clips


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
        lines = scene_lines(scene)
        rows.extend(
            [
                f"## Frame {scene['index']} - {scene['title']}",
                "",
                "- status: timed",
                f"- src: compositions/{scene['id']}.html",
                f"- duration: {timing['durationSeconds']:.3f}s",
                f"- transition_in: {scene['transitionIn']}",
                f"- scene: {scene['shot']['architecture']}；{scene['shot']['primary']}",
                "- voiceover: "
                + " / ".join(
                    f"{line['speaker']}：{line['text']}"
                    for line in lines
                ),
                f"- motion: {', '.join(scene['motionRules'])}",
                "- sfx: shot-synced impact, cut, and rustle cues",
                "",
                f"{scene['title']}承担故事的 {scene['beat']} 节点。"
                "对白、镜头和声效按三个内部镜头对齐。",
                "",
            ]
        )
        for shot in timing["shots"]:
            rows.extend(
                [
                    f"### Shot {scene['index']}.{shot['index']} - {shot['purpose']}",
                    "",
                    f"- from: {shot['startSeconds']:.3f}s",
                    f"- duration: {shot['durationSeconds']:.3f}s",
                    f"- framing: {shot['framing']}",
                    f"- focus: {shot['focusRole']}",
                    "",
                ]
            )
    (production / "STORYBOARD.md").write_text("\n".join(rows), encoding="utf-8")


def build_manifest(
    plan: dict,
    timed_scenes: list[dict],
    captions: list[dict] | None = None,
    audio_clips: list[dict] | None = None,
) -> dict:
    total = sum(scene["durationSeconds"] for scene in timed_scenes)
    fps = plan["metadata"]["fps"]
    manifest = {
        "schemaVersion": plan.get("schemaVersion", 1),
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
            "ambiencePath": "assets/audio/ambience.wav",
            "impactPath": "assets/audio/sfx-impact.wav",
            "whooshPath": "assets/audio/sfx-whoosh.wav",
            "chimePath": "assets/audio/sfx-chime.wav",
            "cutPath": "assets/audio/sfx-cut.wav",
            "rustlePath": "assets/audio/sfx-rustle.wav",
        },
        "scenes": timed_scenes,
        "deliverables": {
            "preview": f"renders/{plan['metadata']['id']}-preview.mp4",
            "final": f"renders/{plan['metadata']['id']}.mp4",
            "qaReport": "qa/verification.json",
        },
    }
    if captions is not None:
        manifest["captions"] = captions
    if audio_clips is not None:
        manifest["audioClips"] = audio_clips
    return manifest


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
    line_dir = audio_dir / "lines"
    segment_dir.mkdir(parents=True, exist_ok=True)
    line_dir.mkdir(parents=True, exist_ok=True)
    (production / "tmp").mkdir(parents=True, exist_ok=True)
    reports = []
    normalized_paths = []
    timed_scenes = []
    captions = []
    cursor = 0.0

    with tempfile.TemporaryDirectory(dir=production / "tmp") as temp_name:
        temp = Path(temp_name)
        for scene in plan["scenes"]:
            lines = scene_lines(scene)
            line_paths = []
            line_timings = []
            scene_words = []
            pauses = []
            local_cursor = INTRO_PAD
            for line_index, line in enumerate(lines):
                extension = "mp3" if provider == "edge" else "wav"
                raw = temp / f"{line['id']}-raw.{extension}"
                line_config = line_voice_config(config, line)
                if provider == "edge":
                    words = await edge_segment(line["text"], line_config, raw)
                elif provider == "silent":
                    words = silent_segment(line["text"], raw)
                elif provider == "f5":
                    words = f5_segment(
                        line["text"],
                        line_config,
                        production,
                        raw,
                        temp,
                    )
                else:
                    raise ValueError(f"unsupported provider: {provider}")

                line_path = line_dir / f"{line['id']}.wav"
                normalize_audio(raw, line_path)
                line_duration = probe(line_path)["duration"]
                global_start = cursor + local_cursor
                shifted_words = [
                    {
                        **word,
                        "lineId": line["id"],
                        "speaker": line["speaker"],
                        "role": line["role"],
                        "start": round(global_start + word["start"], 6),
                        "duration": round(word["duration"], 6),
                    }
                    for word in words
                ]
                scene_words.extend(shifted_words)
                pause = line_pause_seconds(
                    line,
                    lines[line_index + 1]
                    if line_index + 1 < len(lines)
                    else None,
                )
                pauses.append(pause)
                line_paths.append(line_path)
                timing = {
                    **line,
                    "lineIndex": line_index,
                    "localStart": round(local_cursor, 6),
                    "startSeconds": round(global_start, 6),
                    "duration": round(line_duration, 6),
                    "pauseAfter": pause,
                    "voice": line_config.get("voice"),
                    "path": line_path.relative_to(production).as_posix(),
                    "words": shifted_words,
                }
                line_timings.append(timing)
                reports.append(
                    {
                        "sceneId": scene["id"],
                        "lineId": line["id"],
                        "speaker": line["speaker"],
                        "role": line["role"],
                        "kind": line["kind"],
                        "text": line["text"],
                        "voice": line_config.get("voice"),
                        "rawDuration": round(line_duration, 6),
                        "startSeconds": round(global_start, 6),
                        "path": line_path.relative_to(production).as_posix(),
                        "words": shifted_words,
                    }
                )
                local_cursor += line_duration + pause

            spoken_duration = sum(item["duration"] for item in line_timings) + sum(pauses)
            duration = quantized_scene_duration(spoken_duration)
            normalized = segment_dir / f"{scene['id']}.wav"
            assemble_scene_wav(line_paths, pauses, normalized, duration)
            normalized_paths.append(normalized)
            shot_timings = build_shot_timings(scene, line_timings, duration)
            scene_captions = []
            for line_index, timing in enumerate(line_timings):
                shot = shot_timings[min(line_index, len(shot_timings) - 1)]
                line_cues = caption_cues_for_line(
                    scene["id"],
                    timing,
                    line_index,
                    shot["id"],
                    timing["startSeconds"],
                    timing["duration"],
                )
                scene_captions.extend(line_cues)
                captions.extend(line_cues)

            timed_script = [
                {
                    key: value
                    for key, value in timing.items()
                    if key not in {"localStart", "words"}
                }
                for timing in line_timings
            ]
            timed_scene = {
                **scene,
                "script": timed_script,
                "shots": shot_timings,
                "startSeconds": round(cursor, 6),
                "durationSeconds": round(duration, 6),
                "startFrame": round(cursor * plan["metadata"]["fps"]),
                "durationInFrames": round(duration * plan["metadata"]["fps"]),
                "narrationPath": normalized.relative_to(production).as_posix(),
                "captionFrom": (
                    scene_captions[0]["startSeconds"]
                    if scene_captions
                    else round(cursor + INTRO_PAD, 6)
                ),
                "captionTo": (
                    scene_captions[-1]["endSeconds"]
                    if scene_captions
                    else round(cursor + duration - 0.35, 6)
                ),
                "captions": scene_captions,
                "words": scene_words,
            }
            timed_scenes.append(timed_scene)
            cursor += duration

    narration = audio_dir / "narration.wav"
    concat_wavs(normalized_paths, narration)
    music = audio_dir / "music.wav"
    make_music(music, cursor, plan["style"]["key"])
    ambience = audio_dir / "ambience.wav"
    make_ambience(ambience, cursor, plan["style"]["key"])
    sfx = make_sfx(audio_dir)
    probes = [
        probe(narration),
        probe(music),
        probe(ambience),
        *(probe(path) for path in sfx.values()),
    ]
    passed = (
        abs(probes[0]["duration"] - cursor) <= 0.03
        and abs(probes[1]["duration"] - cursor) <= 0.03
        and abs(probes[2]["duration"] - cursor) <= 0.03
        and all(item["sampleRate"] == RATE and item["channels"] == 1 for item in probes)
    )
    if not passed:
        raise ValueError("audio probes failed")

    sfx_durations = {
        key: probe_result["duration"]
        for key, probe_result in zip(sfx, probes[3:])
    }
    audio_clips = build_audio_clips(
        production,
        timed_scenes,
        cursor,
        sfx,
        sfx_durations,
    )
    audio_meta = {
        "provider": provider,
        "voice": config.get("voice"),
        "voiceCast": config.get("voiceCast", {}),
        "voices": reports,
        "bgm": {"path": music.relative_to(production).as_posix(), "duration": round(cursor, 6)},
        "ambience": {
            "path": ambience.relative_to(production).as_posix(),
            "duration": round(cursor, 6),
        },
        "sfx": [
            {"id": key, "path": path.relative_to(production).as_posix()}
            for key, path in sfx.items()
        ],
        "sfxEvents": [
            clip
            for clip in audio_clips
            if clip.get("bus") == "sfx"
        ],
        "captions": captions,
        "total_duration_s": round(cursor, 6),
    }
    (production / "audio_meta.json").write_text(
        json.dumps(audio_meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest = build_manifest(
        plan,
        timed_scenes,
        captions=captions,
        audio_clips=audio_clips,
    )
    (production / "production-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_storyboard(production, plan, timed_scenes)
    report_path = production / "qa/audio.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "pass": passed,
                "audio": probes,
                "segments": reports,
                "captions": captions,
                "shots": [
                    {
                        "sceneId": scene["id"],
                        **shot,
                    }
                    for scene in timed_scenes
                    for shot in scene["shots"]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
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
            ambience.relative_to(production).as_posix(),
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
