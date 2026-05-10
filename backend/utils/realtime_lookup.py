from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request


_WHO_IS_RE = re.compile(r"^\s*who\s+(?:is|was|are)\s+(.+?)\??\s*$", re.IGNORECASE)
_WHAT_IS_PERSON_ROLE_RE = re.compile(
    r"^\s*what\s+is\s+the\s+(?:current|present|latest)\s+(.+?)\??\s*$",
    re.IGNORECASE,
)
_WHAT_IS_RE = re.compile(r"^\s*what\s+(?:is|are)\s+(.+?)\??\s*$", re.IGNORECASE)
_EXPLAIN_RE = re.compile(r"^\s*(?:define|describe|explain)\s+(.+?)\??\s*$", re.IGNORECASE)
_TELL_ME_RE = re.compile(r"^\s*tell\s+me\s+about\s+(.+?)\??\s*$", re.IGNORECASE)
_HOW_MUCH_RE = re.compile(r"^\s*how\s+(?:much|many|big|old|tall|fast|far|long)\s+(.+?)\??\s*$", re.IGNORECASE)
_X_OF_Y_RE = re.compile(r"^\s*(.+?\s+of\s+.+?)\??\s*$", re.IGNORECASE)
_HYDRATION_TROUBLESHOOT_RE = re.compile(
    r"\bhydration\b.*\berror\b|\berror\b.*\bhydration\b",
    re.IGNORECASE,
)


def fetch_realtime_answer(question: str, *, timeout_seconds: float = 4.0) -> tuple[str, str] | None:
    text = (question or "").strip()
    if not text:
        return None

    subject = _extract_subject(text)
    if not subject:
        # If no regex match, try searching for the whole text
        subject = text

    # Step 1: Search for the best page title
    search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(subject)}&format=json&limit=1"
    try:
        req = urllib.request.Request(search_url, headers={"User-Agent": "paragi-prototype/0.5"})
        with urllib.request.urlopen(req, timeout=timeout_seconds * 0.4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = data.get("query", {}).get("search", [])
            title = results[0].get("title") if results else subject.replace(" ", "_")
    except Exception:
        title = subject.replace(" ", "_")

    # Step 2: Fetch summary
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "paragi-prototype/0.5"})
        with urllib.request.urlopen(req, timeout=timeout_seconds * 0.6) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception:
        return None

    extract = str(payload.get("extract", "")).strip()
    resolved_title = str(payload.get("title", "")).strip()
    if not extract:
        return None

    answer = extract
    if resolved_title:
        answer = f"{resolved_title}: {extract}"
    return answer, "wikipedia_summary"


def fetch_troubleshooting_answer(question: str) -> tuple[str, str] | None:
    text = (question or "").strip()
    if not text:
        return None
    lower = text.lower()

    if _HYDRATION_TROUBLESHOOT_RE.search(lower):
        if "next" in lower or "react" in lower or "js" in lower or "javascript" in lower:
            answer = (
                "A hydration error usually means server HTML and first client render do not match. "
                "Check for browser-only APIs (window, localStorage) used during render, Date.now()/Math.random() in JSX, "
                "and conditional UI that differs between server and client. Move client-only logic into useEffect, "
                "use dynamic(() => import(...), { ssr: false }) for client-only components, and ensure initial state/data "
                "is identical on both sides."
            )
            return answer, "troubleshooting_nextjs_hydration"
    return None


def _extract_subject(text: str) -> str:
    for pattern in (
        _WHO_IS_RE,
        _WHAT_IS_PERSON_ROLE_RE,
        _WHAT_IS_RE,
        _EXPLAIN_RE,
        _TELL_ME_RE,
        _HOW_MUCH_RE,
        _X_OF_Y_RE,
    ):
        m = pattern.match(text)
        if m:
            subject = m.group(1).strip()
            # Strip leading articles for better Wikipedia title matching
            for prefix in ("the ", "a ", "an "):
                if subject.lower().startswith(prefix):
                    subject = subject[len(prefix):]
                    break
            return subject.strip()
    return ""

