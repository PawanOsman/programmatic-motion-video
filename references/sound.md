# Sound

Sound sells motion. `sfx.py` synthesises music and effects with numpy on the same timeline as the
picture, mixes them, and normalises loudness. `mv.cli(video, audio=soundtrack)` builds the WAV and
muxes it into the render.

```python
def soundtrack():
    m = sfx.Mixer(tl.duration)                          # loop=True for seamless loops
    info = sfx.backing(m, bpm=112, key='E', mode='minor', style='drive')
    m.add(sfx.whoosh(0.45), tl.start(2) - 0.45, 0.5)    # peaks exactly on the cut into scene 2
    sfx.type_clicks(m, PROMPT, T['type_at'], T['cps'])  # a key click per typed character
    m.add(sfx.chime('success'), T['done'], 0.35, reverb=0.4)
    return m.master('audio.wav', lufs=-14)              # mix, limit, two-pass loudness
```

## Map every motion to a sound

| Motion | Sound |
|---|---|
| Typing | `type_clicks` (or `click()` per character) |
| Press, click | `click()`, then a soft `blip(f)` for what appears |
| Pop-ins, cards, badges | `blip(660..1320)`, rising with each item |
| Transitions, camera moves | `whoosh(dur)`: it peaks at its end, so start it `dur` early |
| Before a big moment | `riser(dur)` or `swell(dur)` ending on the hit |
| Logo hit, title slam | `impact()` |
| Success, notifications, errors | `chime('success' | 'notify' | 'error')` |
| Magic, reveals | `sparkle()` |
| Everything | a music bed under it all |

Timing comes from the same dict as the picture, in seconds, so a timing change moves the sound too.

## Music beds

`sfx.backing(m, start, end, bpm, key, mode, progression, style, gain, fade_in, fade_out)` writes
drums, bass, chords and a melody layer on a beat grid and returns its timing
(`bpm, beat, bar, bars, beats, chords`) so cuts can land on bars.

| style | Feel | Use |
|---|---|---|
| `ambient` | pads and bells, no drums | signage, calm explainers |
| `pulse` | soft kick, hats, eighth-note bass, plucks | product demos |
| `drive` | four-on-the-floor, claps, arpeggio | promos, reels, ads |
| `corporate` | electric piano, light drums, shaker | walkthroughs, explainers |
| `lofi` | slow swing, soft keys | captions, code, podcasts |

Modes: `major`, `minor`, `dorian`, `mixolydian`, `lydian`, `phrygian`. Progressions (scale degrees):
`minor` (i VI III VII), `minor-soft`, `major` (I V vi IV), `major-lift`, `calm`, or your own list.
Instruments to write your own parts: `kick snare clap hat open_hat shaker tom bass sub pluck pad bell
epiano`; notes with `hz('A4')`, `midi()`, `chord(key, mode, degree, octave)`.

Duck the music under hits and voice with `m.duck(times)`; ramp buses with `m.fade(bus, t0, t1, g0, g1)`;
pan effects with the motion (`pan=-1..1`); send to reverb with `reverb=0..1`.

## Loudness

`m.master(path, lufs)` (or `sfx.loudnorm(src, dst, lufs)`) runs two-pass EBU R128 normalisation:

- -14 LUFS for web and social; -16 for podcasts and calm content;
- -23 LUFS for EBU R128 broadcast; -24 LKFS for ATSC A/85;
- true peak -1.5 dBTP before AAC, which adds peaks (it lands at about -1 dBTP).

Check a delivered file: `sfx.loudness('out.mp4')` returns `{'lufs': ..., 'true_peak': ...}`.

## Loops

Make the music a whole number of bars (`bar = 240 / bpm` seconds) and use `Mixer(duration, loop=True)`:
sounds and reverb tails that run past the end wrap to the start, and beds don't fade.

## Existing audio

- `sfx.load(path)` decodes any audio or video file to a stereo array; `m.add(sig, t, gain, bus='music')`.
- `media.audio_of(video, 'a.wav')` extracts a clip's sound; `sfx.loudnorm` levels it.
- Music-reactive visuals: `sfx.analyze(path, fps, bands)` gives per-frame loudness and spectrum
  (`templates/audiogram.py`); tempo and beats: librosa or beat-this.

## Voice-over

- Local text-to-speech: piper-tts, kokoro, coqui-tts, chatterbox-tts; or a TTS API. Kurdish
  (Sorani and Kurmanji) needs a model trained for it.
- Clone voices only with consent.
- Word timings: faster-whisper or whisperx; drive captions and cuts from them, and duck the music
  under the voice (`m.duck(onsets, depth=0.5)` or put the voice on the `voice` bus).

## Real instruments

Write MIDI with mido or pretty_midi and render it with pyfluidsynth and a SoundFont; polish with
pedalboard (compressor, EQ, reverb, limiter). Stock music and effects need a licence that covers the
use and the platform.
