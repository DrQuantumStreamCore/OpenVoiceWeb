# OpenVoiceWeb (OVW) — Technical Architecture Specification

## 1. Design Philosophy & Real-Time Constraints

Designing an audio web browser over standard public switched telephone networks (PSTN) and 4G VoLTE feature phones introduces strict physical and protocol constraints that do not exist in desktop screen readers (such as NVDA or JAWS):

1. **Deterministic Barge-In Latency (< 150ms):** Experienced blind users listen to synthesized speech at `1.5x` to `2.5x` normal speed and navigate by rapidly skimming headings—pressing a key to jump the instant they hear an irrelevant word. If the telephony gateway buffers 3–5 seconds of synthesized PCM audio inside the SIP media server, pressing `8` (Next Heading) results in a sluggish, disorienting delay.
2. **Narrowband Acoustic Passband (300 Hz – 3,400 Hz):** While modern 4G VoLTE calls support AMR-WB (`50 Hz – 7,000 Hz`), many landline and cross-carrier interconnects fall back to ITU-T G.711 (`PCMU/PCMA` at 8 kHz sampling rate). High-frequency sibilants (`s`, `f`, `th`, `z`) critical for speech intelligibility at high playback speeds are attenuated above 3.4 kHz unless compensated via pre-emphasis DSP filtering.
3. **Zero-Cost Inbound Call Economics:** To allow non-profits and blind associations to operate the gateway at near-zero marginal cost, the architecture operates over standard geographic landline DIDs (covered by flat-rate domestic calling plans) and employs **Content-Addressable Audio Caching** so shared news/weather feeds are synthesized once and streamed from memory to hundreds of concurrent callers.

---

## 2. Subsystem 1: SIP/RTP Media Gateway & Sub-150ms DTMF Barge-In

OpenVoiceWeb decouples the SIP signaling/media plane from the Audio-DOM orchestration plane via a bidirectional, frame-paced event socket:

```text
Caller Keypad Press ('8' - Next Heading)
       │
       ▼  (RFC 4733 RTP Event Packet - Payload Type 101)
┌──────────────────────────────────────────────────────────┐
│ 1. SIP/RTP Media Endpoint (FreeSWITCH / PJSIP)           │
│    - Detects RFC 4733 DTMF start-of-event within 20ms    │
│    - Immediately executes `uuid_break` / RTP TX flush    │
└───────────────────────────┬──────────────────────────────┘
                            │  (< 5ms local UNIX socket / gRPC)
                            ▼
┌──────────────────────────────────────────────────────────┐
│ 2. OVW Session State Machine                             │
│    - Cancels in-flight TTS synthesis token stream        │
│    - Advances Audio-DOM cursor: `node.next_heading()`    │
│    - Emits 40ms auditory earcon ("tick") for tactile ack │
└───────────────────────────┬──────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────┐
│ 3. Chunked TTS Streamer                                  │
│    - Synthesizes first clause of new heading (<= 60ms)   │
│    - Streams 20ms RTP frames (160 bytes G.711) to caller │
└──────────────────────────────────────────────────────────┘
Total End-to-End Barge-In Latency: ~95ms - 135ms
```

### Auditory Earcons (Non-Verbal Acoustic Landmarks)
To avoid wasting time speaking meta-phrases like *"Heading Level 2, Link"* before every sentence, OVW injects brief, distinct 40ms–60ms acoustic chimes (earcons) mixed into the PCM stream:
* **Rising two-tone chime (440 Hz -> 880 Hz):** Enters a new major section (`<h1>` / `<h2>`).
* **Short woodblock click (1,200 Hz):** Indicates the current sentence contains a selectable hyperlink (press `#` to follow).
* **Low boundary thud (220 Hz):** Reached the end of the current article or list.

---

## 3. Subsystem 2: The Semantic Web-to-Audio DOM Compiler

Standard HTML pages cannot be read linearly from top to bottom without trapping the listener in repetitive navigation bars, footers, and cookie consent modals. OVW compiles raw web documents into an **Audio DOM Tree (`AudioDocument`)** in three deterministic stages:

### Stage A: Sanitization & Landmark Extraction
1. Fetches target resource via an isolated headless fetcher (blocking ad/tracker domains and stripping `<script>`, `<style>`, `<svg>`, and `<iframe aria-hidden="true">`).
2. Extracts explicit **WAI-ARIA Landmarks** (`role="main"`, `role="navigation"`, `role="search"`, `aria-live`) alongside **Mozilla Readability / Lexbor** structural heuristics.

### Stage B: Hierarchical Node Normalization
The document is compiled into a flat-indexed doubly linked tree of `AudioNode` structs:

```rust
pub struct AudioNode {
    pub node_id: u32,
    pub kind: NodeKind,          // Heading(u8), Paragraph, ListItem(u32), Link, TableSummary
    pub parent_id: Option<u32>,
    pub prev_heading_id: Option<u32>,
    pub next_heading_id: Option<u32>,
    pub prev_sibling_id: Option<u32>,
    pub next_sibling_id: Option<u32>,
    pub text_clauses: Vec<String>, // Pre-segmented at punctuation boundaries for low-latency TTS
    pub links: Vec<HyperlinkTarget>,
    pub content_hash: [u8; 32],    // BLAKE3 hash for shared TTS audio cache lookup
}
```

### Stage C: Clause-Level Pre-Segmentation
Rather than sending an entire 500-word paragraph to the TTS engine at once, each `AudioNode` is split at natural prosodic boundaries (periods, semicolons, em-dashes). The TTS engine synthesizes Clause $N+1$ in the background while Clause $N$ is playing over RTP, achieving near-zero initial time-to-first-audio (TTFA < 70ms).

---

## 4. Subsystem 3: Telephony DSP & Local Voice Pipeline

### 1. Narrowband Intelligibility Pre-Emphasis Filter
Before downsampling 22.05 kHz neural TTS output (Piper / Kokoro ONNX) to 8 kHz G.711 or 16 kHz AMR-WB, OVW passes the PCM stream through a 3-stage DSP pipeline:
* **High-Pass Filter (Cutoff 250 Hz, 12 dB/octave):** Removes low-frequency mud and rumble that saturate small keypad-phone earpieces.
* **Presence Band Boost (+4.5 dB peaking EQ at 2,600 Hz, Q=1.4):** Sharpens consonant definition (`t`, `k`, `s`, `f`) right below the 3.4 kHz PSTN Nyquist rolloff.
* **Lookahead Dynamic Range Limiter (-1.5 dBFS ceiling, 3:1 compression):** Ensures consistent, loud volume for elderly users who may also have mild age-related hearing loss (presbycusis).

### 2. Pitch-Preserving Time-Stretching (WSOLA)
When a user presses Key `3` to increase reading speed (`1.0x` -> `1.25x` -> `1.5x` -> `2.0x` -> `2.5x`), OVW applies **Waveform Similarity Overlap-Add (WSOLA)** in real time on the PCM buffer. This allows instant speed adjustments mid-sentence without re-running neural TTS inference or distorting vocal pitch.

### 3. Push-to-Talk Voice Query (`Key 0`)
While 90% of navigation uses instant tactile DTMF keys, pressing `0` opens a half-duplex voice capture window:
1. Playback mutes immediately and plays a "listening" tone.
2. Inbound RTP audio is buffered until 800ms of silence (VAD) or the user presses `#`.
3. **Whisper.cpp (quantized `base` or `small` int8 model)** transcribes the intent locally.
4. Intent router maps the utterance to either a direct connector (e.g., *"Next train from Baden to Zurich"* -> GTFS API) or a web/Wikipedia search compiled into a fresh `AudioDocument`.

---

## 5. Privacy, Security & Zero-PII Architecture

Because OpenVoiceWeb serves a vulnerable population (blind and elderly citizens), privacy is enforced by design:
* **Salted HMAC Caller-ID Hashing:** The incoming SIP `From:` header (phone number) is immediately hashed in memory using a deployment-specific secret salt: `user_key = HMAC_SHA256(server_salt, E164_number)`. The raw phone number is never written to disk or database logs.
* **No Voice Biometric Retention:** Inbound audio from `Key 0` Push-to-Talk queries is processed strictly in tmpfs (RAM) and overwritten immediately after ASR transcription completes.
* **Content-Addressable Multi-User Audio Cache:** Pre-synthesized audio chunks are indexed solely by the `BLAKE3(text_clause + voice_id)` hash in Redis/DragonflyDB. Five hundred blind users calling in to read the morning news share the exact same cached PCM/Opus audio blocks in RAM—reducing CPU consumption by >90% while keeping individual reading positions strictly isolated.
