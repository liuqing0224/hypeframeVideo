#!/usr/bin/env python3
import argparse
import json
import math
import os
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

from PIL import Image, ImageDraw


ANIMATION_MAP = Path(
    os.environ.get(
        "HYPERFRAMES_ANIMATION_MAP_SCRIPT",
        str(
            Path.home()
            / ".agents/skills/hyperframes-animation/scripts/animation-map.mjs"
        ),
    )
)
EXPECTED_LAYER_ORDER = [
    "backdrop",
    "rear",
    "architecture",
    "tertiary",
    "secondary",
    "primary",
    "foreground",
]


class StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, dict[str, str]]] = []
        self.compositions: list[dict[str, str]] = []
        self.direct_audio: list[dict[str, str]] = []
        self.remote_urls: list[str] = []
        self.layer_indices: list[tuple[str, int]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        for value in attributes.values():
            if value.startswith(("http://", "https://", "//")):
                self.remote_urls.append(value)
        if "data-composition-id" in attributes:
            self.compositions.append(attributes)
        if tag == "audio" and self.stack:
            parent_attrs = self.stack[-1][1]
            if parent_attrs.get("data-composition-id") == "main":
                self.direct_audio.append(attributes)
        if "data-pixel-layer" in attributes and "data-pixel-z" in attributes:
            self.layer_indices.append(
                (attributes["data-pixel-layer"], int(attributes["data-pixel-z"]))
            )
        if tag not in {"area", "base", "br", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}:
            self.stack.append((tag, attributes))

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                return


def read_html(path: Path) -> StructureParser:
    parser = StructureParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def structural_checks(production: Path) -> list[dict]:
    manifest = json.loads((production / "production-manifest.json").read_text(encoding="utf-8"))
    findings = []
    index_path = production / "index.html"
    parser = read_html(index_path)
    root_matches = [item for item in parser.compositions if item.get("data-composition-id") == "main"]
    findings.append(
        {
            "id": "single-main-root",
            "pass": len(root_matches) == 1,
            "detail": f"found {len(root_matches)} main roots",
        }
    )
    static_duration = root_matches[0].get("data-duration") if root_matches else None
    findings.append(
        {
            "id": "static-root-duration",
            "pass": static_duration == f"{manifest['metadata']['durationSeconds']:.3f}".rstrip("0").rstrip("."),
            "detail": f"root={static_duration}, manifest={manifest['metadata']['durationSeconds']}",
        }
    )
    findings.append(
        {
            "id": "root-direct-audio",
            "pass": len(parser.direct_audio) == 5,
            "detail": f"found {len(parser.direct_audio)} direct audio clips",
        }
    )
    findings.append(
        {
            "id": "offline-root",
            "pass": not parser.remote_urls,
            "detail": parser.remote_urls,
        }
    )
    root_source = index_path.read_text(encoding="utf-8")
    author = manifest["metadata"]["author"]
    findings.append(
        {
            "id": "author-hidden",
            "pass": author["class"] not in root_source
            and "author" not in root_source.lower()
            and "班级" not in root_source,
            "detail": (
                "task-card author fields must not be injected; a protagonist may "
                "legitimately share the author's simulated name"
            ),
        }
    )

    for scene in manifest["scenes"]:
        html_path = production / "compositions" / f"{scene['id']}.html"
        scene_parser = read_html(html_path)
        ids = [
            item.get("data-composition-id")
            for item in scene_parser.compositions
            if item.get("data-composition-id")
        ]
        source = html_path.read_text(encoding="utf-8")
        expected_key = f'window.__timelines["{scene["id"]}"]'
        actual_order = [
            name for name, _ in sorted(scene_parser.layer_indices, key=lambda item: item[1])
        ]
        findings.extend(
            [
                {
                    "id": f"{scene['id']}-root",
                    "pass": ids == [scene["id"]],
                    "detail": ids,
                },
                {
                    "id": f"{scene['id']}-timeline",
                    "pass": expected_key in source and "gsap.timeline({ paused: true })" in source,
                    "detail": expected_key,
                },
                {
                    "id": f"{scene['id']}-layer-order",
                    "pass": actual_order == EXPECTED_LAYER_ORDER,
                    "detail": actual_order,
                },
                {
                    "id": f"{scene['id']}-offline",
                    "pass": not scene_parser.remote_urls,
                    "detail": scene_parser.remote_urls,
                },
                {
                    "id": f"{scene['id']}-no-audio",
                    "pass": "<audio" not in source and "<video" not in source,
                    "detail": "sub-compositions must not own driven media",
                },
            ]
        )
    return findings


def motion_checks(production: Path) -> list[dict]:
    findings = []
    for path in sorted((production / "compositions").glob("*.motion.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        subjects = payload["subjects"]
        starts = {subject["role"]: subject["entranceStart"] for subject in subjects}
        in_frame = True
        for subject in subjects:
            bounds = subject["bounds"]
            in_frame &= (
                bounds["x"] >= 0
                and bounds["y"] >= 0
                and bounds["x"] + bounds["width"] <= 1920
                and bounds["y"] + bounds["height"] <= 1080
            )
        phases = payload["phases"]
        continuous = (
            phases["entrance"][0] == 0
            and phases["entrance"][1] == phases["action"][0]
            and phases["action"][1] == phases["hold"][0]
            and phases["hold"][1] == phases["transition"][0]
            and phases["transition"][1] == payload["durationSeconds"]
        )
        findings.extend(
            [
                {
                    "id": f"{payload['compositionId']}-primary-first",
                    "pass": starts["primary"] < starts["secondary"] < starts["tertiary"],
                    "detail": starts,
                },
                {
                    "id": f"{payload['compositionId']}-subjects-in-frame",
                    "pass": in_frame,
                    "detail": [subject["bounds"] for subject in subjects],
                },
                {
                    "id": f"{payload['compositionId']}-phase-continuity",
                    "pass": continuous,
                    "detail": phases,
                },
                {
                    "id": f"{payload['compositionId']}-finite",
                    "pass": payload["assertions"].get("noUnboundedAnimation") is True,
                    "detail": payload["assertions"],
                },
            ]
        )
    return findings


def run_command(command: list[str], cwd: Path, log_path: Path) -> dict:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "$ " + " ".join(command) + "\n\nSTDOUT\n" + result.stdout + "\nSTDERR\n" + result.stderr,
        encoding="utf-8",
    )
    return {
        "command": command,
        "exitCode": result.returncode,
        "log": log_path.relative_to(cwd).as_posix(),
        "pass": result.returncode == 0,
    }


def update_stage(production: Path, stage: str, passed: bool, evidence: list[str]) -> None:
    path = production / "run-status.json"
    status = json.loads(path.read_text(encoding="utf-8"))
    status["stages"][stage] = {
        "status": "complete" if passed else "failed",
        "evidence": evidence,
    }
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def check(production: Path, run_hyperframes: bool = True) -> dict:
    findings = structural_checks(production) + motion_checks(production)
    command_reports = []
    if run_hyperframes:
        command_reports.append(
            run_command(
                ["npx", "--yes", "hyperframes@0.7.70", "lint", "--verbose", "."],
                production,
                production / "qa/hyperframes-lint.log",
            )
        )
        command_reports.append(
            run_command(
                [
                    "npx",
                    "--yes",
                    "hyperframes@0.7.70",
                    "check",
                    "--strict",
                    "--snapshots",
                    "--at-transitions",
                    "--tolerance=80",
                    "--frame-check=severity=error;seek=.25,.5,.75;tol=4",
                    ".",
                ],
                production,
                production / "qa/hyperframes-check.log",
            )
        )
        manifest = json.loads(
            (production / "production-manifest.json").read_text(encoding="utf-8")
        )
        midpoints = [
            scene["startSeconds"] + scene["durationSeconds"] / 2
            for scene in manifest["scenes"]
        ]
        command_reports.append(
            run_command(
                [
                    "npx",
                    "--yes",
                    "hyperframes@0.7.70",
                    "snapshot",
                    "--at",
                    ",".join(f"{value:.3f}" for value in midpoints),
                    "--no-end",
                    "--output",
                    "qa/scene-midpoints",
                    ".",
                ],
                production,
                production / "qa/hyperframes-snapshot.log",
            )
        )
        command_reports.append(
            run_command(
                [
                    "env",
                    "HYPERFRAMES_SKILL_PKG_VERSION=0.7.70",
                    "HYPERFRAMES_SKILL_BOOTSTRAP_DEPS=1",
                    "node",
                    str(ANIMATION_MAP),
                    ".",
                    "--out",
                    "qa/animation-map",
                ],
                production,
                production / "qa/animation-map.log",
            )
        )
    passed = all(item["pass"] for item in findings) and all(
        item["pass"] for item in command_reports
    )
    report = {
        "stage": "check",
        "pass": passed,
        "findings": findings,
        "commands": command_reports,
    }
    report_path = production / "qa/verification.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    evidence = [report_path.relative_to(production).as_posix()]
    evidence.extend(item["log"] for item in command_reports)
    if (production / "qa/scene-midpoints").is_dir():
        evidence.append("qa/scene-midpoints")
    if (production / "qa/animation-map/animation-map.json").is_file():
        evidence.extend(["qa/animation-map", "qa/animation-map.log"])
    update_stage(production, "check", passed, evidence)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not passed:
        raise SystemExit(2)
    return report


def ffprobe(path: Path) -> dict:
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
    return json.loads(result.stdout)


def evidence_frames(production: Path, video: Path, duration: float) -> list[Path]:
    output = production / "qa/render-evidence"
    output.mkdir(parents=True, exist_ok=True)
    frames = []
    for index, fraction in enumerate((0.18, 0.5, 0.84), start=1):
        target = output / f"frame-{index}.png"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-ss",
                f"{duration * fraction:.3f}",
                "-i",
                str(video),
                "-frames:v",
                "1",
                str(target),
            ],
            check=True,
        )
        frames.append(target)
    return frames


def transition_evidence_frames(
    production: Path,
    video: Path,
    boundaries: list[float],
) -> list[Path]:
    output = production / "qa/render-transitions"
    output.mkdir(parents=True, exist_ok=True)
    frames = []
    for transition_index, boundary in enumerate(boundaries, start=1):
        for offset_index, offset in enumerate((-0.2, 0.0, 0.2), start=1):
            target = output / (
                f"transition-{transition_index}-"
                f"{offset_index}-at-{boundary + offset:.3f}s.png"
            )
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-v",
                    "error",
                    "-ss",
                    f"{boundary + offset:.3f}",
                    "-i",
                    str(video),
                    "-frames:v",
                    "1",
                    str(target),
                ],
                check=True,
            )
            frames.append(target)
    return frames


def make_contact_sheet(paths: list[Path], target: Path) -> None:
    tiles = []
    for path in paths:
        with Image.open(path) as source:
            image = source.convert("RGB")
            image.thumbnail((640, 360), Image.Resampling.LANCZOS)
            tiles.append(image.copy())
    canvas = Image.new("RGB", (640 * len(tiles), 400), "#111111")
    draw = ImageDraw.Draw(canvas)
    for index, image in enumerate(tiles):
        canvas.paste(image, (index * 640, 0))
        draw.text((index * 640 + 14, 370), f"render evidence {index + 1}", fill="#ffffff")
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target)


def make_transition_contact_sheet(paths: list[Path], target: Path) -> None:
    tiles = []
    for path in paths:
        with Image.open(path) as source:
            image = source.convert("RGB")
            image.thumbnail((640, 360), Image.Resampling.LANCZOS)
            tiles.append((path.stem, image.copy()))
    columns = 3
    rows = math.ceil(len(tiles) / columns)
    canvas = Image.new("RGB", (640 * columns, 400 * rows), "#111111")
    draw = ImageDraw.Draw(canvas)
    for index, (label, image) in enumerate(tiles):
        left = (index % columns) * 640
        top = (index // columns) * 400
        canvas.paste(image, (left, top))
        draw.text((left + 14, top + 370), label, fill="#ffffff")
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target)


def authored_audio_sync_findings(production: Path, manifest: dict) -> list[dict]:
    parser = read_html(production / "index.html")
    audio_by_id = {item.get("id"): item for item in parser.direct_audio}
    findings = []
    for index, scene in enumerate(manifest["scenes"], start=1):
        audio = audio_by_id.get(f"sfx-{index}", {})
        actual = float(audio.get("data-start", "nan"))
        expected = scene["startSeconds"] + 0.08
        motion = json.loads(
            (
                production
                / "compositions"
                / f"{scene['id']}.motion.json"
            ).read_text(encoding="utf-8")
        )
        primary = next(
            subject for subject in motion["subjects"] if subject["role"] == "primary"
        )
        primary_start = scene["startSeconds"] + primary["entranceStart"]
        findings.append(
            {
                "id": f"sfx-{index}-entry-sync",
                "pass": math.isclose(actual, expected, abs_tol=0.001)
                and abs(actual - primary_start) <= 0.25,
                "detail": {
                    "sfxStart": actual,
                    "expected": expected,
                    "primaryEntrance": primary_start,
                    "deltaSeconds": abs(actual - primary_start),
                },
            }
        )
    return findings


def verify_render(
    production: Path,
    video: Path,
    manual_approved: bool = False,
    promote_to: Path | None = None,
) -> dict:
    manifest = json.loads((production / "production-manifest.json").read_text(encoding="utf-8"))
    probe = ffprobe(video)
    video_streams = [item for item in probe["streams"] if item["codec_type"] == "video"]
    audio_streams = [item for item in probe["streams"] if item["codec_type"] == "audio"]
    video_stream = video_streams[0] if video_streams else {}
    duration = float(probe["format"].get("duration", 0))
    declared = manifest["metadata"]["durationSeconds"]
    fps_parts = video_stream.get("avg_frame_rate", "0/1").split("/")
    fps = float(fps_parts[0]) / max(1.0, float(fps_parts[1]))
    frames = int(video_stream.get("nb_frames") or round(duration * fps))
    expected_frames = manifest["metadata"]["durationInFrames"]
    findings = [
        {"id": "nonempty", "pass": video.is_file() and video.stat().st_size > 100_000, "detail": video.stat().st_size},
        {"id": "resolution", "pass": video_stream.get("width") == 1920 and video_stream.get("height") == 1080, "detail": [video_stream.get("width"), video_stream.get("height")]},
        {"id": "fps", "pass": math.isclose(fps, 30, abs_tol=0.001), "detail": fps},
        {"id": "video-codec", "pass": video_stream.get("codec_name") == "h264", "detail": video_stream.get("codec_name")},
        {"id": "audio-codec", "pass": bool(audio_streams) and audio_streams[0].get("codec_name") == "aac", "detail": [item.get("codec_name") for item in audio_streams]},
        {"id": "duration", "pass": abs(duration - declared) <= 1 / 30 + 0.01, "detail": {"encoded": duration, "declared": declared}},
        {"id": "frame-count", "pass": abs(frames - expected_frames) <= 1, "detail": {"encoded": frames, "declared": expected_frames}},
    ]
    findings.extend(authored_audio_sync_findings(production, manifest))
    extracted = evidence_frames(production, video, declared)
    contact = production / "qa/render-contact-sheet.png"
    make_contact_sheet(extracted, contact)
    transition_extracted = transition_evidence_frames(
        production,
        video,
        [scene["startSeconds"] for scene in manifest["scenes"][1:]],
    )
    transition_contact = production / "qa/render-transition-contact-sheet.png"
    make_transition_contact_sheet(transition_extracted, transition_contact)
    encoded_passed = all(item["pass"] for item in findings)
    report = {
        "stage": "encoded-output",
        "pass": encoded_passed and manual_approved,
        "encodedPass": encoded_passed,
        "manualApproved": manual_approved,
        "video": video.relative_to(production).as_posix(),
        "findings": findings,
        "evidenceFrames": [path.relative_to(production).as_posix() for path in extracted],
        "contactSheet": contact.relative_to(production).as_posix(),
        "transitionEvidenceFrames": [
            path.relative_to(production).as_posix()
            for path in transition_extracted
        ],
        "transitionContactSheet": transition_contact.relative_to(production).as_posix(),
    }
    report_path = production / "qa/render-verification.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    update_stage(
        production,
        "qa",
        encoded_passed and manual_approved,
        [
            report_path.relative_to(production).as_posix(),
            contact.relative_to(production).as_posix(),
            transition_contact.relative_to(production).as_posix(),
        ],
    )
    if encoded_passed and not manual_approved:
        status_path = production / "run-status.json"
        status = json.loads(status_path.read_text(encoding="utf-8"))
        status["stages"]["qa"]["status"] = "ready"
        status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if encoded_passed and manual_approved and promote_to is not None:
        promote_to.mkdir(parents=True, exist_ok=True)
        shutil.copy2(video, promote_to / video.name)
        report["promotedTo"] = (promote_to / video.name).as_posix()
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not encoded_passed:
        raise SystemExit(2)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("--production", required=True)
    check_parser.add_argument("--structural-only", action="store_true")
    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("--production", required=True)
    render_parser.add_argument("--video", required=True)
    render_parser.add_argument("--manual-approved", action="store_true")
    render_parser.add_argument("--promote-to")
    args = parser.parse_args()
    production = Path(args.production).resolve()
    if args.command == "check":
        check(production, run_hyperframes=not args.structural_only)
    else:
        promote_to = Path(args.promote_to).resolve() if args.promote_to else None
        verify_render(
            production,
            Path(args.video).resolve(),
            manual_approved=args.manual_approved,
            promote_to=promote_to,
        )


if __name__ == "__main__":
    main()
