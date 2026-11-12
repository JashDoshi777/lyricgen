"""
System-audio capture for the fingerprint fallback.

  Windows: WASAPI loopback on the default output device.
  macOS  : macOS cannot record system audio directly. Install a virtual loopback
           device (e.g. `brew install blackhole-2ch`), create a Multi-Output Device
           (speakers + BlackHole) in Audio MIDI Setup, and set it as output.
           We then record from the input device whose name contains LOOPBACK_DEVICE.
"""

import io
import sys
import wave

import numpy as np

from config import Config

try:
    import sounddevice as sd
except Exception:  # PortAudio missing
    sd = None


def _record(duration, rate, **kw):
    rec = sd.rec(int(duration * rate), samplerate=rate, dtype='int16', **kw)
    sd.wait()
    return rec


def _to_wav(rec, rate):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(rec.shape[1])
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(rec.tobytes())
    return buf.getvalue()


def _capture_windows(duration, rate):
    hostapis = sd.query_hostapis()
    wasapi = next((i for i, a in enumerate(hostapis) if 'WASAPI' in a['name']), None)
    if wasapi is None:
        raise RuntimeError("WASAPI not found")
    dev_id = hostapis[wasapi]['default_output_device']
    info = sd.query_devices(dev_id)
    try:  # sounddevice >= 0.5.2 supports real loopback capture
        settings = sd.WasapiSettings(loopback=True)
    except TypeError:
        settings = sd.WasapiSettings(exclusive=False)
    for ch in dict.fromkeys([min(info['max_output_channels'], 2), 2, 1]):
        try:
            return _to_wav(_record(duration, rate, channels=ch, device=dev_id, extra_settings=settings), rate)
        except Exception:
            continue
    return None


def _capture_mac(duration, rate):
    needle = (Config.LOOPBACK_DEVICE or 'BlackHole').lower()
    for i, d in enumerate(sd.query_devices()):
        if d['max_input_channels'] > 0 and needle in d['name'].lower():
            ch = min(d['max_input_channels'], 2)
            return _to_wav(_record(duration, rate, channels=ch, device=i), rate)
    return None


_warned = False


def capture_system_audio(duration=None, sample_rate=44100):
    """Return WAV bytes, or None if system audio can't be captured."""
    global _warned
    if sd is None:
        return None
    duration = duration or Config.FINGERPRINT_DURATION
    try:
        if sys.platform == 'win32':
            return _capture_windows(duration, sample_rate)
        if sys.platform == 'darwin':
            wav = _capture_mac(duration, sample_rate)
            if wav is None and not _warned:
                _warned = True
                print(f"[AudioCapture] No '{Config.LOOPBACK_DEVICE}' input device found — fingerprint "
                      "fallback unavailable on macOS (install BlackHole to enable it).")
            return wav
    except Exception as e:
        print(f"[AudioCapture] {e}")
    return None


def check_audio_level(wav_bytes, threshold=300):
    if not wav_bytes:
        return False
    try:
        samples = np.frombuffer(wav_bytes[44:], dtype=np.int16)
        return samples.size > 0 and float(np.sqrt(np.mean(samples.astype(np.float64) ** 2))) > threshold
    except Exception:
        return False
