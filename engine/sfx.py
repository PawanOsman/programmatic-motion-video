"""sfx.py: music and sound effects synthesised with numpy, placed on the same timeline as the picture.

Every sound is a numpy array (mono, or stereo with shape (2, n)) at 48 kHz. Mixer.add() puts one at a
time in seconds; backing() writes a whole music bed; master() mixes, adds reverb, limits and
normalises loudness in two passes.

    m = sfx.Mixer(duration)
    info = sfx.backing(m, bpm=112, key='A', mode='minor', style='pulse')   # music bed on a beat grid
    m.add(sfx.whoosh(0.5), t_cut - 0.5, 0.5)                             # peaks exactly on the cut
    sfx.type_clicks(m, 'Hello world', t0=1.0, cps=16)                    # one key click per character
    wav = m.master('audio.wav', lufs=-14)

Needs numpy, scipy and ffmpeg.
"""
import json
import math
import os
import re
import subprocess

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt, sosfilt_zi

SR = 48000
rng = np.random.default_rng(7)


# ---- helpers ---------------------------------------------------------------------------------

def secs(d):
    return np.arange(int(d * SR)) / SR


def lp(x, fc, o=2):
    return sosfilt(butter(o, min(fc, SR * 0.45), 'lp', fs=SR, output='sos'), x)


def hp(x, fc, o=2):
    return sosfilt(butter(o, fc, 'hp', fs=SR, output='sos'), x)


def bp(x, lo, hi, o=2):
    return sosfilt(butter(o, [lo, min(hi, SR * 0.45)], 'bp', fs=SR, output='sos'), x)


def env(n, attack=0.005, release=0.05, total=None):
    """Linear attack and release envelope over n samples."""
    t = np.arange(n) / SR
    total = total or n / SR
    return np.minimum(1, t / max(attack, 1e-4)) * np.clip((total - t) / max(release, 1e-4), 0, 1)


def stereo(x, pan=0.0):
    """Mono -> stereo with an equal-power pan (-1 left .. 1 right)."""
    x = np.asarray(x, float)
    if x.ndim == 2:
        return x
    th = (pan + 1) * math.pi / 4
    return np.stack([x * math.cos(th), x * math.sin(th)]) * math.sqrt(2)


# ---- notes and harmony -----------------------------------------------------------------------

NOTES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
SCALES = {
    'major': [0, 2, 4, 5, 7, 9, 11], 'minor': [0, 2, 3, 5, 7, 8, 10], 'dorian': [0, 2, 3, 5, 7, 9, 10],
    'mixolydian': [0, 2, 4, 5, 7, 9, 10], 'lydian': [0, 2, 4, 6, 7, 9, 11], 'phrygian': [0, 1, 3, 5, 7, 8, 10],
}
# chord progressions as scale degrees (0 = the key's own chord)
PROGRESSIONS = {
    'minor': [0, 5, 2, 6],        # i  VI  III VII  (epic, tech)
    'minor-soft': [0, 3, 5, 4],   # i  iv  VI  v
    'major': [0, 4, 5, 3],        # I  V   vi  IV   (bright, pop)
    'major-lift': [0, 3, 5, 4],   # I  IV  vi  V
    'calm': [0, 3, 0, 4],         # I  IV  I   V
}


def midi(note):
    """'A4' -> 69, 'C#3', 'Eb5'."""
    m = re.fullmatch(r'([A-G])([#b]?)(-?\d)', note)
    if not m:
        raise ValueError(f'bad note {note!r}')
    return NOTES[m[1]] + {'#': 1, 'b': -1, '': 0}[m[2]] + 12 * (int(m[3]) + 1)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def hz(note):
    """'A4' -> 440.0, 'C#3', 'Eb5'."""
    return mtof(midi(note))


def chord(key='A', mode='minor', degree=0, octave=3, size=3, inversion=0):
    """Frequencies of the triad (size=3) or seventh chord (size=4) on a scale degree of a key."""
    root = midi(f'{key}{octave}') if len(key) <= 2 else midi(key)
    sc = SCALES[mode]
    notes = []
    for k in range(size):
        i = degree + 2 * k
        notes.append(root + sc[i % 7] + 12 * (i // 7))
    for _ in range(inversion):
        notes = notes[1:] + [notes[0] + 12]
    return [mtof(n) for n in notes]


# ---- oscillators and instruments -------------------------------------------------------------

def saw(freq, n):
    """Band-limited sawtooth (polyBLEP): bright without aliasing whistles. freq may be an array."""
    f = np.broadcast_to(np.asarray(freq, float), (n,)).copy()
    p = (np.cumsum(f) / SR) % 1.0
    dt = f / SR
    out = 2 * p - 1
    m = p < dt
    x = p[m] / dt[m]
    out[m] -= x + x - x * x - 1
    m = p > 1 - dt
    x = (p[m] - 1) / dt[m]
    out[m] -= x * x + x + x + 1
    return out


def sine(f, dur, attack=0.005, release=0.05):
    t = secs(dur)
    return np.sin(2 * np.pi * f * t) * env(len(t), attack, release)


def kick(dur=0.45, f0=150, f1=45, punch=1.6):
    t = secs(dur)
    f = f1 + (f0 - f1) * np.exp(-t * 30)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6.5) + 0.3 * rng.standard_normal(len(t)) * np.exp(-t * 350)
    return np.tanh(punch * s)


def snare(dur=0.2):
    t = secs(dur)
    return (bp(rng.standard_normal(len(t)), 1500, 7500) * np.exp(-t * 30) * 1.3
            + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 38) * 0.7)


def clap():
    t = secs(0.4)
    n = bp(rng.standard_normal(len(t)), 900, 2800)
    e = np.zeros_like(t)
    for o in (0, 0.010, 0.021):
        e += (t >= o) * np.exp(-np.clip(t - o, 0, None) * 140) * 0.7
    return n * (e + (t >= 0.03) * np.exp(-np.clip(t - 0.03, 0, None) * 15)) * 2.4


def hat(dur=0.05, decay=75):
    t = secs(dur)
    return hp(rng.standard_normal(len(t)), 7500, 4) * np.exp(-t * decay)


def open_hat(dur=0.35):
    return hat(dur, 12) * 0.8


def shaker(dur=0.09):
    t = secs(dur)
    return bp(rng.standard_normal(len(t)), 5000, 12000) * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2 * 0.8


def tom(f=110, dur=0.35):
    t = secs(dur)
    ff = f * (1 + 0.6 * np.exp(-t * 25))
    return np.sin(2 * np.pi * np.cumsum(ff) / SR) * np.exp(-t * 9)


def bass(f, dur=0.2):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return (lp(saw(f, n) * 0.6, 420) + np.sin(2 * np.pi * f * t) * 0.9) * env(n, 0.004, 0.015) * np.exp(-t * 2.5)


def sub(f, dur=1.0):
    """Pure sine sub-bass with soft edges: felt more than heard."""
    return sine(f, dur, 0.02, 0.1) * 0.9


def pluck(f, dur=0.35):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = saw(f, n) * 0.6 + saw(f * 1.006, n) * 0.4
    e = np.exp(-t * 28)
    return (lp(s, 5000) * e + lp(s, f * 1.6) * (1 - e)) * np.exp(-t * 10) * env(n, 0.002, 0.02)


def pad(freqs, dur, cutoff=1300, attack=0.3, release=0.2):
    """Warm detuned-saw chord, stereo."""
    n = int(dur * SR)
    L = np.zeros(n)
    R = np.zeros(n)
    for f in freqs:
        L += saw(f * 0.996, n) + saw(f * 1.001, n)
        R += saw(f * 1.004, n) + saw(f * 0.999, n)
    e = env(n, attack, release) / (2 * len(freqs))
    return np.stack([lp(L, cutoff) * e, lp(R, cutoff) * e])


def bell(f, dur=1.2):
    t = secs(dur)
    idx = 2.4 * np.exp(-t * 7)
    return np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * 3.5 * t)) * np.exp(-t * 4) * env(len(t), 0.001, 0.05)


def epiano(f, dur=0.8):
    """Soft electric-piano tone (two-operator FM) for corporate and calm beds."""
    t = secs(dur)
    idx = 1.3 * np.exp(-t * 5)
    tone = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t))
    tone += 0.25 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 6)
    return tone * np.exp(-t * 2.2) * env(len(t), 0.003, 0.08) * (1 + 0.08 * np.sin(2 * np.pi * 5 * t))


# ---- sound design for motion -----------------------------------------------------------------

def click(v=1.0):
    """UI click / keyboard tick."""
    t = secs(0.06)
    f = rng.uniform(2800, 4200)
    return (bp(rng.standard_normal(len(t)), f * 0.7, f * 1.3) * np.exp(-t * 260) * 1.4
            + np.sin(2 * np.pi * rng.uniform(180, 260) * t) * np.exp(-t * 90) * 0.5) * v


def blip(f=880, dur=0.25, drop=0.6):
    """Soft pop for things appearing."""
    t = secs(dur)
    ph = 2 * np.pi * np.cumsum(f * (1 + drop * np.exp(-t * 55))) / SR
    return (np.sin(ph) + 0.2 * np.sin(2 * ph)) * np.exp(-t * 15) * env(len(t), 0.001, 0.02)


def whoosh(dur=0.4, f0=300, f1=6000, pan0=-0.6, pan1=0.6, curve=2.0):
    """Filtered-noise sweep for moves and transitions. It peaks at the END, so start it dur before the hit."""
    n = int((dur + 0.08) * SR)
    x = rng.standard_normal(n)
    y = np.zeros(n)
    blk = 512
    zi = None
    for i in range(0, n, blk):
        k = min(1.0, i / (dur * SR))
        fc = f0 * (f1 / f0) ** k
        sos = butter(2, [fc * 0.7, min(fc * 1.4, SR * 0.45)], 'bp', fs=SR, output='sos')
        if zi is None:
            zi = sosfilt_zi(sos) * 0
        y[i:i + blk], zi = sosfilt(sos, x[i:i + blk], zi=zi)
    tc = np.clip(np.arange(n) / (dur * SR), 0, 1)
    y *= tc ** curve * np.where(np.arange(n) > dur * SR, np.exp(-(np.arange(n) / SR - dur) * 60), 1)
    th = (pan0 + (pan1 - pan0) * tc + 1) * np.pi / 4
    return np.stack([y * np.cos(th), y * np.sin(th)]) * math.sqrt(2) * 3


def swell(dur=1.5):
    """Reverse-cymbal-like noise swell that ends on its last sample: start it dur before a hit."""
    t = secs(dur)
    return hp(rng.standard_normal(len(t)), 3000) * (t / dur) ** 3 * 0.8


def riser(dur=2.0, f0=110, f1=880):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return lp(saw(f0 * (f1 / f0) ** (t / dur), n), 3000) * (t / dur) ** 2 * 0.5


def impact(dur=1.6):
    t = secs(dur)
    f = 40 + 35 * np.exp(-t * 6)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)
    return np.tanh(1.5 * (boom + hp(rng.standard_normal(len(t)), 2500) * np.exp(-t * 9) * 0.3))


def chime(kind='success'):
    """Short interface cues: 'success' (rising), 'notify' (two soft tones), 'error' (low double)."""
    seq = {'success': [('E6', 0.0), ('B6', 0.09)], 'notify': [('A5', 0.0), ('E6', 0.13)],
           'error': [('C4', 0.0), ('C4', 0.14)]}[kind]
    out = np.zeros(int(1.3 * SR))
    for note, at in seq:
        tone = bell(hz(note), 1.0) if kind != 'error' else pluck(hz(note), 0.3)
        i = int(at * SR)
        out[i:i + len(tone)] += tone[:len(out) - i] * 0.6
    return out


def sparkle(dur=0.9, notes=('E6', 'G#6', 'B6', 'E7')):
    """A quick glittering arpeggio for reveals and 'magic' moments."""
    out = np.zeros(int((dur + 0.8) * SR))
    for k, n in enumerate(notes):
        tone = bell(hz(n), 0.8) * 0.4
        i = int(k * dur / len(notes) * SR)
        out[i:i + len(tone)] += tone[:len(out) - i]
    return out


# ---- mixer -----------------------------------------------------------------------------------

class Mixer:
    """Buses: 'music', 'fx', 'drums', 'voice'. add(sig, time_s, ...) places a sound.
    duck(times) sidechains the music under kicks or voice. loop=True wraps sounds and reverb tails
    that run past the end back to the start, so a looping video has no audible seam.
    master() mixes, limits and normalises loudness; write() only mixes."""
    BUSES = ('music', 'fx', 'drums', 'voice')

    def __init__(self, duration, loop=False):
        self.n = int(round(duration * SR))
        self.duration, self.loop = duration, loop
        self.bus = {k: np.zeros((2, self.n)) for k in self.BUSES}
        self.send = np.zeros((2, self.n))
        self.ducks = []
        self.fades = []

    def _place(self, arr, i0, part):
        n = part.shape[1]
        if self.loop:
            i0 %= self.n
            while n > 0:
                k = min(n, self.n - i0)
                arr[:, i0:i0 + k] += part[:, :k]
                part = part[:, k:]
                n -= k
                i0 = 0
            return
        if i0 < 0:
            part = part[:, -i0:]
            i0 = 0
        k = min(part.shape[1], self.n - i0)
        if k > 0:
            arr[:, i0:i0 + k] += part[:, :k]

    def add(self, sig, t, gain=1.0, pan=0.0, reverb=0.0, bus='fx'):
        """Place a sound at time t (seconds). reverb is the send level (0..1)."""
        sig = np.asarray(sig, float)
        sig = np.stack([sig, sig]) if sig.ndim == 1 else sig
        gl = math.cos((pan + 1) * math.pi / 4) * math.sqrt(2)
        gr = math.sin((pan + 1) * math.pi / 4) * math.sqrt(2)
        part = sig * gain * np.array([[gl], [gr]])
        i0 = int(round(t * SR))
        self._place(self.bus[bus], i0, part)
        if reverb:
            self._place(self.send, i0, part * reverb)

    def duck(self, times, depth=0.6, release=0.09):
        """Dip the music bus at these times (kicks, voice onsets)."""
        self.ducks += [(t, depth, release) for t in times]

    def fade(self, bus, t0, t1, g0=1.0, g1=0.0):
        """Gain ramp on a bus from g0 at t0 to g1 at t1, holding g0 before and g1 after.
        fade('music', end - 2, end) fades out; fade('music', 0, 1, 0, 1) fades in."""
        self.fades.append((bus, t0, t1, g0, g1))

    def _fade_gain(self, bus):
        g = np.ones(self.n)
        tt = np.arange(self.n) / SR
        for b, t0, t1, g0, g1 in self.fades:
            if b == bus:
                g *= g0 + (g1 - g0) * np.clip((tt - t0) / max(t1 - t0, 1e-6), 0, 1)
        return g

    def _mix(self):
        music = self.bus['music'].copy()
        g = np.ones(self.n)
        for t, depth, rel in self.ducks:
            i0 = int(t * SR) % self.n if self.loop else int(t * SR)
            k = min(int(0.4 * SR), self.n - i0)
            if k > 0:
                g[i0:i0 + k] *= 1 - depth * np.exp(-np.arange(k) / SR / rel)
        ir_t = np.arange(int(2.2 * SR)) / SR
        r = np.random.default_rng(3)
        ir = np.stack([lp(r.standard_normal(len(ir_t)), 5000) * np.exp(-ir_t * 3.0) for _ in range(2)])
        ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True))
        wet = np.stack([fftconvolve(self.send[i], ir[i]) for i in range(2)]) * 0.5
        if self.loop:   # reverb tails wrap to the start
            tail = wet[:, self.n:]
            wet = wet[:, :self.n].copy()
            k = min(tail.shape[1], self.n)
            wet[:, :k] += tail[:, :k]
        else:
            wet = wet[:, :self.n]
        if self.fades:
            music = music * self._fade_gain('music')
            drums = self.bus['drums'] * self._fade_gain('drums')
            fx = self.bus['fx'] * self._fade_gain('fx')
        else:
            drums, fx = self.bus['drums'], self.bus['fx']
        mix = music * g + fx + drums + self.bus['voice'] + wet
        mix = np.stack([hp(mix[i], 28) for i in range(2)])
        peak = max(1e-9, np.abs(mix).max())
        mix = mix / peak
        return np.tanh(1.4 * mix) / np.tanh(1.4) * 0.9   # gentle soft-clip limiter

    def write(self, path, loop=None):
        """Mix to a 32-bit float WAV (no loudness normalisation)."""
        if loop is not None:
            self.loop = loop
        wavfile.write(path, SR, self._mix().T.astype(np.float32))
        return path

    def master(self, path, lufs=-14.0, tp=-1.5):
        """Mix, then two-pass loudness normalisation to `lufs` (see loudnorm). Returns path."""
        raw = os.path.splitext(path)[0] + '_raw.wav'
        self.write(raw)
        loudnorm(raw, path, lufs, tp)
        os.remove(raw)
        return path


def loudnorm(src, dst, lufs=-14.0, tp=-1.5, lra=11.0):
    """Two-pass EBU R128 loudness normalisation: -14 LUFS web/social, -16 podcasts, -23 EBU broadcast,
    -24 LKFS US broadcast (ATSC A/85). tp=-1.5 leaves room for the peaks AAC encoding adds."""
    p1 = subprocess.run(['ffmpeg', '-hide_banner', '-i', src, '-af', f'loudnorm=I={lufs}:TP={tp}:LRA={lra}:print_format=json',
                         '-f', 'null', '-'], capture_output=True, text=True, encoding='utf-8', errors='replace').stderr
    m = json.loads(p1[p1.rindex('{'):p1.rindex('}') + 1])
    af = (f"loudnorm=I={lufs}:TP={tp}:LRA={lra}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-af', af, '-ar', str(SR), '-c:a', 'pcm_s24le', dst], check=True)
    return dst


def loudness(path):
    """Integrated loudness (LUFS) and true peak (dBTP) of a file, for checks before delivery."""
    out = subprocess.run(['ffmpeg', '-hide_banner', '-i', path, '-af', 'loudnorm=print_format=json', '-f', 'null', '-'],
                         capture_output=True, text=True, encoding='utf-8', errors='replace').stderr
    m = json.loads(out[out.rindex('{'):out.rindex('}') + 1])
    return dict(lufs=float(m['input_i']), true_peak=float(m['input_tp']))


# ---- music beds ------------------------------------------------------------------------------

STYLES = ('ambient', 'pulse', 'drive', 'corporate', 'lofi')


def backing(m, start=0.0, end=None, bpm=110, key='A', mode='minor', progression=None, style='pulse',
            gain=0.8, seed=1, fade_in=0.0, fade_out=2.0, octave=3):
    """Write a music bed into mixer m between start and end (seconds; end defaults to the mix length).

    style: 'ambient' (pads and bells, no drums: signage, calm explainers), 'pulse' (soft kick, hats,
    bass, pad: product demos), 'drive' (four-on-the-floor, claps, arpeggio: promos, reels),
    'corporate' (electric piano, light drums), 'lofi' (slow swing, soft keys).
    Returns timing facts to sync the picture: dict(bpm, beat, bar, bars=[bar start times],
    beats=[beat times], chords=[[freqs] per bar]). With m.loop=True, make the length a whole
    number of bars (bar = 240 / bpm seconds) so the music loops cleanly."""
    r = np.random.default_rng(seed)
    end = m.duration if end is None else end
    beat = 60.0 / bpm
    bar = 4 * beat
    n_bars = max(1, int(math.ceil((end - start) / bar - 1e-6)))
    if isinstance(progression, (list, tuple)):
        prog = list(progression)
    else:
        prog = PROGRESSIONS[progression or ('major' if mode in ('major', 'lydian', 'mixolydian') else 'minor')]

    if not m.loop:   # loops never fade; one-shot beds fade with bus automation
        for bus in ('music', 'drums'):
            if fade_in > 0:
                m.fade(bus, start, start + fade_in, 0.0, 1.0)
            if fade_out > 0:
                m.fade(bus, end - fade_out, end, 1.0, 0.0)

    kicks, bars, beats, chords = [], [], [], []
    for b in range(n_bars):
        t0 = start + b * bar
        deg = prog[b % len(prog)]
        ch = chord(key, mode, deg, octave, 3)
        bars.append(t0)
        chords.append(ch)
        beats += [t0 + k * beat for k in range(4)]
        root = chord(key, mode, deg, octave - 1, 1)[0]
        top = chord(key, mode, deg, octave + 1, 3)
        g = gain
        if style in ('ambient', 'pulse', 'corporate', 'lofi'):
            m.add(pad(ch + [ch[0] * 2], bar + 0.4, 900 if style == 'ambient' else 1300, 0.6, 0.4), t0,
                  0.55 * g, reverb=0.35, bus='music')
        if style == 'drive':
            m.add(pad(ch, bar + 0.2, 1800), t0, 0.35 * g, reverb=0.25, bus='music')
        # bass
        if style == 'ambient':
            m.add(sub(root, bar), t0, 0.35 * g, bus='music')
        elif style == 'pulse':
            for k in range(8):
                m.add(bass(root, beat * 0.45), t0 + k * beat / 2, (0.55 if k % 2 == 0 else 0.4) * g, bus='music')
        elif style == 'drive':
            for k in range(8):
                if k % 2 == 1:
                    m.add(bass(root, beat * 0.45), t0 + k * beat / 2, 0.6 * g, bus='music')
        elif style in ('corporate', 'lofi'):
            for k in range(4):
                m.add(bass(root, beat * 0.9), t0 + k * beat, 0.45 * g, bus='music')
        # melody layer
        if style in ('pulse', 'drive'):
            steps = 16 if style == 'drive' else 8
            pattern = [0, 1, 2, 1, 0, 2, 1, 2]
            for k in range(steps):
                f = top[pattern[k % len(pattern)]]
                m.add(pluck(f, 0.3), t0 + k * bar / steps, (0.16 if style == 'drive' else 0.2) * g,
                      pan=0.35 * math.sin(k * 1.3), reverb=0.3, bus='music')
        elif style in ('corporate', 'lofi'):
            for k in range(4):
                sw = 0.08 * beat if (style == 'lofi' and k % 2) else 0.0
                for f in (ch if k % 2 == 0 else ch[1:] + [ch[0] * 2]):
                    m.add(epiano(f * 2, beat * 1.4), t0 + k * beat + sw, 0.13 * g, reverb=0.3, bus='music')
        elif style == 'ambient':
            for _ in range(2):
                k = int(r.integers(0, 8))
                f = top[int(r.integers(0, 3))] * 2
                m.add(bell(f, 1.6), t0 + k * beat / 2, 0.12 * g, pan=float(r.uniform(-0.6, 0.6)), reverb=0.6, bus='music')
        # drums
        if style == 'pulse':
            for k in (0, 2):
                m.add(kick(), t0 + k * beat, 0.7 * g, bus='drums'); kicks.append(t0 + k * beat)
            for k in (1, 3):
                m.add(clap(), t0 + k * beat, 0.18 * g, reverb=0.2, bus='drums')
            for k in range(8):
                m.add(hat(), t0 + k * beat / 2, (0.12 if k % 2 else 0.07) * g, pan=0.3, bus='drums')
        elif style == 'drive':
            for k in range(4):
                m.add(kick(), t0 + k * beat, 0.8 * g, bus='drums'); kicks.append(t0 + k * beat)
                m.add(open_hat(), t0 + k * beat + beat / 2, 0.14 * g, pan=0.25, bus='drums')
            for k in (1, 3):
                m.add(clap(), t0 + k * beat, 0.35 * g, reverb=0.25, bus='drums')
            for k in range(16):
                m.add(hat(0.03, 120), t0 + k * beat / 4, 0.05 * g, pan=-0.3, bus='drums')
        elif style == 'corporate':
            for k in (0, 2):
                m.add(kick(0.35, 120, 50, 1.2), t0 + k * beat, 0.5 * g, bus='drums'); kicks.append(t0 + k * beat)
            for k in (1, 3):
                m.add(snare(), t0 + k * beat, 0.16 * g, reverb=0.3, bus='drums')
            for k in range(8):
                m.add(shaker(), t0 + k * beat / 2, 0.1 * g, pan=0.3, bus='drums')
        elif style == 'lofi':
            for k, off in ((0, 0), (2, 0.5)):
                m.add(kick(0.4, 110, 45, 1.3), t0 + (k + off) * beat, 0.45 * g, bus='drums'); kicks.append(t0 + (k + off) * beat)
            for k in (1, 3):
                m.add(snare(0.25), t0 + k * beat, 0.14 * g, reverb=0.35, bus='drums')
            for k in range(8):
                sw = 0.1 * beat if k % 2 else 0.0
                m.add(hat(0.04, 90), t0 + k * beat / 2 + sw, 0.06 * g, pan=0.2, bus='drums')
    if kicks:
        m.duck(kicks, depth=0.45)
    return dict(bpm=bpm, beat=beat, bar=bar, bars=bars, beats=beats, chords=chords)


def type_clicks(m, text_or_count, t0, cps=16.0, gain=0.25, pan=0.1):
    """One key click per typed character (spaces get a softer click)."""
    chars = text_or_count if isinstance(text_or_count, str) else 'x' * int(text_or_count)
    for i, ch in enumerate(chars):
        m.add(click(0.55 if ch == ' ' else 0.85), t0 + i / cps, gain, pan=pan)


# ---- audio files and analysis ----------------------------------------------------------------

def load(path, sr=SR):
    """Decode any audio or video file's sound to a stereo float array (2, n) at sr."""
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '2', '-ar', str(sr), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).T.astype(float)


def analyze(sig_or_path, fps=30, bands=24, fmin=40.0, fmax=12000.0, attack=0.5, release=0.12, per_band=True):
    """Per-video-frame loudness and spectrum for audiograms and visualisers.
    Returns dict(level=(frames,), bands=(frames, bands)), both smoothed and scaled to 0..1.
    attack/release (0..1) set how fast values rise and fall between frames. per_band scales each band
    by its own range, so quiet high bands still move (set False for a true spectrum shape)."""
    x = load(sig_or_path) if isinstance(sig_or_path, str) else np.asarray(sig_or_path, float)
    mono = x.mean(axis=0) if x.ndim == 2 else x
    hop = SR / fps
    n_frames = int(len(mono) / hop)
    win = 2048
    w = np.hanning(win)
    edges = np.geomspace(fmin, fmax, bands + 1)
    freqs = np.fft.rfftfreq(win, 1 / SR)
    idx = [np.where((freqs >= edges[k]) & (freqs < edges[k + 1]))[0] for k in range(bands)]
    level = np.zeros(n_frames)
    spec = np.zeros((n_frames, bands))
    for f in range(n_frames):
        c = int(f * hop)
        seg_ = mono[max(0, c - win // 2): c + win // 2]
        if len(seg_) < win:
            seg_ = np.pad(seg_, (0, win - len(seg_)))
        level[f] = math.sqrt(float(np.mean(seg_ ** 2)))
        mag = np.abs(np.fft.rfft(seg_ * w))
        spec[f] = [mag[i].mean() if len(i) else 0.0 for i in idx]
    level = level / (level.max() or 1)
    spec = np.log1p(spec * 10)
    if per_band:
        lo = np.percentile(spec, 5, axis=0)
        hi = np.percentile(spec, 98, axis=0)
        spec = (spec - lo) / np.maximum(hi - lo, 1e-9)
    else:
        spec = spec / (np.percentile(spec, 99) or 1)
    spec = np.clip(spec, 0, 1)
    for arr in (level, spec):          # attack/release smoothing, frame to frame
        for f in range(1, n_frames):
            a = np.where(arr[f] > arr[f - 1], attack, release)
            arr[f] = arr[f - 1] + (arr[f] - arr[f - 1]) * a
    return dict(level=level, bands=spec)
