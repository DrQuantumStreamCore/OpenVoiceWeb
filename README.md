# OpenVoiceWeb (OVW) 📞🌐

**An Open-Source SIP/DTMF-to-Semantic-Web Audio Browser Engine for Visually Impaired Keypad Phone Users**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![License: Apache 2.0](https://img.shields.io/badge/Client_SDKs-Apache_2.0-green.svg)](https://opensource.org/licenses/Apache-2.0)
[![Protocol: SIP / RTP / RFC 4733](https://img.shields.io/badge/Telephony-SIP_%7C_RTP_%7C_RFC_4733-orange.svg)](#)
[![Accessibility: WAI-ARIA 1.2](https://img.shields.io/badge/Web_Standards-WAI--ARIA_1.2_%7C_HTML5-purple.svg)](#)

> **Live Interactive UI / Gateway Prototype:** [https://rc2kmwpxgxjyy.kimi.place/](https://rc2kmwpxgxjyy.kimi.place/)

---

## 🎯 Overview & Problem Statement

Over 30 million citizens in Europe live with blindness or partial sight, and **more than 65% are over the age of 65**. While younger digital natives rely on smartphone screen readers (VoiceOver, TalkBack), millions of older adults experiencing late-onset sight loss (macular degeneration, glaucoma, diabetic retinopathy) cannot operate flat glass touchscreens that lack physical orientation points.

As public transit schedules, news, municipal portals, and health services migrate exclusively to visual web browsers, citizens who rely on **classic tactile keypad ("dumb") phones** or basic landlines face severe digital exclusion. Meanwhile, commercial smart speakers (Alexa, Google Home) require home Wi-Fi, trap users inside proprietary walled gardens, harvest voice biometrics, and cannot navigate structured long-form web pages.

**OpenVoiceWeb (OVW)** solves this by turning any standard PSTN landline or 2G/4G VoLTE keypad telephone into a fast, privacy-preserving, self-hostable **Audio Browser for the Open Web**.

---

## ✨ Key Features

* **Zero Hardware or Data Plan Required:** Works over a standard geographic voice call (`G.711 PCMU/PCMA` narrowband or `AMR-WB / Opus` wideband) from any legacy landline or basic keypad phone.
* **Sub-150ms Tactile Keypad (DTMF) "Barge-In":** Unlike legacy IVR menus, OVW treats the 12-key telephone keypad (`0–9`, `*`, `#`) as a real-time DOM navigation controller. Users can interrupt speech mid-syllable to jump across headings, skip paragraphs, follow hyperlinks, or ramp playback speed between `0.75x` and `2.5x`.
* **Semantic Web-to-Audio DOM Compiler:** Strips visual clutter, tracking scripts, and cookie banners from arbitrary websites, RSS/Atom feeds, MediaWiki pages, and ActivityPub streams—compiling WAI-ARIA landmarks and HTML5 headings (`<h1>`–`<h6>`, `<article>`, `<nav>`) into a hierarchical Audio DOM Tree.
* **100% Open-Weight, Local Speech Pipeline:** Uses self-hosted neural Text-to-Speech (Piper / Kokoro ONNX) and low-latency speech recognition (Whisper.cpp) tuned specifically for 8kHz/16kHz telephony passbands. Zero reliance on proprietary Big Tech cloud APIs.
* **Passwordless, Zero-PII Authentication:** Optional Caller-ID (CLI) hashing (`HMAC-SHA256`) loads user language preferences, playback speed, and personal bookmarks automatically without storing raw phone numbers or requiring visual PIN entry.
* **European Accessibility Act (EAA) Ready Connectors:** Built-in open-source adapters for GTFS/NeTEx real-time public transport (e.g., SBB, DB, SNCF), Open-Meteo weather, MediaWiki, RSS/Atom, and IMAP/JMAP audio email readout.

---

## ⌨️ The 12-Key Tactile Audio-DOM Grammar

OpenVoiceWeb maps standard WAI-ARIA and HTML5 document structures to an intuitive, ergonomic 12-key telephone keypad layout:

```text
+-----------------------+-----------------------+-----------------------+
|          [1]          |          [2]          |          [3]          |
|    Main Channels /    |   Previous Heading    |   Playback Speed +    |
|     Home Bookmark     |     (H1 - H6 Up)      |  (Cycle 1.0x -> 2.5x) |
+-----------------------+-----------------------+-----------------------+
|          [4]          |          [5]          |          [6]          |
|  Previous Paragraph   |    Pause / Resume     |    Next Paragraph     |
|    / Rewind 10 Sec    |  (Read Current Meta)  |   / Skip 10 Sec Fwd   |
+-----------------------+-----------------------+-----------------------+
|          [7]          |          [8]          |          [9]          |
|   Previous Link /     |     Next Heading      |     Next Link /       |
|   Menu Item in Node   |    (H1 - H6 Down)     |   Menu Item in Node   |
+-----------------------+-----------------------+-----------------------+
|          [*]          |          [0]          |          [#]          |
|    Go Back / Up One   |    Push-to-Talk       |    Select / Follow    |
|   Level (DOM Parent)  |  Voice Search / Query |   Active Link / Item  |
+-----------------------+-----------------------+-----------------------+
```

---

## 🏗️ High-Level System Architecture

```text
+--------------------+         SIP / RTP (G.711 / Opus)         +-----------------------------------+
|  Keypad Feature    | <======================================> |  SIP / RTP Media Gateway          |
|  Phone / Landline  |         RFC 4733 Out-of-Band DTMF        |  (FreeSWITCH / PJSIP Event Socket)|
+--------------------+                                          +-----------------+-----------------+
                                                                                  |
                                                           gRPC / WebSockets      |  20ms PCM Frames +
                                                           (Low-Latency Control)  |  DTMF Interrupts
                                                                                  v
+---------------------------------------------------------------------------------------------------+
|                               OpenVoiceWeb Core Orchestrator (Rust / Python)                      |
|                                                                                                   |
|  +-----------------------------+   +-----------------------------+   +-------------------------+  |
|  | Session & DTMF State Engine |   | Semantic Audio-DOM Compiler |   | Telephony DSP & TTS/ASR |  |
|  | - Sub-150ms RTP Buffer Flush|   | - Readability / Lexbor HTML |   | - Piper / Kokoro TTS    |  |
|  | - HMAC-SHA256 CLI Auth      |   | - WAI-ARIA Tree Linearizer  |   | - Whisper.cpp ASR       |  |
|  | - Cursor & Bookmark State   |   | - RSS / ActivityPub / GTFS  |   | - WSOLA Time-Stretching |  |
|  +-----------------------------+   +-----------------------------+   +-------------------------+  |
+---------------------------------------------------------------------------------------------------+
                                                                                  |
                                                                                  v
                                                        +-------------------------------------------+
                                                        |  Open Internet & Public Infrastructure    |
                                                        |  - HTML5 / WAI-ARIA Websites              |
                                                        |  - RSS / Atom / MediaWiki / ActivityPub   |
                                                        |  - GTFS Transit APIs / Open-Meteo / JMAP  |
                                                        +-------------------------------------------+
```

For a deep dive into the real-time RTP buffer flushing, DSP pre-emphasis filters, and DOM linearization algorithms, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## 🚀 Quickstart (Docker Compose Sandbox)

You can spin up a complete local OpenVoiceWeb node—including the SIP soft-switch, Semantic Audio-DOM Compiler, and local Piper TTS engine—and dial into it from any SIP softphone (e.g., Linphone, Bria, MicroSIP) or connect a local SIP trunk.

### Prerequisites
* Docker & Docker Compose (v2.20+)
* 4 GB RAM (CPU-only execution supported via ONNX Runtime; GPU optional)

### 1. Clone and Launch
```bash
git clone https://github.com/DrQuantumStreamCore/OpenVoiceWeb.git
cd OpenVoiceWeb
cp .env.example .env
docker compose up --build -d
```

### 2. Dial In via Any SIP Client
Point any open-source SIP client (such as **Linphone**) to:
* **SIP URI:** `sip:1000@127.0.0.1:5060`
* **Transport:** UDP / TCP
* **Codec:** `PCMU (G.711 u-law)`, `PCMA (G.711 A-law)`, or `Opus`
* **DTMF Mode:** `RFC 4733 (RTP Payload)`

Use keys `2`/`8` to jump headings, `4`/`6` to skip paragraphs, `3` to speed up speech, and `0` to issue a voice query.

---

## 🗺️ Roadmap & Milestones

- [x] **Phase 0: Concept & Interactive Gateway Prototype** — Validation of keypad-first UX and hybrid voice/DTMF workflows ([Live Demo](https://rc2kmwpxgxjyy.kimi.place/)).
- [ ] **Milestone 1: Open SIP/RTP & Real-Time DTMF State-Machine Engine** — Containerized FreeSWITCH/ARI bridge, sub-150ms RTP buffer flush on RFC 4733 interrupt, and zero-PII HMAC CLI state store.
- [ ] **Milestone 2: Semantic Web-to-Audio DOM Parser & WAI-ARIA Compiler** — Headless DOM extraction (Lexbor/Readability), WAI-ARIA landmark mapping to 12-key grammar, and session link-graph traversal.
- [ ] **Milestone 3: Local Open-Weight Neural TTS & ASR Edge Pipeline** — Multi-language telephony TTS (EN, DE, FR, RO, ES), WSOLA pitch-preserving speed scaling (`0.75x–2.5x`), and 300Hz–3400Hz PSTN pre-emphasis DSP filter bank.
- [ ] **Milestone 4: EAA Public Service Connectors & BVI Field Validation** — Turnkey connectors for GTFS public transit, Open-Meteo, RSS, and IMAP/JMAP; Helm/Kubernetes manifests; field validation with 50+ visually impaired seniors.

---

## 📜 License & Open Standards Commitment

* **Core Engine & Server Components:** Licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0-or-later)** to guarantee that any cloud-hosted or telecom-deployed modifications remain free and open to the visually impaired community.
* **Protocol Adapters & Client Plugins:** Licensed under the **Apache License 2.0**.

---

## 🤝 Credits & Maintainers

Initiated and maintained by **Cristinel (Chris) Corobana** (Telecommunications & Streaming Systems Architect; Founder of Doctor Quantum Ltd, Corobana Consulting IT, and Freedom Smile NGO) alongside AI Lead **Gabriel Dobocan** and Co-Founder **Sebastian Văduva**.
