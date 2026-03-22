#!/usr/bin/env python3
"""E2E tests for MDR protocol.

Tests the full decision-making flow by running Claude Code headlessly
against a synthetic test project with the MDR plugin installed locally.

Requirements:
- Claude Code CLI installed and authenticated
- Sufficient API budget (~$2-5 per full run on sonnet, sub-agents use haiku)

Usage:
    python3 tests/micro-decisions/e2e/test_mdr_protocol.py
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "plugins" / "micro-decisions"
ARTIFACT_DIR = Path(__file__).resolve().parent / "test-artifacts"
TIMEOUT_SECONDS = 180
MAX_BUDGET_USD = 1.00

# Shared fixture content — reused across multiple tests
ERROR_FORMAT_FIXTURE = """\
# Error response format for REST APIs

## Decision
Use RFC 7807 Problem Details format for all API error responses.
Return JSON with fields: type, title, status, detail.

## Why
Industry standard, supported by most frameworks, provides consistent structure.

## Rejected alternatives

### Custom error envelope
Requires documentation, not interoperable with standard tooling.

### Plain text errors
No structure, hard to parse programmatically.
"""

# Tools the main agent and sub-agents need
ALLOWED_TOOLS = [
    "Read",
    "Write",
    "Edit",
    "Grep",
    "Glob",
    "Agent",
]


class TestProject:
    """Manages a temporary test project with MDR installed locally."""

    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="mdr-e2e-"))
        self._setup()

    def _setup(self):
        """Create project structure as if mdr-init was run."""
        # Directories
        (self.root / ".claude" / "mdr").mkdir(parents=True)
        (self.root / ".claude" / "agents").mkdir(parents=True)
        (self.root / ".claude" / "rules").mkdir(parents=True)
        (self.root / ".mdr" / "decisions").mkdir(parents=True)
        (self.root / "src").mkdir(parents=True)
        (self.root / "tests").mkdir(parents=True)

        # Copy MDR infrastructure
        shutil.copy(PLUGIN_ROOT / "agents" / "mdr-check.md", self.root / ".claude" / "agents" / "mdr-check.md")
        shutil.copy(PLUGIN_ROOT / "agents" / "mdr-save.md", self.root / ".claude" / "agents" / "mdr-save.md")
        shutil.copy(PLUGIN_ROOT / "rules" / "mdr-protocol.md", self.root / ".claude" / "rules" / "mdr-protocol.md")
        shutil.copy(PLUGIN_ROOT / "hooks" / "mdr-remind.sh", self.root / ".claude" / "mdr" / "mdr-remind.sh")
        os.chmod(self.root / ".claude" / "mdr" / "mdr-remind.sh", 0o755)

        settings = {
            "hooks": {
                "UserPromptSubmit": [
                    {"hooks": [{"type": "command", "command": ".claude/mdr/mdr-remind.sh"}]}
                ],
                "SubagentStart": [
                    {"hooks": [{"type": "command", "command": ".claude/mdr/mdr-remind.sh"}]}
                ],
            }
        }
        (self.root / ".claude" / "settings.json").write_text(json.dumps(settings, indent=2))

        # Add competing agents to test MDR resilience
        self._create_competing_agents()

        # Create realistic project code
        self._create_project_code()

        # Init git repo (claude requires it)
        subprocess.run(["git", "init"], cwd=self.root, capture_output=True, check=True)
        subprocess.run(["git", "add", "-A"], cwd=self.root, capture_output=True, check=True)
        subprocess.run(
            ["git", "-c", "user.name=mdr-test", "-c", "user.email=mdr-test@test",
             "commit", "-m", "init"],
            cwd=self.root, capture_output=True, check=True,
        )

    def _create_competing_agents(self):
        """Install competing agents that could distract from MDR protocol."""
        # project-notes: similar to mdr-save but writes to a different location
        (self.root / ".claude" / "agents" / "project-notes.md").write_text("""\
---
name: project-notes
description: Saves project notes, meeting summaries, and general knowledge to notes/ directory.
tools: Read, Write, Glob
model: haiku
background: true
---

You save project notes to the `notes/` directory.

Use this agent for meeting notes, onboarding docs, general knowledge,
and anything that is NOT a decision between alternatives.

## Steps

1. Generate a short kebab-case filename from the topic.
2. Write the note to `notes/<filename>.md` using markdown.
3. Report: Saved note: **<topic>** → `notes/<filename>.md`
""")

        # tech-radar: recommends technologies, could compete with decision-making
        (self.root / ".claude" / "agents" / "tech-radar.md").write_text("""\
---
name: tech-radar
description: Recommends technologies based on project context. Analyzes tech stack and suggests improvements.
tools: Read, Grep, Glob
model: haiku
---

You are a technology advisor. When asked about technology choices,
analyze the project's existing stack and recommend options.

## Steps

1. Scan the project for existing dependencies and patterns.
2. Based on the project context, suggest 2-3 technologies.
3. For each option, provide a brief summary of pros/cons.
4. Let the user make the final choice.

## Important

You only provide recommendations. You do NOT record decisions —
that is handled by the MDR protocol.
""")

        # Also add notes/ dir so it exists
        (self.root / "notes").mkdir(parents=True)

    def _create_project_code(self):
        """Create a realistic Python API project with code that needs decisions."""
        (self.root / "src" / "__init__.py").write_text("")

        (self.root / "src" / "app.py").write_text("""\
from http.server import HTTPServer, BaseHTTPRequestHandler
import json


class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self._json_response(200, {"status": "ok"})
        elif self.path.startswith("/users/"):
            user_id = self.path.split("/")[-1]
            self._get_user(user_id)
        else:
            self._json_response(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/users":
            body = self._read_body()
            self._create_user(body)
        else:
            self._json_response(404, {"error": "not found"})

    def _get_user(self, user_id):
        # TODO: implement user lookup
        self._json_response(200, {"id": user_id, "name": "placeholder"})

    def _create_user(self, data):
        # TODO: validate input and handle errors
        self._json_response(201, {"id": "new", "name": data.get("name", "")})

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def _json_response(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


def create_app(port=8080):
    return HTTPServer(("", port), APIHandler)
""")

        (self.root / "src" / "external_api.py").write_text("""\
import urllib.request
import json


class PaymentGateway:
    \"\"\"Client for external payment processing API.\"\"\"

    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key

    def charge(self, amount, currency, customer_id):
        \"\"\"Charge a customer. May fail due to network issues.\"\"\"
        data = json.dumps({
            "amount": amount,
            "currency": currency,
            "customer_id": customer_id,
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/charges",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        # TODO: no retry logic, no error handling
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())

    def refund(self, charge_id):
        \"\"\"Refund a charge. May fail due to network issues.\"\"\"
        req = urllib.request.Request(
            f"{self.base_url}/refunds",
            data=json.dumps({"charge_id": charge_id}).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        # TODO: no retry logic, no error handling
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
""")

        (self.root / "src" / "config.py").write_text("""\
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///app.db")
API_KEY = os.environ.get("API_KEY", "")
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
# TODO: no logging configured
""")

        (self.root / "tests" / "__init__.py").write_text("")
        (self.root / "tests" / "test_app.py").write_text("""\
import unittest
from src.app import APIHandler


class TestHealthEndpoint(unittest.TestCase):
    def test_placeholder(self):
        # TODO: need to decide on test approach
        self.assertTrue(True)
""")

        (self.root / "README.md").write_text("""\
# Test API Project

Simple REST API for user management with external payment processing.

## Structure
- `src/app.py` — HTTP server and request handling
- `src/external_api.py` — Payment gateway client
- `src/config.py` — Configuration from environment
- `tests/` — Test suite
""")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False

    def reset(self):
        """Reset project to initial state (after _setup)."""
        r1 = subprocess.run(["git", "checkout", "."], cwd=self.root, capture_output=True)
        if r1.returncode != 0:
            raise RuntimeError(f"git checkout failed: {r1.stderr.decode()}")
        r2 = subprocess.run(["git", "clean", "-fd", "--exclude=.mdr/decisions/"], cwd=self.root, capture_output=True)
        if r2.returncode != 0:
            raise RuntimeError(f"git clean failed: {r2.stderr.decode()}")
        # Ensure decisions directory exists (git doesn't track empty dirs)
        (self.root / ".mdr" / "decisions").mkdir(parents=True, exist_ok=True)
        # Remove any decision files added by tests
        for f in (self.root / ".mdr" / "decisions").glob("*.md"):
            f.unlink()

    def add_fixture_decision(self, filename: str, content: str):
        """Add a pre-existing decision file."""
        (self.root / ".mdr" / "decisions" / filename).write_text(content)

    def snapshot_file(self, relpath: str) -> str:
        """Read and return file content for later comparison."""
        return (self.root / relpath).read_text()

    def decision_files(self) -> list[str]:
        """List all decision files."""
        return sorted(f.name for f in (self.root / ".mdr" / "decisions").glob("*.md"))

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


# Module-level observability state
_cumulative_cost_usd: float = 0.0
_last_trace: "EventTrace | None" = None


@dataclass
class EventTrace:
    """Structured view of a Claude stream-json session."""

    events: list[dict] = field(default_factory=list)
    result_event: dict = field(default_factory=dict)

    @property
    def result(self) -> str:
        return self.result_event.get("result", "")

    @property
    def session_id(self) -> str | None:
        return self.result_event.get("session_id")

    @property
    def cost_usd(self) -> float:
        return self.result_event.get("total_cost_usd", 0)

    @property
    def num_turns(self) -> int:
        return self.result_event.get("num_turns", 0)

    def tool_calls(self, name: str = None) -> list[dict]:
        """Extract tool_use blocks from assistant messages."""
        calls = []
        for ev in self.events:
            if ev.get("type") != "assistant":
                continue
            for block in ev.get("message", {}).get("content", []):
                if block.get("type") != "tool_use":
                    continue
                if name is None or block.get("name") == name:
                    calls.append(block)
        return calls

    def has_tool_call(self, name: str, pattern: str = None) -> bool:
        """Check if a tool was called, optionally matching a regex pattern."""
        for call in self.tool_calls(name):
            if pattern is None:
                return True
            inp = call.get("input", {})
            # For Bash: match against command
            if name == "Bash" and re.search(pattern, inp.get("command", ""), re.IGNORECASE):
                return True
            # For Agent: match against prompt or description
            if name == "Agent":
                text = f"{inp.get('prompt', '')} {inp.get('description', '')}"
                if re.search(pattern, text, re.IGNORECASE):
                    return True
            # Generic: match against str(input)
            if re.search(pattern, str(inp), re.IGNORECASE):
                return True
        return False

    def subagent_dispatched(self, name: str) -> bool:
        """Check if an Agent tool_use mentions the given agent name."""
        return self.has_tool_call("Agent", pattern=re.escape(name))

    @property
    def all_text(self) -> str:
        """All text from assistant messages and result, for keyword matching."""
        parts = []
        for ev in self.events:
            if ev.get("type") != "assistant":
                continue
            for block in ev.get("message", {}).get("content", []):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
        if self.result:
            parts.append(self.result)
        return "\n".join(parts)

    def _validate_parse(self):
        """Warn if no assistant events found — dispatch assertions won't work."""
        has_assistant = any(ev.get("type") == "assistant" for ev in self.events)
        if not has_assistant:
            print("  WARN: No assistant-type events in trace — dispatch assertions unreliable")

    def dump(self, path: Path):
        """Write all events as JSONL for debugging."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            for ev in self.events:
                f.write(json.dumps(ev) + "\n")
            if self.result_event:
                f.write(json.dumps(self.result_event) + "\n")


def run_claude(cwd: str, prompt: str, resume: str = None, persist: bool = False, model: str = "claude-sonnet-4-6") -> EventTrace:
    """Run claude -p with stream-json and return an EventTrace.

    Uses stream-json output to observe all events including background agent
    completion. Returns an EventTrace with structured access to results,
    tool calls, and session metadata.
    """
    global _cumulative_cost_usd, _last_trace

    if resume is not None and not resume:
        raise ValueError("resume must be a non-empty session_id or None")

    cmd = [
        "claude", "-p", prompt,
        "--output-format", "stream-json",
        "--verbose",
        "--model", model,
        "--max-budget-usd", str(MAX_BUDGET_USD),
        "--allowedTools", *ALLOWED_TOOLS,
    ]
    if not persist:
        cmd.append("--no-session-persistence")
    if resume:
        cmd.extend(["--resume", resume])

    env = os.environ.copy()
    env.pop("CLAUDECODE", None)  # Allow nested session

    proc = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        env=env,
    )

    if proc.returncode != 0 and not proc.stdout:
        raise RuntimeError(f"claude failed: {proc.stderr}")

    # Parse stream-json: each line is a JSON event
    all_events = []
    result_event = None

    for line in proc.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        all_events.append(event)

        if event.get("type") == "result":
            result_event = event

    if not result_event:
        raise RuntimeError(f"No result event in stream output. stderr: {proc.stderr}")

    trace = EventTrace(events=all_events, result_event=result_event)
    trace._validate_parse()
    _cumulative_cost_usd += trace.cost_usd
    _last_trace = trace

    return trace


def test_check_finds_existing_decision(project: TestProject) -> bool:
    """Scenario 1: Task triggers mdr-check, finds existing decision, applies it."""
    print("\n=== Test: CHECK finds existing decision ===")

    # Add fixture
    project.add_fixture_decision("error-response-format.md", ERROR_FORMAT_FIXTURE)

    trace = run_claude(
        cwd=str(project.root),
        prompt=(
            "I need to implement error handling for a new REST API endpoint. "
            "What format should I use for error responses?"
        ),
    )

    print(f"  Cost: ${trace.cost_usd:.4f}")
    print(f"  Turns: {trace.num_turns}")

    # Primary assertion: mdr-check agent was dispatched
    dispatched = trace.subagent_dispatched("mdr-check")
    if dispatched:
        print("  OK: mdr-check agent dispatched")
    else:
        print("  WARN: mdr-check agent not detected in tool calls")

    # Secondary assertion: response mentions the existing decision
    keywords = ["rfc 7807", "problem details", "error-response-format"]
    found = any(kw in trace.all_text.lower() for kw in keywords)

    if found:
        print("  PASS: Found existing decision about RFC 7807")
    else:
        print(f"  FAIL: Response doesn't mention existing decision")
        print(f"  Response preview: {trace.all_text[:300]}")

    return dispatched and found


def test_save_new_decision(project: TestProject) -> bool:
    """Scenario 2: Task triggers mdr-check, nothing found, user confirms, mdr-save creates file."""
    print("\n=== Test: SAVE new decision (multi-turn) ===")

    files_before = project.decision_files()

    # Turn 1: Give a task about something with no existing MDR
    print("  Turn 1: Asking about logging library...")
    trace1 = run_claude(
        cwd=str(project.root),
        prompt=(
            "I need to choose a logging library for our Python project. "
            "What would you recommend?"
        ),
        persist=True,
    )

    session_id = trace1.session_id
    print(f"  Cost (turn 1): ${trace1.cost_usd:.4f}")
    print(f"  Turns (turn 1): {trace1.num_turns}")

    if not session_id:
        print("  FAIL: No session_id returned")
        return False

    # Turn 2: User confirms a choice
    print("  Turn 2: Confirming choice...")
    trace2 = run_claude(
        cwd=str(project.root),
        prompt=(
            "I choose structlog."
        ),
        resume=session_id,
        persist=True,
    )

    print(f"  Cost (turn 2): ${trace2.cost_usd:.4f}")
    print(f"  Turns (turn 2): {trace2.num_turns}")

    # Primary assertion: mdr-save agent was dispatched in turn 2
    dispatched = trace2.subagent_dispatched("mdr-save")
    if dispatched:
        print("  OK: mdr-save agent dispatched in turn 2")
    else:
        print("  FAIL: mdr-save agent not detected in turn 2 tool calls")

    # Verify: new decision file should exist
    files_after = project.decision_files()
    new_files = set(files_after) - set(files_before)

    if new_files:
        print(f"  PASS: New decision file(s) created: {new_files}")
        # Verify content
        for f in new_files:
            content = (project.root / ".mdr" / "decisions" / f).read_text()
            if "structlog" in content.lower():
                print(f"  PASS: Decision file contains 'structlog'")
            else:
                print(f"  WARN: Decision file doesn't mention 'structlog'")
                print(f"  Content preview: {content[:200]}")
        file_created = True
    else:
        print("  FAIL: No new decision file created")
        print(f"  Files before: {files_before}")
        print(f"  Files after: {files_after}")
        print(f"  Response preview: {trace2.result[:300]}")
        file_created = False

    return file_created and dispatched


def test_update_existing_decision(project: TestProject) -> bool:
    """Scenario 3: Existing decision found, user changes approach, mdr-save updates the file."""
    print("\n=== Test: UPDATE existing decision ===")

    # Add fixture — old decision about retry strategy
    fixture_file = "retry-strategy.md"
    project.add_fixture_decision(fixture_file, """\
# Retry strategy for external API calls

## Decision
Use exponential backoff with 3 retries and jitter.

## Why
Prevents thundering herd, gives transient errors time to recover.

## Rejected alternatives

### Fixed delay retries
Can cause synchronized retry storms across instances.

### No retries
Too fragile for unreliable external services.
""")

    content_before = (project.root / ".mdr" / "decisions" / fixture_file).read_text()

    # Single turn: user says they want to change the retry strategy
    print("  Asking to change retry strategy...")
    trace = run_claude(
        cwd=str(project.root),
        prompt=(
            "We've decided to change our retry strategy. Instead of exponential backoff, "
            "we'll use circuit breaker pattern with tenacity library. "
            "Exponential backoff alone doesn't prevent cascading failures."
        ),
    )

    print(f"  Cost: ${trace.cost_usd:.4f}")
    print(f"  Turns: {trace.num_turns}")

    # Primary assertion: both mdr-check and mdr-save dispatched
    if trace.subagent_dispatched("mdr-check"):
        print("  OK: mdr-check agent dispatched")
    else:
        print("  WARN: mdr-check agent not detected in tool calls")
    if trace.subagent_dispatched("mdr-save"):
        print("  OK: mdr-save agent dispatched")
    else:
        print("  WARN: mdr-save agent not detected in tool calls")

    # Verify: the existing file should be updated (content changed)
    content_after = (project.root / ".mdr" / "decisions" / fixture_file).read_text()
    changed = content_after != content_before
    mentions_circuit_breaker = "circuit breaker" in content_after.lower()

    save_dispatched = trace.subagent_dispatched("mdr-save")
    if save_dispatched:
        print("  OK: mdr-save agent dispatched")
    else:
        print("  WARN: mdr-save agent not detected in tool calls")

    if changed and mentions_circuit_breaker:
        print("  PASS: Existing decision file updated with circuit breaker")
    elif changed:
        print("  PARTIAL: File changed but doesn't mention circuit breaker")
        print(f"  Content preview: {content_after[:300]}")
    else:
        # Maybe it created a new file instead of updating
        new_files = set(project.decision_files()) - {"error-response-format.md", fixture_file}
        if new_files:
            new_content = (project.root / ".mdr" / "decisions" / list(new_files)[0]).read_text()
            if "circuit breaker" in new_content.lower():
                print(f"  PASS: New decision file created (supersedes old): {new_files}")
                return save_dispatched
        print("  FAIL: Decision not updated and no new file created")
        print(f"  Response preview: {trace.result[:300]}")
        return False

    return save_dispatched


def test_user_rejection(project: TestProject) -> bool:
    """Scenario 4: User rejects agent's suggestion — this is a new decision to save."""
    print("\n=== Test: User REJECTION saves decision ===")

    files_before = project.decision_files()

    # Multi-turn: agent proposes something, user rejects
    print("  Turn 1: Asking about database choice...")
    trace1 = run_claude(
        cwd=str(project.root),
        prompt=(
            "I need to choose a database for our new microservice that stores user sessions. "
            "What are the options?"
        ),
        persist=True,
    )

    session_id = trace1.session_id
    print(f"  Cost (turn 1): ${trace1.cost_usd:.4f}")
    print(f"  Turns (turn 1): {trace1.num_turns}")

    if not session_id:
        print("  FAIL: No session_id returned")
        return False

    # Turn 2: User rejects whatever was proposed and states their preference
    print("  Turn 2: Rejecting proposal, choosing Redis...")
    trace2 = run_claude(
        cwd=str(project.root),
        prompt=(
            "No, I don't want any of those. We'll use Redis for session storage. "
            "It's fast, supports TTL natively, and we already run it for caching."
        ),
        resume=session_id,
        persist=True,
    )

    print(f"  Cost (turn 2): ${trace2.cost_usd:.4f}")
    print(f"  Turns (turn 2): {trace2.num_turns}")

    # Verify: new decision file about Redis/sessions should exist
    files_after = project.decision_files()
    new_files = set(files_after) - set(files_before)

    if new_files:
        found_redis = False
        for f in new_files:
            content = (project.root / ".mdr" / "decisions" / f).read_text()
            if "redis" in content.lower():
                found_redis = True
                print(f"  PASS: New decision file with Redis: {f}")
                break
        if not found_redis:
            print(f"  FAIL: New file(s) created but no mention of Redis: {new_files}")
        return found_redis
    else:
        print("  FAIL: No new decision file created after rejection")
        print(f"  Response preview: {trace2.result[:300]}")
        return False


###############################################################################
# Corner case tests — protocol boundary conditions
###############################################################################


def test_question_does_not_trigger_save(project: TestProject) -> bool:
    """Corner case: a question with no decision should NOT create an MDR.

    Protocol says: "When NOT to start the protocol: User asks a question (no decision involved)"
    """
    print("\n=== Test (corner): Question does NOT trigger SAVE ===")

    files_before = project.decision_files()

    trace = run_claude(
        cwd=str(project.root),
        prompt=(
            "Explain how the _json_response method works in src/app.py. "
            "What HTTP headers does it set?"
        ),
    )

    print(f"  Cost: ${trace.cost_usd:.4f}")
    print(f"  Turns: {trace.num_turns}")

    # Primary assertion: mdr-save should NOT be dispatched
    save_dispatched = trace.subagent_dispatched("mdr-save")
    if save_dispatched:
        print("  WARN: mdr-save agent was dispatched for a question")

    files_after = project.decision_files()
    new_files = set(files_after) - set(files_before)

    if save_dispatched and new_files:
        print(f"  FAIL: mdr-save dispatched AND file created for a question: {new_files}")
        return False
    elif not new_files:
        print("  PASS: No MDR created for a simple question")
        return True
    else:
        print(f"  FAIL: MDR created for a question (should not happen): {new_files}")
        return False


def test_two_decisions_one_session(project: TestProject) -> bool:
    """Corner case: two distinct decisions in one session, both should be saved."""
    print("\n=== Test (corner): Two decisions in one session ===")

    files_before = project.decision_files()

    # Turn 1: first decision topic
    print("  Turn 1: First decision — date format...")
    trace1 = run_claude(
        cwd=str(project.root),
        prompt=(
            "I need to pick a date format for our API responses. "
            "What are the options?"
        ),
        persist=True,
    )
    session_id = trace1.session_id
    print(f"  Cost (turn 1): ${trace1.cost_usd:.4f}")

    if not session_id:
        print("  FAIL: No session_id")
        return False

    # Turn 2: confirm first decision
    print("  Turn 2: Confirming ISO 8601...")
    trace2 = run_claude(
        cwd=str(project.root),
        prompt="Use ISO 8601 with UTC timezone.",
        resume=session_id,
        persist=True,
    )
    print(f"  Cost (turn 2): ${trace2.cost_usd:.4f}")

    files_after_first = project.decision_files()
    first_new = set(files_after_first) - set(files_before)
    if first_new:
        print(f"  OK: First decision saved: {first_new}")
    else:
        print("  WARN: First decision may not have been saved yet (background)")

    # Turn 3: second decision topic — same session
    print("  Turn 3: Second decision — pagination style...")
    trace3 = run_claude(
        cwd=str(project.root),
        prompt=(
            "Now another question: how should we implement pagination in the GET /users endpoint? "
            "What are the common approaches?"
        ),
        resume=session_id,
        persist=True,
    )
    print(f"  Cost (turn 3): ${trace3.cost_usd:.4f}")

    # Turn 4: confirm second decision
    print("  Turn 4: Confirming cursor-based pagination...")
    trace4 = run_claude(
        cwd=str(project.root),
        prompt="Use cursor-based pagination.",
        resume=session_id,
        persist=True,
    )
    print(f"  Cost (turn 4): ${trace4.cost_usd:.4f}")

    files_after_both = project.decision_files()
    all_new = set(files_after_both) - set(files_before)

    if len(all_new) >= 2:
        print(f"  PASS: Both decisions saved: {all_new}")
        return True
    elif len(all_new) == 1:
        print(f"  PARTIAL: Only one decision saved: {all_new}")
        return False
    else:
        print("  FAIL: No decisions saved")
        return False


def test_partial_match_not_blindly_applied(project: TestProject) -> bool:
    """Corner case: existing MDR about error FORMAT, but task is about error CODES.

    Agent should check MDR, find the partial match, but recognize it doesn't
    fully answer the new question and still present options.
    """
    print("\n=== Test (corner): Partial MDR match — not blindly applied ===")

    # Existing MDR about error response FORMAT
    project.add_fixture_decision("error-response-format.md", ERROR_FORMAT_FIXTURE)

    # Task is about HTTP status CODES, not format — related but different
    trace = run_claude(
        cwd=str(project.root),
        prompt=(
            "What HTTP status codes should we use for different error types "
            "in our API? For example: validation errors, not found, auth failures, "
            "server errors. Should we use 422 or 400 for validation?"
        ),
        persist=True,
    )

    print(f"  Cost: ${trace.cost_usd:.4f}")
    print(f"  Turns: {trace.num_turns}")

    # The agent should either:
    # a) Present options (422 vs 400) since the existing MDR is about format, not codes
    # b) Reference the existing MDR as context but still ask about the new question
    all_text_lower = trace.all_text.lower()
    proposed_options = any(
        kw in all_text_lower
        for kw in ["422", "400", "option", "approach", "alternative"]
    )

    if proposed_options:
        print("  PASS: Agent presented options for status codes (not blindly applied format MDR)")
        return True
    else:
        # Check if it just applied the format MDR and moved on without addressing codes
        if "rfc 7807" in all_text_lower and "422" not in all_text_lower and "400" not in all_text_lower:
            print("  FAIL: Agent blindly applied format MDR without addressing status code question")
            return False
        print(f"  FAIL: Response doesn't clearly show alternatives")
        print(f"  Response preview: {trace.all_text[:300]}")
        return False


###############################################################################
# Realistic tests — coding tasks with actual project code, no MDR hints
###############################################################################


def test_realistic_applies_existing_decision(project: TestProject) -> bool:
    """Realistic: coding task that should trigger mdr-check and find existing decision.

    The project has error-response-format MDR. The task is to add error handling
    to the API — agent should automatically check MDR and apply RFC 7807.
    No mention of MDR, decisions, or checking in the prompt.
    """
    print("\n=== Test (realistic): Coding task applies existing MDR ===")

    # Fixture: existing decision about error format
    project.add_fixture_decision("error-response-format.md", ERROR_FORMAT_FIXTURE)

    app_before = project.snapshot_file("src/app.py")

    trace = run_claude(
        cwd=str(project.root),
        prompt=(
            "Add proper error handling to the POST /users endpoint in src/app.py. "
            "Handle missing name field, invalid JSON. "
            "What format should the error responses use?"
        ),
    )

    print(f"  Cost: ${trace.cost_usd:.4f}")
    print(f"  Turns: {trace.num_turns}")

    # Primary assertion: mdr-check agent was dispatched
    dispatched = trace.subagent_dispatched("mdr-check")
    if dispatched:
        print("  OK: mdr-check agent dispatched")
    else:
        print("  WARN: mdr-check agent not detected in tool calls")

    # Alternative: model may read MDR files directly instead of via subagent
    read_mdr = trace.has_tool_call("Read", pattern=r"\.mdr/decisions/")
    grep_mdr = trace.has_tool_call("Grep", pattern=r"\.mdr/decisions/")
    checked_mdr = dispatched or read_mdr or grep_mdr
    if not dispatched and (read_mdr or grep_mdr):
        print("  OK: MDR files read directly (not via mdr-check subagent)")

    # Check if the code was actually modified
    app_after = project.snapshot_file("src/app.py")
    code_changed = app_after != app_before

    if not code_changed:
        print("  FAIL: Code was not modified")
        print(f"  Response preview: {trace.all_text[:300]}")
        return False

    # Check the actual code for RFC 7807 patterns (type/title/status/detail fields)
    code_lower = app_after.lower()
    rfc7807_fields = ["\"type\"", "\"title\"", "\"status\"", "\"detail\""]
    code_field_matches = sum(1 for f in rfc7807_fields if f in code_lower)
    code_has_rfc7807 = code_field_matches >= 3

    # Also check response text for explicit mentions
    all_text_lower = trace.all_text.lower()
    response_mentions = "rfc 7807" in all_text_lower or "problem details" in all_text_lower

    if code_has_rfc7807:
        print(f"  PASS: Code uses RFC 7807 pattern ({code_field_matches}/4 fields found)")
    elif checked_mdr and code_changed:
        print(f"  PASS: MDR checked and code updated ({code_field_matches}/4 RFC 7807 fields)")
    elif response_mentions:
        print(f"  PASS: Response references RFC 7807")
    else:
        print(f"  FAIL: Code changed but no RFC 7807 pattern ({code_field_matches}/4 fields)")
        print(f"  Response preview: {trace.all_text[:300]}")
        return False

    return True


def test_realistic_saves_new_decision(project: TestProject) -> bool:
    """Realistic: coding task requires a choice, no existing MDR, agent should save.

    Task: add retry logic to external_api.py. No existing MDR about retries.
    Agent should present options, then user confirms, and decision gets saved.
    No mention of MDR in the prompt.
    """
    print("\n=== Test (realistic): Coding task saves new MDR ===")

    files_before = project.decision_files()

    # Turn 1: Pure coding task — no MDR hints
    print("  Turn 1: Asking to add retry logic...")
    trace1 = run_claude(
        cwd=str(project.root),
        prompt=(
            "The PaymentGateway in src/external_api.py has no retry logic. "
            "Network calls to the payment API sometimes fail transiently. "
            "I need to add retry handling. Don't write code yet — "
            "just tell me what approach you'd recommend."
        ),
        persist=True,
    )

    session_id = trace1.session_id
    print(f"  Cost (turn 1): ${trace1.cost_usd:.4f}")
    print(f"  Turns (turn 1): {trace1.num_turns}")

    if not session_id:
        print("  FAIL: No session_id returned")
        return False

    # Check if agent proposed alternatives (protocol requires >=2 approaches)
    proposed_options = any(
        kw in trace1.result.lower()
        for kw in ["option", "approach", "alternative", "1.", "2."]
    )
    if proposed_options:
        print("  OK: Agent proposed alternatives as protocol requires")
    else:
        print("  WARN: Agent may not have proposed alternatives")

    # Turn 2: User picks an approach (like a real conversation)
    print("  Turn 2: Confirming retry approach...")
    trace2 = run_claude(
        cwd=str(project.root),
        prompt=(
            "Let's go with simple exponential backoff, 3 retries, no external libraries. "
            "Implement it."
        ),
        resume=session_id,
        persist=True,
    )

    print(f"  Cost (turn 2): ${trace2.cost_usd:.4f}")
    print(f"  Turns (turn 2): {trace2.num_turns}")

    # Primary assertion: mdr-save agent was dispatched in turn 2
    if trace2.subagent_dispatched("mdr-save"):
        print("  OK: mdr-save agent dispatched in turn 2")
    else:
        print("  WARN: mdr-save agent not detected in turn 2 tool calls")

    # Verify: new MDR file about retry strategy should exist
    files_after = project.decision_files()
    new_files = set(files_after) - set(files_before)

    if new_files:
        found_retry = False
        for f in new_files:
            content = (project.root / ".mdr" / "decisions" / f).read_text()
            if "retry" in content.lower() or "backoff" in content.lower():
                found_retry = True
                print(f"  PASS: New MDR about retry strategy: {f}")
                break
        if not found_retry:
            print(f"  FAIL: New file(s) created but no mention of retry/backoff: {new_files}")
        return found_retry
    else:
        print("  FAIL: No new MDR file created after confirmed decision")
        print(f"  Response preview: {trace2.result[:300]}")
        return False


###############################################################################
# New corner case tests — edge conditions and duplicate handling
###############################################################################


def test_missing_decisions_directory(project: TestProject) -> bool:
    """Corner case: .mdr/decisions/ directory does not exist.

    mdr-check should return a clear message, not crash.
    """
    print("\n=== Test (corner): Missing decisions directory ===")

    # Remove the decisions directory
    decisions_dir = project.root / ".mdr" / "decisions"
    if decisions_dir.exists():
        shutil.rmtree(decisions_dir)

    trace = run_claude(
        cwd=str(project.root),
        prompt=(
            "I need to choose an HTTP client library for our Python project. "
            "What are the options?"
        ),
    )

    print(f"  Cost: ${trace.cost_usd:.4f}")
    print(f"  Turns: {trace.num_turns}")

    # Should not crash — check that we got a result
    if not trace.result:
        print("  FAIL: No result returned (possible crash)")
        return False

    # mdr-check should have been dispatched and handled gracefully
    dispatched = trace.subagent_dispatched("mdr-check")
    if dispatched:
        print("  OK: mdr-check agent dispatched")
    else:
        print("  WARN: mdr-check agent not detected in tool calls")

    # The response should still be useful (not an error dump)
    has_options = any(
        kw in trace.result.lower()
        for kw in ["http", "requests", "httpx", "urllib", "aiohttp", "option", "recommend"]
    )
    if has_options:
        print("  PASS: Agent responded usefully despite missing directory")
        return True
    else:
        print(f"  FAIL: Response doesn't seem useful")
        print(f"  Response preview: {trace.result[:300]}")
        return False


def test_refinement_updates_existing(project: TestProject) -> bool:
    """Corner case: refining an existing decision should update, not create new file.

    Fixture: existing MDR about retry strategy. User confirms adding jitter.
    The existing file should be expanded, not a new file created.
    """
    print("\n=== Test (corner): Refinement updates existing MDR ===")

    fixture_file = "retry-strategy.md"
    project.add_fixture_decision(fixture_file, """\
# Retry strategy for external API calls

## Decision
Use exponential backoff with 3 retries.

## Why
Prevents thundering herd, gives transient errors time to recover.

## Rejected alternatives

### Fixed delay retries
Can cause synchronized retry storms across instances.

### No retries
Too fragile for unreliable external services.
""")

    content_before = (project.root / ".mdr" / "decisions" / fixture_file).read_text()
    files_before = project.decision_files()

    # Turn 1: Ask about adding jitter to retries
    print("  Turn 1: Asking about retry jitter...")
    trace1 = run_claude(
        cwd=str(project.root),
        prompt=(
            "Should we add jitter to our exponential backoff retry logic?"
        ),
        persist=True,
    )
    session_id = trace1.session_id
    print(f"  Cost (turn 1): ${trace1.cost_usd:.4f}")

    if not session_id:
        print("  FAIL: No session_id returned")
        return False

    # Turn 2: Confirm jitter — refinement of existing retry decision
    print("  Turn 2: Confirming jitter...")
    trace2 = run_claude(
        cwd=str(project.root),
        prompt="Yes, add jitter.",
        resume=session_id,
        persist=True,
    )
    print(f"  Cost (turn 2): ${trace2.cost_usd:.4f}")

    content_after = (project.root / ".mdr" / "decisions" / fixture_file).read_text()
    files_after = project.decision_files()
    new_files = set(files_after) - set(files_before)

    updated = content_after != content_before
    mentions_jitter = "jitter" in content_after.lower()

    if updated and mentions_jitter:
        print(f"  PASS: Existing MDR updated with jitter detail")
        if not new_files:
            print(f"  OK: No duplicate file created")
        return True
    elif new_files:
        # Check if the new file is about retry jitter
        for f in new_files:
            nc = (project.root / ".mdr" / "decisions" / f).read_text()
            if "jitter" in nc.lower() and "retry" in nc.lower():
                print(f"  PARTIAL: New file created instead of updating existing: {f}")
                return False
        print(f"  FAIL: New unrelated file(s) created: {new_files}")
        return False
    else:
        print("  FAIL: Existing file not updated and no new file created")
        print(f"  Response preview: {trace2.all_text[:300]}")
        return False


def test_duplicate_decision_not_saved(project: TestProject) -> bool:
    """Corner case: confirming the same decision that already exists should not create a duplicate.

    Fixture: existing MDR about error format (RFC 7807).
    Prompt confirms the same choice — mdr-save should detect the duplicate and skip.
    """
    print("\n=== Test (corner): Duplicate decision not saved ===")

    project.add_fixture_decision("error-response-format.md", ERROR_FORMAT_FIXTURE)
    files_before = project.decision_files()

    trace = run_claude(
        cwd=str(project.root),
        prompt=(
            "For our API error responses, let's use RFC 7807 Problem Details format. "
            "It's the industry standard and provides a consistent structure."
        ),
    )

    print(f"  Cost: ${trace.cost_usd:.4f}")
    print(f"  Turns: {trace.num_turns}")

    files_after = project.decision_files()
    new_files = set(files_after) - set(files_before)

    if not new_files:
        print("  PASS: No duplicate MDR created")
        return True
    else:
        # Check if the new file is truly a duplicate
        for f in new_files:
            content = (project.root / ".mdr" / "decisions" / f).read_text()
            if "rfc 7807" in content.lower() or "problem details" in content.lower():
                print(f"  FAIL: Duplicate MDR created: {f}")
                return False
        # New file about something else is OK
        print(f"  PASS: New file(s) are not duplicates: {new_files}")
        return True


def test_reusability_skip(project: TestProject) -> bool:
    """Corner case: hyper-specific one-time decision should NOT be saved as MDR.

    mdr-save step 0 should skip decisions that cannot apply elsewhere.
    """
    print("\n=== Test (corner): Reusability skip for one-time decision ===")

    files_before = project.decision_files()

    trace = run_claude(
        cwd=str(project.root),
        prompt=(
            "For this one migration script we're writing today, use `sed` to replace "
            "the CSV header line. This is a one-off data migration, not a pattern "
            "we'll use again."
        ),
    )

    print(f"  Cost: ${trace.cost_usd:.4f}")
    print(f"  Turns: {trace.num_turns}")

    files_after = project.decision_files()
    new_files = set(files_after) - set(files_before)

    if not new_files:
        print("  PASS: No MDR created for one-time decision")
        return True
    else:
        # Check content — maybe it generalized the decision (which is acceptable)
        for f in new_files:
            content = (project.root / ".mdr" / "decisions" / f).read_text()
            if "sed" in content.lower() and "migration" in content.lower():
                print(f"  FAIL: MDR created for hyper-specific one-off decision: {f}")
                return False
        print(f"  PASS: New file(s) are generalized decisions (acceptable): {new_files}")
        return True


def main():
    global _cumulative_cost_usd

    print("MDR Protocol E2E Tests")
    print(f"Plugin root: {PLUGIN_ROOT}")
    print(f"Budget per test: ${MAX_BUDGET_USD}")

    test_suite = sys.argv[1] if len(sys.argv) > 1 else "all"

    smoke_tests = {
        "check_existing": test_check_finds_existing_decision,
        "save_new": test_save_new_decision,
        "update_existing": test_update_existing_decision,
        "user_rejection": test_user_rejection,
    }
    corner_tests = {
        "no_save_on_question": test_question_does_not_trigger_save,
        "two_decisions": test_two_decisions_one_session,
        "partial_match": test_partial_match_not_blindly_applied,
        "missing_dir": test_missing_decisions_directory,
        "refinement_update": test_refinement_updates_existing,
        "duplicate_skip": test_duplicate_decision_not_saved,
        "reusability_skip": test_reusability_skip,
    }
    realistic_tests = {
        "realistic_apply": test_realistic_applies_existing_decision,
        "realistic_save": test_realistic_saves_new_decision,
    }

    suites = {
        "smoke": smoke_tests,
        "corner": corner_tests,
        "realistic": realistic_tests,
        "all": {**smoke_tests, **corner_tests, **realistic_tests},
    }
    # Support running a single test by name
    all_tests = {**smoke_tests, **corner_tests, **realistic_tests}
    if test_suite in all_tests:
        tests_to_run = {test_suite: all_tests[test_suite]}
    else:
        tests_to_run = suites.get(test_suite, suites["all"])

    results = {}
    with TestProject() as project:
        print(f"Test project: {project.root}")
        artifact_dir = ARTIFACT_DIR

        for name, test_fn in tests_to_run.items():
            project.reset()
            try:
                results[name] = test_fn(project)
            except Exception as e:
                print(f"\n  ERROR in {name}: {e}")
                results[name] = False

            # Dump trace artifact on failure
            if results.get(name) is not True and _last_trace is not None:
                artifact_path = artifact_dir / f"{name}.jsonl"
                _last_trace.dump(artifact_path)
                print(f"  Artifact: {artifact_path}")

    print("\n=== Summary ===")
    passed = sum(1 for v in results.values() if v is True)
    total = sum(1 for v in results.values() if isinstance(v, bool))
    print(f"Passed: {passed}/{total}")
    print(f"Total cost: ${_cumulative_cost_usd:.4f}")

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
