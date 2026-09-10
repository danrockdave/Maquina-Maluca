"""
Procedural chiptune synthesizer: composes the soundtrack and every sound effect
with numpy and saves them as WAV files in assets/audio/.

    python -m tools.make_audio
"""
import os
import wave
import numpy as np

SR = 22050
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'audio')

_NOTE_INDEX = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


# ---------------------------------------------------------------- basics
def note_freq(name):
    """'C4' -> 261.63 Hz, 'F#3', 'Bb2' also accepted."""
    letter = name[0].upper()
    rest = name[1:]
    semitone = _NOTE_INDEX[letter]
    if rest.startswith('#'):
        semitone += 1
        rest = rest[1:]
    elif rest.startswith('b'):
        semitone -= 1
        rest = rest[1:]
    octave = int(rest)
    midi = 12 * (octave + 1) + semitone
    return 440.0 * 2 ** ((midi - 69) / 12)


def osc(kind, freq, n, duty=0.5, sweep=1.0):
    """Waveform of n samples. sweep multiplies the frequency across the note."""
    t = np.arange(n) / SR
    if sweep != 1.0:
        f = freq * sweep ** (t / (n / SR))
        phase = np.cumsum(f) / SR
    else:
        phase = freq * t
    frac = phase % 1.0
    if kind == 'square':
        return np.where(frac < duty, 1.0, -1.0)
    if kind == 'triangle':
        return 4.0 * np.abs(frac - 0.5) - 1.0
    if kind == 'saw':
        return 2.0 * frac - 1.0
    if kind == 'sine':
        return np.sin(2 * np.pi * phase)
    if kind == 'noise':
        rng = np.random.default_rng(int(freq) + n)
        return rng.uniform(-1.0, 1.0, n)
    raise ValueError(kind)


def adsr(n, attack=0.005, decay=0.05, sustain=0.7, release=0.05):
    a, d, r = int(attack * SR), int(decay * SR), int(release * SR)
    a, d, r = min(a, n), min(d, n), min(r, n)
    env = np.ones(n) * sustain
    env[:a] = np.linspace(0, 1, a, endpoint=False) if a else env[:a]
    if d:
        env[a:a + d] = np.linspace(1, sustain, d, endpoint=False)[:max(0, min(d, n - a))]
    if r:
        env[n - r:] *= np.linspace(1, 0, r)
    return env


def tone(freq, dur, kind='square', vol=0.3, duty=0.5, sweep=1.0, env=None):
    n = max(1, int(dur * SR))
    env = adsr(n, **(env or {}))
    return osc(kind, freq, n, duty, sweep) * env * vol


def silence(dur):
    return np.zeros(max(1, int(dur * SR)))


def lowpass(x, alpha=0.2):
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += alpha * (v - acc)
        y[i] = acc
    return y


def mix(*tracks):
    n = max(len(t) for t in tracks)
    out = np.zeros(n)
    for t in tracks:
        out[:len(t)] += t
    return out


def normalize(x, peak=0.85):
    m = np.abs(x).max()
    return x * (peak / m) if m > 0 else x


def concat(parts):
    return np.concatenate(parts) if parts else np.zeros(1)


def sequence(notes, bpm, kind='square', vol=0.25, duty=0.5, env=None, unit=0.5):
    """notes: list of (name or 'R', length) where length is in beats * unit."""
    beat = 60.0 / bpm
    out = []
    for name, length in notes:
        dur = length * unit * beat
        if name == 'R':
            out.append(silence(dur))
        else:
            out.append(tone(note_freq(name), dur, kind, vol, duty, env=env))
    return concat(out)


def write_wav(name, data):
    os.makedirs(OUT_DIR, exist_ok=True)
    data = np.clip(data, -1.0, 1.0)
    pcm = (data * 32767).astype('<i2')
    path = os.path.join(OUT_DIR, name)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print("saved", path)


# ---------------------------------------------------------------- drums
def kick(dur=0.12):
    return tone(150.0, dur, 'sine', 0.6, sweep=0.25, env={'attack': 0.001, 'decay': 0.08, 'sustain': 0.2, 'release': 0.03})


def hihat(dur=0.04):
    return tone(8000.0, dur, 'noise', 0.12, env={'attack': 0.001, 'decay': 0.03, 'sustain': 0.1, 'release': 0.01})


def snare(dur=0.1):
    return mix(tone(4000.0, dur, 'noise', 0.25, env={'decay': 0.06, 'sustain': 0.2}),
               tone(200.0, dur * 0.6, 'triangle', 0.3, sweep=0.5))


def drum_track(pattern, bpm, bars, unit=0.5):
    """pattern: string per 8th note, chars: k=kick s=snare h=hihat .=rest"""
    step = 60.0 / bpm * unit
    n = int(step * len(pattern) * bars * SR) + SR
    out = np.zeros(n)
    for bar in range(bars):
        for i, ch in enumerate(pattern):
            start = int(((bar * len(pattern)) + i) * step * SR)
            hit = None
            if ch == 'k':
                hit = kick()
            elif ch == 's':
                hit = snare()
            elif ch == 'h':
                hit = hihat()
            elif ch == 'x':
                hit = mix(kick(), hihat())
            if hit is not None:
                out[start:start + len(hit)] += hit[:max(0, min(len(hit), n - start))]
    return out


# ---------------------------------------------------------------- music
def music_game():
    """Upbeat loop for the gameplay (C major, 150 bpm, 16 bars)."""
    bpm = 150
    lead_env = {'attack': 0.005, 'decay': 0.06, 'sustain': 0.6, 'release': 0.03}
    # Each tuple = (note, eighths)
    a = [('E5', 1), ('G5', 1), ('A5', 2), ('G5', 1), ('E5', 1), ('D5', 2),
         ('C5', 1), ('D5', 1), ('E5', 2), ('G5', 2), ('R', 2),
         ('A5', 1), ('G5', 1), ('E5', 2), ('D5', 1), ('C5', 1), ('D5', 2),
         ('E5', 1), ('D5', 1), ('C5', 2), ('A4', 2), ('R', 2)]
    b = [('C5', 1), ('E5', 1), ('G5', 1), ('C6', 1), ('B5', 2), ('G5', 2),
         ('A5', 1), ('G5', 1), ('E5', 1), ('D5', 1), ('E5', 2), ('R', 2),
         ('F5', 1), ('E5', 1), ('D5', 1), ('C5', 1), ('D5', 2), ('E5', 2),
         ('G5', 1), ('E5', 1), ('D5', 2), ('C5', 2), ('R', 2)]
    lead = sequence(a + a + b + b, bpm, 'square', 0.16, duty=0.25, env=lead_env)

    bass_env = {'attack': 0.003, 'decay': 0.1, 'sustain': 0.5, 'release': 0.05}
    bass_bar = lambda root, fifth: [(root, 1), (root, 1), (fifth, 1), (root, 1),
                                    (root, 1), (fifth, 1), (root, 1), (fifth, 1)]
    prog = [('C3', 'G3'), ('C3', 'G3'), ('A2', 'E3'), ('A2', 'E3'),
            ('F2', 'C3'), ('F2', 'C3'), ('G2', 'D3'), ('G2', 'D3')] * 2
    bass_notes = []
    for root, fifth in prog:
        bass_notes += bass_bar(root, fifth)
    bass = sequence(bass_notes, bpm, 'triangle', 0.3, env=bass_env)

    chord_env = {'attack': 0.01, 'decay': 0.2, 'sustain': 0.2, 'release': 0.1}
    chords = []
    for root, fifth in prog:
        chords += [('R', 1), (fifth, 1), ('R', 1), (fifth, 1), ('R', 1), (fifth, 1), ('R', 1), (fifth, 1)]
    harm = sequence(chords, bpm, 'square', 0.06, duty=0.5, env=chord_env)

    drums = drum_track('khshkhsh', bpm, 16)
    n = len(lead)
    return normalize(mix(lead, bass[:n], harm[:n], drums[:n]), 0.8)


def music_menu():
    """Calm arpeggio loop for the menus (90 bpm, 8 bars)."""
    bpm = 90
    env = {'attack': 0.01, 'decay': 0.15, 'sustain': 0.4, 'release': 0.1}
    chords = [['C4', 'E4', 'G4', 'B4'], ['A3', 'C4', 'E4', 'G4'],
              ['F3', 'A3', 'C4', 'E4'], ['G3', 'B3', 'D4', 'F4']] * 2
    arp = []
    for chord in chords:
        for note in chord + chord[::-1]:
            arp.append((note, 1))
    lead = sequence(arp, bpm, 'triangle', 0.28, env=env)
    pad_env = {'attack': 0.3, 'decay': 0.3, 'sustain': 0.6, 'release': 0.4}
    pad = sequence([(c[0], 8) for c in chords], bpm, 'sine', 0.18, env=pad_env)
    n = len(lead)
    return normalize(mix(lead, pad[:n]), 0.7)


def jingle_win():
    bpm = 170
    env = {'attack': 0.005, 'decay': 0.08, 'sustain': 0.6, 'release': 0.05}
    lead = sequence([('C5', 1), ('E5', 1), ('G5', 1), ('C6', 2), ('G5', 1), ('C6', 4)], bpm, 'square', 0.22, duty=0.3, env=env)
    harm = sequence([('E4', 1), ('G4', 1), ('C5', 1), ('E5', 2), ('C5', 1), ('E5', 4)], bpm, 'triangle', 0.18, env=env)
    return normalize(mix(lead, harm), 0.7)


def jingle_lose():
    bpm = 120
    env = {'attack': 0.005, 'decay': 0.1, 'sustain': 0.5, 'release': 0.1}
    return sequence([('E4', 1), ('Eb4', 1), ('D4', 1), ('Db4', 3)], bpm, 'square', 0.22, duty=0.4, env=env)


# ---------------------------------------------------------------- sfx
def sfx_click():
    return tone(1400.0, 0.05, 'square', 0.25, duty=0.3, env={'decay': 0.03, 'sustain': 0.2})


def sfx_place():
    return mix(tone(220.0, 0.12, 'triangle', 0.5, sweep=0.5, env={'decay': 0.08, 'sustain': 0.2}),
               tone(3000.0, 0.03, 'noise', 0.15))


def sfx_remove():
    return tone(600.0, 0.15, 'square', 0.22, duty=0.3, sweep=0.3, env={'decay': 0.1, 'sustain': 0.3})


def sfx_rotate():
    return tone(500.0, 0.08, 'square', 0.2, duty=0.25, sweep=2.0, env={'decay': 0.05, 'sustain': 0.4})


def sfx_bounce():
    return tone(320.0, 0.09, 'sine', 0.5, sweep=0.5, env={'attack': 0.002, 'decay': 0.06, 'sustain': 0.2})


def sfx_boing():
    """Trampoline."""
    return tone(180.0, 0.35, 'square', 0.3, duty=0.5, sweep=3.0,
                env={'attack': 0.005, 'decay': 0.2, 'sustain': 0.4, 'release': 0.1})


def sfx_boom():
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    rumble = lowpass(osc('noise', 7.0, n), 0.05) * np.exp(-t * 6.0) * 1.6
    thump = tone(90.0, 0.4, 'sine', 0.8, sweep=0.3, env={'attack': 0.002, 'decay': 0.3, 'sustain': 0.1})
    return normalize(mix(rumble, thump), 0.8)


def sfx_start():
    return sequence([('C5', 1), ('G5', 1)], 240, 'square', 0.22, duty=0.3,
                    env={'decay': 0.05, 'sustain': 0.5})


def sfx_stop():
    return sequence([('G5', 1), ('C5', 1)], 240, 'square', 0.22, duty=0.3,
                    env={'decay': 0.05, 'sustain': 0.5})


def sfx_wind():
    """Looping fan noise (2 s, faded ends so the loop is seamless)."""
    n = SR * 2
    noise = lowpass(osc('noise', 1.0, n), 0.08) * 0.9
    t = np.arange(n) / SR
    wobble = 0.75 + 0.25 * np.sin(2 * np.pi * 6.0 * t)
    fade = np.minimum(1.0, np.minimum(t, (n / SR) - t) * 20.0)
    return noise * wobble * fade * 0.5


def sfx_belt():
    """Looping conveyor motor (1 s)."""
    n = SR
    t = np.arange(n) / SR
    buzz = osc('saw', 55.0, n) * 0.5 + osc('square', 110.0, n, 0.2) * 0.3
    tick = (np.sin(2 * np.pi * 8.0 * t) > 0.95).astype(float) * 0.4
    fade = np.minimum(1.0, np.minimum(t, 1.0 - t) * 40.0)
    return lowpass(buzz * 0.25 + tick * osc('noise', 3.0, n) * 0.2, 0.15) * fade


SOUNDS = {
    'music_game.wav': music_game,
    'music_menu.wav': music_menu,
    'win.wav': jingle_win,
    'lose.wav': jingle_lose,
    'click.wav': sfx_click,
    'place.wav': sfx_place,
    'remove.wav': sfx_remove,
    'rotate.wav': sfx_rotate,
    'bounce.wav': sfx_bounce,
    'boing.wav': sfx_boing,
    'boom.wav': sfx_boom,
    'start.wav': sfx_start,
    'stop.wav': sfx_stop,
    'wind.wav': sfx_wind,
    'belt.wav': sfx_belt,
}


def main():
    for name, builder in SOUNDS.items():
        write_wav(name, builder())


if __name__ == '__main__':
    main()
