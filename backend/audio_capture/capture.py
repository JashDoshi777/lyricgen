"""
Audio capture module using WASAPI loopback.
Records system audio output for fingerprint recognition.
"""

import io
import wave
import numpy as np
import sounddevice as sd
from config import Config


def get_loopback_device():
    """Find the WASAPI loopback device for system audio capture."""
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()

    # Find WASAPI host API
    wasapi_index = None
    for i, api in enumerate(hostapis):
        if 'WASAPI' in api['name']:
            wasapi_index = i
            break

    if wasapi_index is None:
        raise RuntimeError("WASAPI host API not found. Windows is required.")

    # Find default output device with WASAPI
    for i, dev in enumerate(devices):
        if dev['hostapi'] == wasapi_index and dev['max_output_channels'] > 0:
            if 'Speakers' in dev['name'] or 'headphone' in dev['name'].lower():
                return i, dev

    # Fallback: find any WASAPI output device
    for i, dev in enumerate(devices):
        if dev['hostapi'] == wasapi_index and dev['max_output_channels'] > 0:
            return i, dev

    raise RuntimeError("No suitable WASAPI loopback device found.")


def capture_system_audio(duration=None, sample_rate=44100):
    """
    Capture system audio using WASAPI loopback.

    Args:
        duration: Recording duration in seconds (default from config).
        sample_rate: Sample rate in Hz.

    Returns:
        bytes: WAV file data as bytes.
    """
    if duration is None:
        duration = Config.FINGERPRINT_DURATION

    try:
        device_id, device_info = get_loopback_device()
        channels = min(device_info['max_output_channels'], 2)

        # Try different channel counts — WASAPI loopback may reject the reported count
        channel_attempts = [channels]
        if channels != 2:
            channel_attempts.append(2)
        if channels != 1:
            channel_attempts.append(1)

        recording = None
        used_channels = channels
        for ch in channel_attempts:
            try:
                recording = sd.rec(
                    int(duration * sample_rate),
                    samplerate=sample_rate,
                    channels=ch,
                    dtype='int16',
                    device=device_id,
                    extra_settings=sd.WasapiSettings(exclusive=False)
                )
                sd.wait()
                used_channels = ch
                break
            except Exception:
                continue

        if recording is None:
            print("[AudioCapture] All channel configurations failed")
            return None

        # Convert to WAV bytes
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(used_channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(recording.tobytes())

        wav_buffer.seek(0)
        return wav_buffer.read()

    except Exception as e:
        print(f"[AudioCapture] Error capturing audio: {e}")
        return None


def check_audio_level(audio_data, threshold=500):
    """
    Check if audio data contains meaningful sound (not silence).

    Args:
        audio_data: Raw audio bytes.
        threshold: Minimum RMS level to consider as non-silent.

    Returns:
        bool: True if audio level is above threshold.
    """
    if audio_data is None:
        return False

    try:
        samples = np.frombuffer(audio_data, dtype=np.int16)
        rms = np.sqrt(np.mean(samples.astype(float) ** 2))
        return rms > threshold
    except Exception:
        return False
