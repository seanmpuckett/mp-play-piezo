
# piezo player library for micropython
# 2025 Shea M Puckett
# Apache 2.0 License e.g. you're on your own

from machine import Pin,PWM,Timer
import array


buf_play = array.array('H',bytearray(32))
BUF_POS = const(0)
BUF_TOP = const(1)
PLAYING = const(2)
NOTE_OFF = const(3)
DATA_START = const(4)

pwm = None
timer = None

def setup(pin, timerid):
    global pwm, timer
    timer = Timer(timerid)
    pwm = PWM(Pin(pin,Pin.OUT))
    pwm.duty_u16(0)
    pwm.deinit()
    pwm.init()
    pwm.duty_u16(0)
  
def play(seq): 
    if stop(): return
    if count := _parse(seq):
        buf_play[BUF_TOP] = count
        buf_play[BUF_POS] = DATA_START 
        buf_play[PLAYING] = 1   
        _handler(None)

def stop():
    if pwm is None: return 1
    timer.deinit()
    if buf_play[PLAYING]: pwm.duty_u16(0)
    buf_play[PLAYING] = 0

def isplaying():
    return buf_play[PLAYING]
 
### internals
 
@micropython.viper
def _handler(junk):
    _buf = ptr16(buf_play)
  
    if not _buf[PLAYING]: stop(); return
    pos = _buf[BUF_POS]
    if pos >= _buf[BUF_TOP]: stop(); return

    f = _buf[pos]
    d = _buf[pos + 1]

    duty = 256 << ((f >> 13) & 7)
    f &= 0x1FFF

    if f == 0:            # rest
        pwm.duty_u16(0)
    elif f == 1:          # click
        pwm.duty_u16(65535)
    else:                 # tone
        pwm.duty_u16(duty)
        pwm.freq(f)

    duration   = d & 0x1FFF
    note_off   = ((duration * (d >> 13)) >> 3) if f else 0
    _buf[BUF_POS]  = pos + 2

    if note_off:
      _buf[NOTE_OFF] = note_off
      timer.init(period=duration - note_off, mode=Timer.ONE_SHOT, callback=_noteoff)
    else:
      timer.init(period=duration, mode=Timer.ONE_SHOT, callback=_handler)


def _noteoff(junk):
    pwm.duty_u16(0)
    timer.init(period=buf_play[NOTE_OFF], mode=Timer.ONE_SHOT, callback=_handler)
    




    
notes = "C D EF G A B!R,"
freqs = (
    33, 35, 37, 39, 41, 44, 46, 49, 52, 55, 58, 62, 
    65, 69, 73, 78, 82, 87, 92, 98, 104, 110, 117, 123, 
    131, 139, 147, 156, 165, 175, 185, 196, 208, 220, 233, 247, 
    262, 277, 294, 311, 330, 349, 370, 392, 415, 440, 466, 494, 
    523, 554, 587, 622, 659, 698, 740, 784, 831, 880, 932, 988, 
    1047, 1109, 1175, 1245, 1319, 1397, 1480, 1568, 1661, 1760, 1865, 1976, 
    2093, 2217, 2349, 2489, 2637, 2794, 2960, 3136, 3322, 3520, 3729, 3951, 
    4186, 4435, 4699, 4978, 5274, 5588, 5920, 6272, 6645, 7040, 7459, 7902
)



def _parse(seq):
    buflen = len(buf_play) - 2
    seq = seq.upper()
    i = 0
    lseq=len(seq)
    octave = 48
    wholenote = 2000 # milliseconds in a whole note at 120 bpm
    length = 4
    sharp = gap = 0
    dot = 256
    duty = 0xE000
    bufin = DATA_START
    lfreqs = len(freqs)
    nxt = loopstart = loopcount = 0
    cmd = seq[0]
    while i < lseq:
        i += 1
        mod = 0
        while i < lseq:
            nxt = seq[i]
            if nxt == '#': sharp += 1; i += 1
            elif nxt == '-': sharp -= 1; i += 1
            elif nxt == '.': dot = dot * 3 >> 1; i += 1
            elif nxt == ':': dot = dot * 2 // 3; i += 1
            else:
                v = ord(nxt)-48
                if v<0 or v>9: break
                mod = mod * 10 + v
                i += 1              
        if cmd == ' ': pass
        elif cmd == 'O': octave = (mod-1) * 12
        elif cmd == '<': octave -= 12
        elif cmd == '>': octave += 12
        elif cmd == 'T': wholenote = (240000) // (mod or 1)
        elif cmd == 'L': length = mod
        elif cmd == 'M': gap = 0x2000 * mod
        elif cmd == 'V': duty = 0x2000 * mod
        elif cmd == 'S': 
            octave += mod if sharp >= 0 else -mod
            sharp = 0
        elif cmd == '[': 
            loopstart = i
            loopcount = mod or 1
        elif cmd == ']':
            if loopcount > 0: 
                i = loopstart
                nxt = seq[i]
                loopcount -= 1
        else:
            note = notes.find(cmd)
            if note < 0: print("unknown music play command:",cmd); return 0
            freq = freqs[(note + octave + sharp) % lfreqs] if note < 12 else 1 if note == 12 else 0
            on = ((wholenote * dot) >> 8) // (mod or length or 1) 
            buf_play[bufin] = freq | duty
            buf_play[bufin + 1] = on | gap
            bufin += 2
            if bufin >= buflen: 
              buf_play.extend(bytearray(32)) # 16 more entries
              buflen = len(buf_play) - 2
            sharp = 0
            dot = 256
        cmd = nxt
    return bufin




                        
"""
MicroPython Music Player Module

This module provides a lightweight, interrupt-driven music player that uses PWM
to generate tones based on a compact ASCII music string format similar to that used
by Microsoft Extended BASIC's PLAY function.  
    
Useful for creating simple tunes and sound effects from an attached piezo speaker
    

=== USER GUIDE: MUSIC STRING FORMAT ===

Music sequences are defined as strings with the following commands:

Notes:
  C D E F G A B   - Play corresponding note in current octave
  R or ,          - Rest (silence)
  !               - Click (full-volume pulse)

Accidentals:
  # after note     - Sharp (e.g., C#)
  - after note     - Flat (e.g., D-)

Duration modifiers:
  . after note     - Dotted note (adds 50% duration)
  : after note     - Triplet note (2/3 duration)

Numeric suffixes:
  Number after note or command - Sets duration (for notes) or value (for commands)
    Example: C4 = quarter note C, L8 = default length = eighth note

Octave control:
  O<number>       - Set octave (1-8); e.g., O4
  <               - Decrease octave by 1
  >               - Increase octave by 1
  S<number>       - Transpose by semitones -96 to 96 (cumulative)

Looping:
  [<number>       - Start of loop segment. If no number, loops once
  ]               - End of loop segment.  No nested loops. 
                    Transposition and octave changes "stack" within loops
  
Tempo & timing:
  T<number>       - Set tempo in BPM (beats per minute); e.g., T120
  L<number>       - Set default note length (1=whole, 2=half, 4=quarter, etc.)
  M<number>       - Set gap (silence) after each note as fraction of note length
                    (0 = no gap, 1 = 1/8 gap, ... 7 = 7/8 gap)

Volume (PWM duty cycle):
  V<number>       - Set volume level (0-7); affects subsequent notes

Whitespace is ignored. Commands are case-insensitive.

Example:
  "T120 O5 L4 V4 C D E F G A B >C < <B A G F E D C"

=== TECHNICAL INTEGRATION NOTES ===

Hardware setup:
  - Call setup(pin, timerid) once at startup:
      pin: GPIO pin number for PWM output
      timerid: ID of hardware timer to use for interrupts

Playing music:
  - play(seq): Starts playing the given music string.
    Returns immediately; playback occurs in background via timer interrupt.
  - stop(): Stops playback immediately and disables PWM & interrupt.
  - isplaying(): returns 1 if music is playing, 0 if not

Interrupts:
  - Uses a periodic hardware timer for note start/stop 
  - Handler is implemented in Viper mode for speed.
  - Interrupts shut off when not needed

Buffering:
  - Uses a global array 'buf_play' to store parsed note data.
  - Buffer grows automatically as needed.

PWM configuration:
  - PWM frequency is set per-note (up to ~8 kHz based on freqs table).
  - Duty cycle encodes volume (3-bit value embedded in upper bits of frequency word).

Data format in buffer (16-bit words):
  [freq | (duty<<13)]  - Frequency (13 bits) + volume (3 bits)
  [duration | (gap<<13)] - Note duration (13 bits) + gap timing (3 bits)

Constants:
  BUF_POS, BUF_TOP, PLAYING, COUNTDOWN, NOTE_OFF, DATA_START
    - Used internally for buffer and state management.

Dependencies:
  - Uses machine.PWM, machine.Pin, machine.Timer, and array modules.

Limitations:
  - Max note frequency limited by PWM and data format (up to B8 - 7902Hz)
  - Only one sequence can play at a time.
  - No polyphony (monophonic output only).
    
    
=== OPTIONAL RTTTL (ringtone text transfer language) TRANSLATOR ===
    
Use to translate ringtones into the format used here:
    
e.g. PacMan:d=16,o=6,b=140:b5,b,f#,d#,8b,8d#,c,c7,g,f,8c7,8e,b5,b,f#,d#,8b,8d#,32d#,32e,f,32f,32f#,g,32g,32g#,a,8b
translates to: T140L16O6<B>BF#D#B8D#8C>C<GF>C8<E8<B>BF#D#B8D#8D#32E32FF32F#32GG32G#32AB8
    
def rtttl_to_music(rtttl):
    _, d, n = rtttl.split(":", 2)
    bd = od = dd = ""
    for x in d.split(","):
        if x[0] == 'b': bd = x[2:]
        elif x[0] == 'o': od = x[2:]
        elif x[0] == 'd': dd = x[2:]
    bpm = int(bd) if bd else 63
    def_oct = int(od) if od else 6
    def_dur = int(dd) if dd else 4

    out = ["T", str(bpm), "L", str(def_dur), "O", str(def_oct)]
    cur_oct = def_oct

    for note in n.split(","):
        note = note.strip()
        if not note or note[0] == 'p':
            out.append("R")
            if note and note[1:].isdigit():
                out.append(note[1:])
            continue

        i = 0
        while i < len(note) and note[i].isdigit():
            i += 1
        dur = note[:i]
        p = note[i:]

        base = p[0].upper()
        j = 1
        if j < len(p) and p[j] == '#':
            base += '#'
            j += 1
        oct_part = p[j:]
        target_oct = int(oct_part) if oct_part.isdigit() else def_oct

        d_oct = target_oct - cur_oct
        if d_oct:
            out.append(">" if d_oct == 1 else "<" if d_oct == -1 else "O" + str(target_oct))
        cur_oct = target_oct

        out.append(base)
        if dur:
            out.append(dur)

    return "".join(out)
    

"""
                  
