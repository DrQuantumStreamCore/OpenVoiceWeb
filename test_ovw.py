"""
Unit tests for OpenVoiceWeb Semantic Audio-DOM Compiler & DSP Pipeline.
"""

import numpy as np
from src.dom_compiler import SemanticAudioDOMCompiler
from src.dsp_pipeline import TelephonyDSPPipeline


def test_dom_compiler_headings_and_links():
    sample_html = """
    <html>
      <body>
        <nav aria-hidden="true">Hidden visual menu</nav>
        <main role="main">
          <h1>Swiss Public Transit Accessibility</h1>
          <p>Welcome to the audio portal. Check the <a href="/timetables">SBB Timetables</a> today.</p>
          <h2>Regional Updates</h2>
          <p>Baden to Zurich line operates normally.</p>
        </main>
      </body>
    </html>
    """
    nodes = SemanticAudioDOMCompiler.compile_html(sample_html, base_url="https://example.ch")
    assert len(nodes) == 4
    assert nodes[0].kind == "heading"
    assert nodes[0].next_heading_id == 2
    assert nodes[1].links[0].url == "https://example.ch/timetables"


def test_dsp_preemphasis_and_earcon():
    dsp = TelephonyDSPPipeline(sample_rate=8000)
    earcon = dsp.generate_earcon("heading")
    assert earcon.shape[0] == int(8000 * 0.045)
    processed = dsp.apply_pstn_preemphasis(earcon)
    assert np.max(np.abs(processed)) <= 0.85
