"""Calibrate an Ollama judge on the frozen recorded answers from HW8."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import time
from datetime import datetime, timezone
from urllib.request import ProxyHandler, Request, build_opener

from scoring import SYSTEM, VERDICT_SCHEMA, groups, parse_verdict, score

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "evals/sets/l09_labels.jsonl"
RUBRIC = ROOT / "rubrics/rubric.v1.md"
FREEZE = ROOT / "evidence/labels-freeze.json"
PILOT_IDS = [f"HW8-{i:02}" for i in (1, 2, 3, 4, 11, 12, 13, 14, 21, 22, 23, 24)]
OPENER = build_opener(ProxyHandler({}))


def load_frozen():
    freeze = json.loads(FREEZE.read_bytes())
    labels = LABELS.read_bytes()
    rubric = RUBRIC.read_bytes()
    labels_hash = hashlib.sha256(labels).hexdigest()
    if (
        freeze["human_review_confirmed"] is not True
        or labels_hash != freeze["labels_sha256"]
        or hashlib.sha256(rubric).hexdigest() != freeze["rubric_sha256"]
    ):
        raise ValueError("Frozen HW8 labels or rubric do not match the source.")
    cases = [json.loads(line) for line in labels.splitlines() if line.strip()]
    ids = {case["id"] for case in cases}
    for case in cases:
        meta = case["additional_metadata"]
        if (
            meta["rubric_version"] != "rubric.v1"
            or meta["rubric"] != rubric.decode("utf-8")
            or meta["label"] not in {"PASS", "FAIL"}
            or meta["runs"] != 5
        ):
            raise ValueError(f"Unexpected metadata for {case['id']}.")
    if len(cases) != 30 or len(ids) != 30 or not set(PILOT_IDS) <= ids:
        raise ValueError("Expected the 30 frozen cases and all 12 pilot IDs.")
    return cases, labels_hash


def request(base, path, body=None):
    payload = None if body is None else json.dumps(body).encode("utf-8")
    req = Request(base + path, data=payload, headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=180) as response:
        return json.load(response)


def run_attempt(base, model, mode, case):
    question = case["input"]
    answer = case["answer_under_test"]
    rubric = case["additional_metadata"]["rubric"]
    body = {
        "model": model,
        "stream": False,
        "system": SYSTEM,
        "prompt": f"CUSTOMER QUESTION:\n{question}\n\nAGENT ANSWER:\n{answer}\n\nRUBRIC:\n{rubric}\n\nJSON:",
        "options": {"temperature": 0},
    }
    if mode == "schema":
        body["format"] = VERDICT_SCHEMA
    start = time.perf_counter()
    try:
        response = request(base, "/api/generate", body)
    except json.JSONDecodeError as exc:
        response = exc.doc
    result = {
        "elapsed_seconds": time.perf_counter() - start,
        "response": response,
    }
    output = response.get("response") if isinstance(response, dict) else None
    if not isinstance(output, str):
        result["response_error"] = "Expected an Ollama JSON object with a string response."
        return result

    result.update(verdict="MISS", json_object=False)
    try:
        result["json_object"] = isinstance(json.loads(output), dict)
    except ValueError:
        pass
    try:
        result.update(parse_verdict(output, answer))
    except ValueError as exc:
        result["protocol_error"] = str(exc)
    return result


def save_report(path, report):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("set", choices=("l10_one", "l10_pilot", "l09_labels"))
    parser.add_argument("--format", choices=("schema", "none"))
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    mode = args.format or os.environ.get("JUDGE_FORMAT", "schema")
    if mode not in {"schema", "none"}:
        parser.error("JUDGE_FORMAT must be schema or none.")
    if mode == "none" and args.set != "l10_one":
        parser.error("Use schema for calibration.")
    cases, labels_hash = load_frozen()
    if args.set == "l10_one":
        cases = [case for case in cases if case["id"] == "HW8-22"]
    elif args.set == "l10_pilot":
        cases = [case for case in cases if case["id"] in PILOT_IDS]
    repeats = 3 if args.set == "l10_one" else 5
    print(f"{args.set}: {len(cases)} cases × {repeats} attempts", flush=True)
    if args.validate_only:
        return

    configured = os.environ.get("JUDGE_MODEL_OVERRIDE") or os.environ["JUDGE_MODEL"]
    base = os.environ["OLLAMA_URL"].rstrip("/")
    model = configured.removeprefix("ollama:")
    if not configured.startswith("ollama:") or model.endswith(("-cloud", ":cloud")):
        raise ValueError("An explicit local Ollama model is required.")
    if base not in {"http://localhost:11434", "http://host.docker.internal:11434"}:
        raise ValueError("An approved local Ollama endpoint is required.")
    version = request(base, "/api/version")["version"]
    model_info = next((item for item in request(base, "/api/tags")["models"] if item["name"] == model), None)
    if model_info is None or model_info["digest"] != os.environ["OLLAMA_MODEL_DIGEST"]:
        raise ValueError("The local model does not match the pinned digest.")
    if model_info["size"] > 6_000_000_000:
        raise ValueError("The local model exceeds the L10 size limit.")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = ROOT / "reports" / f"calibration-{args.set}-{mode}-{stamp}.json"
    path.parent.mkdir(exist_ok=True)
    report = {
        "set": args.set, "labels_sha256": labels_hash,
        "judge_model": configured, "model_info": model_info, "ollama_version": version,
        "rubric_version": "rubric.v1", "format": mode, "temperature": 0,
        "runs": repeats, "status": "running", "cases": [],
    }
    start = time.perf_counter()
    save_report(path, report)
    active_attempt = None
    try:
        for case in cases:
            meta = case["additional_metadata"]
            outputs = []
            row = {"id": case["id"], "label": meta["label"], "disputed": meta["disputed"], "outputs": outputs}
            report["cases"].append(row)
            for attempt_number in range(1, repeats + 1):
                active_attempt = {"case_id": case["id"], "attempt_number": attempt_number}
                attempt = run_attempt(base, model, mode, case)
                outputs.append(attempt)
                if "response_error" in attempt:
                    raise ValueError(attempt["response_error"])
                save_report(path, report)
                print(f"{case['id']} {attempt_number}/{repeats}: {attempt['verdict']} ({attempt['elapsed_seconds']:.2f}s)", flush=True)
            if repeats == 5:
                row.update(score(row["label"], outputs))
            save_report(path, report)
    except (OSError, ValueError, KeyError) as exc:
        report.update(status="error", error=str(exc), failed_attempt=active_attempt)
        save_report(path, report)
        raise

    times = [output["elapsed_seconds"] for row in report["cases"] for output in row["outputs"]]
    elapsed = time.perf_counter() - start
    report.update(status="complete", elapsed=elapsed, t_call_mean=elapsed / len(times),
                  request_median_seconds=statistics.median(times))
    if repeats == 5:
        report["groups"] = groups(report["cases"])
    save_report(path, report)
    print(path.relative_to(ROOT), flush=True)


if __name__ == "__main__":
    main()
