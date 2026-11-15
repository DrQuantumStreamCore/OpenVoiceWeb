"""
OpenVoiceWeb (OVW) - Semantic Web-to-Audio DOM Compiler
License: GNU AGPLv3

Strips visual bloat and compiles HTML5 / WAI-ARIA landmarks into a doubly-linked
AudioDocument navigable via a standard 12-key telephone keypad (DTMF).
"""

import hashlib
import re
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup, Tag


@dataclass
class HyperlinkTarget:
    label: str
    url: str


@dataclass
class AudioNode:
    node_id: int
    kind: str  # "heading", "paragraph", "list_item"
    heading_level: int
    text_clauses: List[str]
    links: List[HyperlinkTarget] = field(default_factory=list)
    prev_heading_id: Optional[int] = None
    next_heading_id: Optional[int] = None
    prev_sibling_id: Optional[int] = None
    next_sibling_id: Optional[int] = None
    content_hash: str = ""

    def __post_init__(self) -> None:
        joined = "|".join(self.text_clauses)
        self.content_hash = hashlib.blake2b(joined.encode("utf-8"), digest_size=16).hexdigest()


class SemanticAudioDOMCompiler:
    STRIP_TAGS = {"script", "style", "noscript", "svg", "canvas", "iframe", "footer", "aside"}
    CLAUSE_SPLIT_RE = re.compile(r"(?<=[.!?;:])\s+")

    @classmethod
    def split_into_clauses(cls, text: str) -> List[str]:
        cleaned = re.sub(r"\s+", " ", text).strip()
        if not cleaned:
            return []
        return [c.strip() for c in cls.CLAUSE_SPLIT_RE.split(cleaned) if c.strip()]

    @classmethod
    def compile_html(cls, html: str, base_url: str = "") -> List[AudioNode]:
        soup = BeautifulSoup(html, "lxml")

        # 1. Remove non-auditory and tracking elements
        for tag in soup.find_all(cls.STRIP_TAGS):
            tag.decompose()
        for hidden in soup.find_all(attrs={"aria-hidden": "true"}):
            hidden.decompose()

        # 2. Prefer WAI-ARIA role="main" or <main> / <article> if present
        root: Tag = (
            soup.find(attrs={"role": "main"})
            or soup.find("main")
            or soup.find("article")
            or soup.body
            or soup
        )

        nodes: List[AudioNode] = []
        heading_indices: List[int] = []

        for elem in root.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li"]):
            text = elem.get_text(" ", strip=True)
            clauses = cls.split_into_clauses(text)
            if not clauses:
                continue

            node_id = len(nodes)
            tag_name = elem.name.lower()

            if tag_name.startswith("h"):
                kind = "heading"
                level = int(tag_name[1])
                heading_indices.append(node_id)
            elif tag_name == "li":
                kind = "list_item"
                level = 0
            else:
                kind = "paragraph"
                level = 0

            links: List[HyperlinkTarget] = []
            for a_tag in elem.find_all("a", href=True):
                link_text = a_tag.get_text(strip=True)
                href = a_tag["href"].strip()
                if link_text and not href.startswith("#") and not href.lower().startswith("javascript:"):
                    resolved_url = urljoin(base_url, href) if base_url else href
                    links.append(HyperlinkTarget(label=link_text, url=resolved_url))

            nodes.append(
                AudioNode(
                    node_id=node_id,
                    kind=kind,
                    heading_level=level,
                    text_clauses=clauses,
                    links=links,
                )
            )

        # 3. Wire doubly-linked sibling and heading pointers for O(1) DTMF jumps
        total = len(nodes)
        for idx, node in enumerate(nodes):
            if idx > 0:
                node.prev_sibling_id = idx - 1
            if idx < total - 1:
                node.next_sibling_id = idx + 1

            prev_h = [h for h in heading_indices if h < idx]
            next_h = [h for h in heading_indices if h > idx]
            node.prev_heading_id = prev_h[-1] if prev_h else None
            node.next_heading_id = next_h[0] if next_h else None

        return nodes
