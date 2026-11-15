"""
OpenVoiceWeb (OVW) - Telephony DSP Pre-Emphasis & Auditory Earcon Engine
License: GNU AGPLv3

Optimizes neural TTS audio intelligibility over 8kHz G.711 (300Hz-3400Hz) and
16kHz AMR-WB VoLTE channels for elderly and visually impaired listeners.
"""

import numpy as np
from scipy.signal import butter, lfilter


class TelephonyDSPPipeline:
    def __init__(self, sample_rate: int = 8000) -> None:
        self.sample_rate = sample_rate

    def apply_pstn_preemphasis(self, pcm_samples: np.ndarray) -> np.ndarray:
        """
        Applies a 250Hz high-pass filter (removes low-end rumble on small keypad handsets)
        followed by a first-order high-frequency pre-emphasis filter (alpha=0.85) to boost
        consonant definition between 2.0kHz and 3.4kHz before G.711 quantization.
        """
        if pcm_samples.size == 0:
            return pcm_samples.astype(np.float32)

        nyquist = 0.5 * self.sample_rate
        highpass_cutoff = 250.0 / nyquist
        b, a = butter(2, highpass_cutoff, btype="high", analog=False)
        filtered = lfilter(b, a, pcm_samples)

        # First-order pre-emphasis: y[n] = x[n] - 0.85 * x[n-1]
        emphasized = np.append(filtered[0], filtered[1:] - 0.85 * filtered[:-1])

        # Soft lookahead limiter (-1.5 dBFS ceiling)
        peak = np.max(np.abs(emphasized)) + 1e-9
        normalized = (emphasized / peak) * 0.84
        return normalized.astype(np.float32)

    def generate_earcon(self, earcon_type: str) -> np.ndarray:
        """
        Synthesizes brief 45ms non-verbal acoustic landmarks (earcons) so blind users
        receive instant tactile confirmation of keypad presses without verbose TTS announcements.
        """
        duration_sec = 0.045
        t = np.linspace(0, duration_sec, int(self.sample_rate * duration_sec), endpoint=False)

        if earcon_type == "heading":
            # Rising two-tone chime (440Hz -> 880Hz)
            freq = np.linspace(440.0, 880.0, len(t))
        elif earcon_type == "link":
            # Crisp 1200Hz click
            freq = 1200.0
        else:
            # Boundary low tone (220Hz)
            freq = 220.0

        wave = 0.5 * np.sin(2.0 * np.pi * freq * t)
        envelope = np.hanning(len(t))
        return (wave * envelope).astype(np.float32)
