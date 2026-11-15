"""
OpenVoiceWeb (OVW) - Core SIP/DTMF Session Orchestrator
License: GNU AGPLv3

Exposes the complete 12-key DTMF state machine (including Keys 1, 2, 3, 4, 5, 6, 7, 8, 9, *, 0, #),
zero-PII HMAC Caller-ID authentication, and REST/WebSocket simulation endpoints.
"""

import hashlib
import hmac
import os
from dataclasses import dataclass, field
from typing import Dict, List
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.dom_compiler import AudioNode, SemanticAudioDOMCompiler

app = FastAPI(
    title="OpenVoiceWeb (OVW) Audio-DOM Orchestrator",
    version="0.2.1",
    description="Open-Source SIP/DTMF-to-Semantic-Web Audio Browser Engine",
)

HMAC_SALT = os.getenv("OVW_CLI_HMAC_SALT", "ovw-default-salt").encode("utf-8")
SPEED_STEPS = [1.0, 1.25, 1.5, 2.0, 2.5]
HOME_PORTAL_URL = "https://en.wikipedia.org/wiki/European_Accessibility_Act"


@dataclass
class CallSession:
    session_token: str
    current_url: str
    nodes: List[AudioNode] = field(default_factory=list)
    cursor: int = 0
    link_cursor: int = 0
    speed_idx: int = 0
    paused: bool = False
    voice_query_active: bool = False
    history_stack: List[str] = field(default_factory=list)

    @property
    def playback_speed(self) -> float:
        return SPEED_STEPS[self.speed_idx]


SESSIONS: Dict[str, CallSession] = {}


def hash_caller_id(e164_number: str) -> str:
    """Zero-PII authentication: salts and hashes incoming SIP CLI in memory."""
    return hmac.new(HMAC_SALT, e164_number.strip().encode("utf-8"), hashlib.sha256).hexdigest()


async def fetch_and_compile_url(url: str) -> List[AudioNode]:
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "OpenVoiceWeb/0.2 (+https://nlnet.nl)"})
        resp.raise_for_status()
    nodes = SemanticAudioDOMCompiler.compile_html(resp.text, base_url=url)
    if not nodes:
        raise HTTPException(status_code=422, detail="No readable semantic nodes found on target page.")
    return nodes


class DialInRequest(BaseModel):
    caller_id: str = "+41440000000"
    initial_url: str = HOME_PORTAL_URL


class DTMFKeyPressRequest(BaseModel):
    session_token: str
    digit: str  # '0'-'9', '*', '#'


@app.get("/healthz")
async def health_check():
    return {"status": "ok", "service": "OpenVoiceWeb Orchestrator", "version": "0.2.1"}


@app.post("/api/v1/session/dial")
async def start_call_session(req: DialInRequest):
    session_token = hash_caller_id(req.caller_id)
    nodes = await fetch_and_compile_url(req.initial_url)

    session = CallSession(session_token=session_token, current_url=req.initial_url, nodes=nodes)
    SESSIONS[session_token] = session

    first_node = session.nodes[0]
    return {
        "session_token": session_token,
        "current_url": session.current_url,
        "total_audio_nodes": len(nodes),
        "playback_speed": session.playback_speed,
        "earcon": "heading" if first_node.kind == "heading" else "none",
        "active_node": {
            "node_id": first_node.node_id,
            "kind": first_node.kind,
            "clauses": first_node.text_clauses,
            "links_count": len(first_node.links),
        },
    }


@app.post("/api/v1/session/dtmf")
async def handle_dtmf_interrupt(req: DTMFKeyPressRequest):
    """
    Complete 12-Key Tactile Audio-DOM Grammar:
      [1] Home Portal / Main Channels
      [2] Previous Heading        [8] Next Heading
      [3] Cycle Speed (1.0x->2.5x)
      [4] Previous Paragraph      [6] Next Paragraph
      [5] Pause / Resume
      [7] Previous Link in Node   [9] Next Link in Node
      [*] Go Back (History Pop)   [#] Follow Active Link
      [0] Toggle Push-to-Talk Voice Search
    """
    session = SESSIONS.get(req.session_token)
    if not session:
        raise HTTPException(status_code=404, detail="Active call session not found.")

    current = session.nodes[session.cursor]
    earcon = "none"
    action_taken = "noop"

    if req.digit == "1":  # Home Portal
        session.history_stack.append(session.current_url)
        session.nodes = await fetch_and_compile_url(HOME_PORTAL_URL)
        session.current_url = HOME_PORTAL_URL
        session.cursor = 0
        session.link_cursor = 0
        earcon = "heading"
        action_taken = "returned_home_portal"

    elif req.digit == "8":  # Next Heading
        if current.next_heading_id is not None:
            session.cursor = current.next_heading_id
            session.link_cursor = 0
            earcon = "heading"
            action_taken = "jump_next_heading"
        else:
            earcon = "boundary"
            action_taken = "end_of_headings"

    elif req.digit == "2":  # Previous Heading
        if current.prev_heading_id is not None:
            session.cursor = current.prev_heading_id
            session.link_cursor = 0
            earcon = "heading"
            action_taken = "jump_prev_heading"
        else:
            earcon = "boundary"
            action_taken = "start_of_headings"

    elif req.digit == "6":  # Next Paragraph / Sibling
        if current.next_sibling_id is not None:
            session.cursor = current.next_sibling_id
            session.link_cursor = 0
            action_taken = "next_node"
        else:
            earcon = "boundary"
            action_taken = "end_of_document"

    elif req.digit == "4":  # Previous Paragraph / Sibling
        if current.prev_sibling_id is not None:
            session.cursor = current.prev_sibling_id
            session.link_cursor = 0
            action_taken = "prev_node"
        else:
            earcon = "boundary"
            action_taken = "start_of_document"

    elif req.digit == "3":  # Cycle Playback Speed (WSOLA)
        session.speed_idx = (session.speed_idx + 1) % len(SPEED_STEPS)
        action_taken = f"speed_changed_{session.playback_speed}x"

    elif req.digit == "5":  # Pause / Resume Toggle
        session.paused = not session.paused
        action_taken = "paused" if session.paused else "resumed"

    elif req.digit == "9":  # Next Hyperlink in Active Node
        if current.links:
            session.link_cursor = (session.link_cursor + 1) % len(current.links)
            earcon = "link"
            action_taken = f"selected_link_{session.link_cursor}"
        else:
            earcon = "boundary"
            action_taken = "no_links_in_node"

    elif req.digit == "7":  # Previous Hyperlink in Active Node
        if current.links:
            session.link_cursor = (session.link_cursor - 1) % len(current.links)
            earcon = "link"
            action_taken = f"selected_link_{session.link_cursor}"
        else:
            earcon = "boundary"
            action_taken = "no_links_in_node"

    elif req.digit == "#":  # Follow Active Hyperlink
        if current.links and 0 <= session.link_cursor < len(current.links):
            target_url = current.links[session.link_cursor].url
            session.history_stack.append(session.current_url)
            session.nodes = await fetch_and_compile_url(target_url)
            session.current_url = target_url
            session.cursor = 0
            session.link_cursor = 0
            earcon = "heading"
            action_taken = f"followed_link_to_{target_url}"
        else:
            earcon = "boundary"
            action_taken = "no_active_link_to_follow"

    elif req.digit == "*":  # Go Back to Previous Page
        if session.history_stack:
            prev_url = session.history_stack.pop()
            session.nodes = await fetch_and_compile_url(prev_url)
            session.current_url = prev_url
            session.cursor = 0
            session.link_cursor = 0
            earcon = "heading"
            action_taken = f"navigated_back_to_{prev_url}"
        else:
            session.cursor = 0
            earcon = "boundary"
            action_taken = "reset_to_top_of_page"

    elif req.digit == "0":  # Toggle Push-to-Talk Voice Query
        session.voice_query_active = not session.voice_query_active
        session.paused = session.voice_query_active
        earcon = "link"
        action_taken = "ptt_listening_started" if session.voice_query_active else "ptt_listening_stopped"

    node = session.nodes[session.cursor]
    active_link = node.links[session.link_cursor] if node.links else None
    return {
        "rtp_buffer_flushed": True,
        "action": action_taken,
        "earcon": earcon,
        "current_url": session.current_url,
        "playback_speed": session.playback_speed,
        "paused": session.paused,
        "active_link": {"label": active_link.label, "url": active_link.url} if active_link else None,
        "active_node": {
            "node_id": node.node_id,
            "kind": node.kind,
            "heading_level": node.heading_level,
            "clauses": node.text_clauses,
            "links": [{"label": l.label, "url": l.url} for l in node.links],
            "content_hash": node.content_hash,
        },
    }
