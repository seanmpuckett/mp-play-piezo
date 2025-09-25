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
  - Call setup(pin, timerid, interruptrate) once at startup:
      pin: GPIO pin number for PWM output
      timerid: ID of hardware timer to use for interrupts
      interruptrate: HZ of interrupts, defaults to 120 which is fine

Playing music:
  - play(seq): Starts playing the given music string.
    Returns immediately; playback occurs in background via timer interrupt.
  - stop(): Stops playback immediately and disables PWM & interrupt.
  - isplaying(): returns 1 if music is playing, 0 if not

Interrupts:
  - Uses a hardware timer running at 120 Hz (or whatever you pass in)
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

See source for this.
