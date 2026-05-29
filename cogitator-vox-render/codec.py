# -*- coding: utf-8 -*-
"""
Cogitator-Vox codec core — continuous-phase BFSK with Goertzel demodulation.
Pure standard library. Shared by the Flask web app.

  FREQ_ZERO / FREQ_ONE  : the two FSK tones
  BIT_DURATION          : seconds per bit (encode + decode must agree)
  GOLD_CODE             : frame-sync preamble

The Omnissiah provides.
"""

import wave
import struct
import math
import io

# ───────────────────────────── CODEC PARAMETERS ─────────────────────────────
SAMPLE_RATE   = 44100   # Hz
BIT_DURATION  = 0.025   # seconds per bit
FREQ_ZERO     = 2000    # Hz  -> binary 0
FREQ_ONE      = 6000    # Hz  -> binary 1
AMPLITUDE     = 0.85    # 0..1 fraction of full scale (headroom avoids clipping)
FULL_SCALE    = 32767

GOLD_CODE = "110010011100111011001001110011101100100111001110110010011100111"
SAMPLES_PER_BIT = int(round(SAMPLE_RATE * BIT_DURATION))


# ───────────────────────────── ENCODING ─────────────────────────────
def text_to_binary(text: str) -> str:
    return ''.join(format(b, '08b') for b in text.encode('utf-8'))


def binary_to_text(binary: str) -> str:
    n = len(binary) - (len(binary) % 8)
    by = bytearray(int(binary[i:i + 8], 2) for i in range(0, n, 8))
    return by.decode('utf-8', errors='replace')


def encode_bits_to_samples(binary: str):
    samples = []
    phase = 0.0
    for bit in binary:
        freq = FREQ_ONE if bit == '1' else FREQ_ZERO
        dphase = 2.0 * math.pi * freq / SAMPLE_RATE
        for _ in range(SAMPLES_PER_BIT):
            samples.append(math.sin(phase))
            phase += dphase
            if phase > 2.0 * math.pi:
                phase -= 2.0 * math.pi
    return samples


def samples_to_wav_bytes(samples) -> bytes:
    buf = bytearray()
    peak = AMPLITUDE * FULL_SCALE
    for s in samples:
        buf.extend(struct.pack('<h', int(s * peak)))
    return bytes(buf)


def encode_to_wav_bytes(text: str) -> bytes:
    """Encode text -> in-memory WAV bytes (no disk needed, ideal for web)."""
    frame = GOLD_CODE + text_to_binary(text)
    audio = samples_to_wav_bytes(encode_bits_to_samples(frame))
    bio = io.BytesIO()
    with wave.open(bio, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio)
    return bio.getvalue()


# ───────────────────────────── DECODING ─────────────────────────────
def goertzel(samples, freq, sample_rate=SAMPLE_RATE) -> float:
    n = len(samples)
    if n == 0:
        return 0.0
    k = 0.5 + (n * freq) / sample_rate
    w = (2.0 * math.pi / n) * int(k)
    coeff = 2.0 * math.cos(w)
    s_prev = s_prev2 = 0.0
    for x in samples:
        s = x + coeff * s_prev - s_prev2
        s_prev2 = s_prev
        s_prev = s
    return s_prev2 ** 2 + s_prev ** 2 - coeff * s_prev * s_prev2


def read_wav_samples_from_bytes(data: bytes):
    with wave.open(io.BytesIO(data), 'rb') as wf:
        ch = wf.getnchannels()
        sw = wf.getsampwidth()
        fr = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    if sw != 2:
        raise ValueError("Sanctioned input is 16-bit PCM only.")
    ints = struct.unpack('<' + 'h' * (len(raw) // 2), raw)
    if ch > 1:
        ints = [sum(ints[i:i + ch]) / ch for i in range(0, len(ints), ch)]
    inv = 1.0 / FULL_SCALE
    return [v * inv for v in ints], fr


def demodulate_bits(samples, sample_rate=SAMPLE_RATE) -> str:
    spb = int(round(sample_rate * BIT_DURATION))
    bits = []
    for start in range(0, len(samples) - spb + 1, spb):
        window = samples[start:start + spb]
        e0 = goertzel(window, FREQ_ZERO, sample_rate)
        e1 = goertzel(window, FREQ_ONE, sample_rate)
        bits.append('1' if e1 > e0 else '0')
    return ''.join(bits)


def find_preamble(bits: str, max_errors: int = 4) -> int:
    glen = len(GOLD_CODE)
    best_idx, best_err = -1, glen + 1
    for i in range(0, len(bits) - glen + 1):
        err = sum(1 for a, b in zip(bits[i:i + glen], GOLD_CODE) if a != b)
        if err < best_err:
            best_err, best_idx = err, i
            if err == 0:
                break
    if best_idx == -1 or best_err > max_errors:
        return -1
    return best_idx + glen


def decode_from_wav_bytes(data: bytes) -> dict:
    samples, fr = read_wav_samples_from_bytes(data)
    bits = demodulate_bits(samples, fr)
    start = find_preamble(bits)
    if start < 0:
        return {'ok': False, 'text': '',
                'reason': 'Litany of sync not found — corrupt or alien data.'}
    return {'ok': True, 'text': binary_to_text(bits[start:])}
