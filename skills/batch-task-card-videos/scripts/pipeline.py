#!/usr/bin/env python3
import argparse
import concurrent.futures
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import jsonschema
from PIL import Image, ImageDraw


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "skills/batch-task-card-videos/assets/task-card-batch.schema.json"
PLAN_SCRIPT = REPO_ROOT / "skills/plan-task-card-video/scripts/compile_plan.py"
QUEUE_SCRIPT = REPO_ROOT / "skills/generate-layered-pixel-assets/scripts/build_prompt_queue.py"
AUDIO_SCRIPT = REPO_ROOT / "skills/batch-task-card-videos/scripts/generate_audio.py"
LAYER_SCRIPT = REPO_ROOT / "skills/process-layered-assets/scripts/process_assets.py"
COMPOSE_SCRIPT = REPO_ROOT / "skills/compose-hyperframes-video/scripts/compose.py"
VERIFY_SCRIPT = REPO_ROOT / "skills/verify-hyperframes-video/scripts/verify.py"
MEDIA_USE = Path(
    os.environ.get(
        "HYPERFRAMES_MEDIA_USE_SCRIPT",
        str(Path.home() / ".agents/skills/media-use/scripts/resolve.mjs"),
    )
)

STAGES = [
    "plan",
    "visual_generation",
    "audio",
    "layer_processing",
    "composition",
    "check",
    "preview",
    "render",
    "qa",
]
ALLOWED_STATUSES = {"pending", "ready", "running", "complete", "failed", "blocked"}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def production_fingerprint(production: Path) -> str:
    digest = hashlib.sha256()
    paths = [
        production / "production-manifest.json",
        production / "index.html",
        *sorted((production / "compositions").glob("*.html")),
        *sorted((production / "compositions").glob("*.motion.json")),
    ]
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        digest.update(path.relative_to(production).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def load_batch(path: Path, validate: bool = True) -> dict:
    payload = load_json(path)
    if validate:
        schema = load_json(SCHEMA_PATH)
        jsonschema.Draft202012Validator(schema).validate(payload)
        ids = [card["id"] for card in payload["cards"]]
        if len(ids) != len(set(ids)):
            duplicates = sorted({card_id for card_id in ids if ids.count(card_id) > 1})
            raise ValueError(f"duplicate card ids: {duplicates}")
        forbidden_duration_keys = {"duration", "duration_seconds", "durationSeconds"}
        for card in payload["cards"]:
            if forbidden_duration_keys.intersection(card):
                raise ValueError(f"{card['id']}: task cards cannot set a video duration")
    return payload


def production_path(workspace: Path, card_id: str) -> Path:
    return workspace / "videos" / card_id


@contextlib.contextmanager
def production_lock(production: Path):
    production.mkdir(parents=True, exist_ok=True)
    lock_path = production / ".pipeline.lock"
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def run(command: list[str], cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )


def validate_status(status: dict) -> None:
    if set(status.get("stages", {})) != set(STAGES):
        raise ValueError("run-status.json does not contain the required stage set")
    for stage, payload in status["stages"].items():
        if payload.get("status") not in ALLOWED_STATUSES:
            raise ValueError(f"{stage}: invalid status {payload.get('status')!r}")


def update_stage(
    production: Path,
    stage: str,
    state: str,
    evidence: list[str] | None = None,
    error: str | None = None,
) -> None:
    if state not in ALLOWED_STATUSES:
        raise ValueError(state)
    status_path = production / "run-status.json"
    status = load_json(status_path)
    payload = {
        "status": state,
        "evidence": evidence or [],
        "updatedAt": now_iso(),
    }
    if error:
        payload["error"] = error
    status["stages"][stage] = payload
    write_json(status_path, status)


def init_project(production: Path) -> None:
    if (production / "meta.json").is_file() and (production / "package.json").is_file():
        return
    if production.exists() and any(production.iterdir()):
        allowed = {".pipeline.lock"}
        if {item.name for item in production.iterdir()} - allowed:
            raise ValueError(f"cannot initialize a non-HyperFrames non-empty directory: {production}")
    environment = dict(os.environ)
    environment["HYPERFRAMES_SKIP_SKILLS"] = "1"
    run(
        [
            "npx",
            "--yes",
            "hyperframes@0.7.70",
            "init",
            str(production),
            "--non-interactive",
            "--example=blank",
        ],
        cwd=production.parent,
        env=environment,
    )


def prepare_one(batch_path: Path, workspace: Path, card_id: str) -> dict:
    production = production_path(workspace, card_id)
    production.parent.mkdir(parents=True, exist_ok=True)
    init_project(production)
    with production_lock(production):
        run(
            [
                sys.executable,
                str(PLAN_SCRIPT),
                "--batch",
                str(batch_path),
                "--card-id",
                card_id,
                "--output",
                str(production),
            ],
            cwd=REPO_ROOT,
        )
        run(
            [sys.executable, str(QUEUE_SCRIPT), "--production", str(production)],
            cwd=REPO_ROOT,
        )
    return {"id": card_id, "production": str(production), "status": "prepared"}


def queue_complete(production: Path) -> bool:
    path = production / "tmp/imagegen/prompt-queue.jsonl"
    if not path.is_file():
        return False
    queue = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return bool(queue) and all(item["status"] == "generated" for item in queue)


def set_ready_states(production: Path) -> dict:
    status_path = production / "run-status.json"
    status = load_json(status_path)
    validate_status(status)
    stages = status["stages"]

    def ready(stage: str, condition: bool) -> None:
        if condition and stages[stage]["status"] in {"pending", "blocked"}:
            stages[stage] = {"status": "ready", "evidence": [], "updatedAt": now_iso()}

    ready("visual_generation", stages["plan"]["status"] == "complete" and not queue_complete(production))
    ready("audio", stages["plan"]["status"] == "complete")
    ready("layer_processing", stages["visual_generation"]["status"] == "complete")
    ready(
        "composition",
        stages["audio"]["status"] == "complete"
        and stages["layer_processing"]["status"] == "complete",
    )
    ready("check", stages["composition"]["status"] == "complete")
    ready("preview", stages["check"]["status"] == "complete")
    if stages["preview"]["status"] != "complete" and stages["render"]["status"] == "pending":
        stages["render"] = {
            "status": "blocked",
            "evidence": [],
            "error": "final Studio preview approval is required",
            "updatedAt": now_iso(),
        }
    ready("render", stages["preview"]["status"] == "complete")
    ready("qa", stages["render"]["status"] == "complete")
    write_json(status_path, status)
    return status


def scan_batch(batch: dict, workspace: Path) -> list[dict]:
    rows = []
    for card in batch["cards"]:
        production = production_path(workspace, card["id"])
        if not (production / "run-status.json").is_file():
            rows.append({"id": card["id"], "production": str(production), "status": "unprepared"})
            continue
        status = set_ready_states(production)
        rows.append(
            {
                "id": card["id"],
                "production": str(production),
                "stages": {
                    stage: status["stages"][stage]["status"]
                    for stage in STAGES
                },
            }
        )
    return rows


def execute_stage(
    production: Path,
    stage: str,
    audio_provider: str | None = None,
    structural_check: bool = False,
) -> None:
    update_stage(production, stage, "running")
    commands = {
        "audio": [
            sys.executable,
            str(AUDIO_SCRIPT),
            "--production",
            str(production),
            *([] if audio_provider is None else ["--provider", audio_provider]),
        ],
        "layer_processing": [
            sys.executable,
            str(LAYER_SCRIPT),
            "--production",
            str(production),
        ],
        "composition": [
            sys.executable,
            str(COMPOSE_SCRIPT),
            "--production",
            str(production),
        ],
        "check": [
            sys.executable,
            str(VERIFY_SCRIPT),
            "check",
            "--production",
            str(production),
            *(["--structural-only"] if structural_check else []),
        ],
    }
    try:
        result = run(commands[stage], cwd=REPO_ROOT)
        if load_json(production / "run-status.json")["stages"][stage]["status"] != "complete":
            update_stage(production, stage, "complete", [f"qa/{stage}.log"])
        log_path = production / f"qa/{stage}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(result.stdout + result.stderr, encoding="utf-8")
    except Exception as error:
        update_stage(production, stage, "failed", error=str(error))
        raise


def advance_one(
    production: Path,
    audio_provider: str | None,
    structural_check: bool,
) -> dict:
    completed = []
    errors = []
    with production_lock(production):
        for stage in ("audio", "layer_processing", "composition", "check"):
            status = set_ready_states(production)
            state = status["stages"][stage]["status"]
            if state == "complete":
                continue
            if state != "ready":
                continue
            try:
                execute_stage(
                    production,
                    stage,
                    audio_provider=audio_provider,
                    structural_check=structural_check,
                )
                completed.append(stage)
            except Exception as error:
                errors.append({"stage": stage, "error": str(error)})
                break
        status = set_ready_states(production)
    return {
        "id": production.name,
        "completed": completed,
        "errors": errors,
        "stages": {stage: status["stages"][stage]["status"] for stage in STAGES},
    }


def approval_path(workspace: Path, batch_id: str) -> Path:
    return workspace / "approvals" / f"{batch_id}-studio-preview.json"


def build_batch_contact_sheet(batch: dict, workspace: Path) -> Path:
    rows: list[tuple[str, Image.Image]] = []
    for card in batch["cards"]:
        production = production_path(workspace, card["id"])
        source_path = production / "qa/shot-midpoints/contact-sheet.jpg"
        if not source_path.is_file():
            source_path = production / "qa/scene-midpoints/contact-sheet.jpg"
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        with Image.open(source_path) as source:
            image = source.convert("RGB")
            image.thumbnail((1800, 420), Image.Resampling.LANCZOS)
            rows.append((card["id"], image.copy()))
    label_height = 34
    width = max(image.width for _, image in rows)
    height = sum(label_height + image.height for _, image in rows)
    canvas = Image.new("RGB", (width, height), "#101010")
    draw = ImageDraw.Draw(canvas)
    top = 0
    for card_id, image in rows:
        draw.text((14, top + 10), card_id, fill="#ffffff")
        top += label_height
        canvas.paste(image, (0, top))
        top += image.height
    target = workspace / "qa/batch-contact-sheet.jpg"
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target, quality=92)
    return target


def start_previews(
    batch: dict,
    workspace: Path,
    base_port: int,
    approve: bool,
    approved_by: str,
    stop: bool,
) -> list[dict]:
    rows = []
    if approve:
        not_checked = []
        for card in batch["cards"]:
            production = production_path(workspace, card["id"])
            status = load_json(production / "run-status.json")
            if status["stages"]["check"]["status"] != "complete":
                not_checked.append(card["id"])
        if not_checked:
            raise ValueError(f"cannot approve unchecked previews: {not_checked}")
        approval = {
            "schemaVersion": 2,
            "batchId": batch["batch_id"],
            "approvedAt": now_iso(),
            "approvedBy": approved_by,
            "productions": [
                {
                    "id": card["id"],
                    "compositionSha256": production_fingerprint(
                        production_path(workspace, card["id"])
                    ),
                }
                for card in batch["cards"]
            ],
        }
        write_json(approval_path(workspace, batch["batch_id"]), approval)
        for card in batch["cards"]:
            production = production_path(workspace, card["id"])
            update_stage(
                production,
                "preview",
                "complete",
                [approval_path(workspace, batch["batch_id"]).relative_to(workspace).as_posix()],
            )
        return [{"approval": str(approval_path(workspace, batch["batch_id"]))}]

    contact_sheet = None if stop else build_batch_contact_sheet(batch, workspace)
    for index, card in enumerate(batch["cards"]):
        production = production_path(workspace, card["id"])
        status = set_ready_states(production)
        if status["stages"]["preview"]["status"] not in {"ready", "running", "complete"}:
            rows.append({"id": card["id"], "status": "not-ready"})
            continue
        command = [
            "npx",
            "--yes",
            "hyperframes@0.7.70",
            "preview",
            "--background",
            "--no-open",
            "--port",
            str(base_port + index),
        ]
        if stop:
            command = [
                "npx",
                "--yes",
                "hyperframes@0.7.70",
                "preview",
                "--stop",
            ]
        result = run(command, cwd=production)
        url = (
            None
            if stop
            else (
                f"http://localhost:{base_port + index}/"
                f"#project/{production.name}"
            )
        )
        update_stage(
            production,
            "preview",
            "ready" if stop else "running",
            [] if stop else [url],
        )
        rows.append(
            {
                "id": card["id"],
                "status": "stopped" if stop else "running",
                "url": url,
                "contactSheet": None if contact_sheet is None else str(contact_sheet),
                "output": result.stdout.strip(),
            }
        )
    return rows


def approval_valid(batch: dict, workspace: Path) -> bool:
    path = approval_path(workspace, batch["batch_id"])
    if not path.is_file():
        return False
    payload = load_json(path)
    expected = [
        {
            "id": card["id"],
            "compositionSha256": production_fingerprint(
                production_path(workspace, card["id"])
            ),
        }
        for card in batch["cards"]
    ]
    return (
        payload.get("schemaVersion") == 2
        and payload.get("batchId") == batch["batch_id"]
        and payload.get("productions") == expected
    )


def render_one(
    production: Path,
    manual_approved: bool,
    promote_to: Path | None,
) -> dict:
    manifest = load_json(production / "production-manifest.json")
    target = production / manifest["deliverables"]["final"]
    target.parent.mkdir(parents=True, exist_ok=True)
    with production_lock(production):
        status = set_ready_states(production)
        if status["stages"]["render"]["status"] not in {"ready", "complete"}:
            raise ValueError(f"{production.name}: render is not approved and ready")
        if status["stages"]["render"]["status"] != "complete" or not target.is_file():
            update_stage(production, "render", "running")
            try:
                run(
                    [
                        "npx",
                        "--yes",
                        "hyperframes@0.7.70",
                        "render",
                        "--quality",
                        "high",
                        "--fps",
                        "30",
                        "--workers",
                        "2",
                        "--strict",
                        "--no-best-effort",
                        "--output",
                        str(target),
                        ".",
                    ],
                    cwd=production,
                )
                update_stage(
                    production,
                    "render",
                    "complete",
                    [target.relative_to(production).as_posix()],
                )
            except Exception as error:
                update_stage(production, "render", "failed", error=str(error))
                raise
        command = [
            sys.executable,
            str(VERIFY_SCRIPT),
            "render",
            "--production",
            str(production),
            "--video",
            str(target),
        ]
        if manual_approved:
            command.append("--manual-approved")
        if promote_to:
            command.extend(["--promote-to", str(promote_to)])
        run(command, cwd=REPO_ROOT)
    return {
        "id": production.name,
        "video": str(target),
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "manualApproved": manual_approved,
    }


def reset_retry(production: Path, stage: str, asset_id: str | None) -> dict:
    with production_lock(production):
        status_path = production / "run-status.json"
        status = load_json(status_path)
        retry_dependents = {
            "plan": STAGES,
            "visual_generation": [
                "visual_generation",
                "layer_processing",
                "composition",
                "check",
                "preview",
                "render",
                "qa",
            ],
            "audio": [
                "audio",
                "composition",
                "check",
                "preview",
                "render",
                "qa",
            ],
            "layer_processing": [
                "layer_processing",
                "composition",
                "check",
                "preview",
                "render",
                "qa",
            ],
            "composition": ["composition", "check", "preview", "render", "qa"],
            "check": ["check", "preview", "render", "qa"],
            "preview": ["preview", "render", "qa"],
            "render": ["render", "qa"],
            "qa": ["qa"],
        }
        for name in retry_dependents[stage]:
            status["stages"][name] = {"status": "pending", "evidence": [], "updatedAt": now_iso()}
        if stage == "visual_generation":
            queue_path = production / "tmp/imagegen/prompt-queue.jsonl"
            queue = [
                json.loads(line)
                for line in queue_path.read_text(encoding="utf-8").splitlines()
                if line
            ]
            targets = [item for item in queue if asset_id is None or item["assetId"] == asset_id]
            if not targets:
                raise ValueError(f"asset not found: {asset_id}")
            plan = load_json(production / "story-plan.json")
            manifest_path = production / "production-manifest.json"
            manifest = load_json(manifest_path) if manifest_path.is_file() else None
            asset_manifest_path = production / "asset-manifest.json"
            asset_manifest = load_json(asset_manifest_path)
            key_map = {
                "backdrop": "backdropSource",
                "environment-sheet": "environmentSource",
                "character-sheet": "charactersSource",
            }
            for item in targets:
                item["version"] += 1
                item["targetPath"] = re.sub(
                    r"-v\d+(\.[^.]+)$",
                    f"-v{item['version']}\\1",
                    item["targetPath"],
                )
                item["status"] = "pending"
                for payload in [plan, manifest]:
                    if payload is None:
                        continue
                    scene = next(scene for scene in payload["scenes"] if scene["id"] == item["sceneId"])
                    scene["assets"][key_map[item["kind"]]] = item["targetPath"]
                asset_entry = next(
                    asset for asset in asset_manifest["assets"] if asset["id"] == item["assetId"]
                )
                asset_entry["sourcePath"] = item["targetPath"]
                asset_entry["status"] = "pending"
            queue_path.write_text(
                "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in queue),
                encoding="utf-8",
            )
            write_json(production / "story-plan.json", plan)
            write_json(asset_manifest_path, asset_manifest)
            if manifest is not None:
                write_json(manifest_path, manifest)
        write_json(status_path, status)
        refreshed = set_ready_states(production)
    return {
        "id": production.name,
        "stage": stage,
        "status": refreshed["stages"][stage]["status"],
    }


def print_summary(rows: list[dict]) -> None:
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "prepare", "scan", "advance", "retry", "preview", "render", "summary"):
        child = subparsers.add_parser(name)
        child.add_argument("--batch", required=True)
        if name != "validate":
            child.add_argument("--workspace", default=".")
        if name in {"prepare", "advance"}:
            child.add_argument("--workers", type=int, default=4)
        if name == "advance":
            child.add_argument("--audio-provider", choices=["edge", "f5", "silent"])
            child.add_argument("--structural-check", action="store_true")
        if name == "retry":
            child.add_argument("--video", required=True)
            child.add_argument("--stage", choices=STAGES, required=True)
            child.add_argument("--asset-id")
        if name == "preview":
            child.add_argument("--base-port", type=int, default=3101)
            child.add_argument("--approve", action="store_true")
            child.add_argument("--approved-by", default="user")
            child.add_argument("--stop", action="store_true")
        if name == "render":
            child.add_argument("--workers", type=int, default=2)
            child.add_argument("--manual-approved", action="store_true")
            child.add_argument("--promote", action="store_true")
    args = parser.parse_args()
    batch_path = Path(args.batch).resolve()
    batch = load_batch(batch_path)
    if args.command == "validate":
        print_summary(
            {
                "valid": True,
                "batchId": batch["batch_id"],
                "cards": [card["id"] for card in batch["cards"]],
            }
        )
        return
    workspace = Path(args.workspace).resolve()
    if args.command == "prepare":
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [
                executor.submit(prepare_one, batch_path, workspace, card["id"])
                for card in batch["cards"]
            ]
            print_summary([future.result() for future in futures])
    elif args.command in {"scan", "summary"}:
        print_summary(scan_batch(batch, workspace))
    elif args.command == "advance":
        productions = [production_path(workspace, card["id"]) for card in batch["cards"]]
        missing = [path.name for path in productions if not (path / "run-status.json").is_file()]
        if missing:
            raise ValueError(f"prepare these productions first: {missing}")
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [
                executor.submit(
                    advance_one,
                    production,
                    args.audio_provider,
                    args.structural_check,
                )
                for production in productions
            ]
            print_summary([future.result() for future in futures])
    elif args.command == "retry":
        print_summary(
            reset_retry(
                production_path(workspace, args.video),
                args.stage,
                args.asset_id,
            )
        )
    elif args.command == "preview":
        if args.approve and args.stop:
            raise ValueError("--approve and --stop are mutually exclusive")
        print_summary(
            start_previews(
                batch,
                workspace,
                args.base_port,
                args.approve,
                args.approved_by,
                args.stop,
            )
        )
    elif args.command == "render":
        if not approval_valid(batch, workspace):
            raise ValueError(
                "render refused: run preview, obtain explicit user approval, then record it with preview --approve"
            )
        promote_to = workspace / "out/final" if args.promote else None
        productions = [production_path(workspace, card["id"]) for card in batch["cards"]]
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(2, args.workers)) as executor:
            futures = [
                executor.submit(
                    render_one,
                    production,
                    args.manual_approved,
                    promote_to,
                )
                for production in productions
            ]
            print_summary([future.result() for future in futures])


if __name__ == "__main__":
    main()
