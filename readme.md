# STLR

## Installation

1. Verify that Python is installed. In the terminal/command prompt:

```bash
python3 --version
```

should output something like "Python 3.11.2". If not, also try `python --version`, or `py --version`. Take note of which command works (for argument, we will assume `python3`).

2. Install necessary dependencies.

```bash
python3 -m pip install -r requirements.txt
```

## Usage

1. Construct a file with the necessary commands. This file should contain lines in the following pattern

```text
VA line audio filename
correct transcription

VA line audio filename
correct transcription

VA line audio filename
correct transcription
```

For example (suppose this file is `commands.txt`):

```text
05.mp3
Actually, this is fine. Clearly my noble wants to play Hide and Seek. Well, I wonder what'll happen if I find you.
```

2. Run STLR against the file you just created.

```bash
python3 stlr.py commands.txt
```

Your output should be something like (except likely colored):

```text
2023-04-30 16:21:11.022 | INFO     | __main__:process_audio:104 - loading audio (05.mp3)...
2023-04-30 16:21:11.023 | WARNING  | __main__:load_audio:75 - audio must be WAV format mono PCM. converting...
2023-04-30 16:21:11.356 | INFO     | __main__:process_audio:108 - processing...
2023-04-30 16:21:12.926 | SUCCESS  | __main__:handle_one:125 - 
Actually,{w=0.39} this{w=0.06} is{w=0.06} fine.{w=0.63} Clearly my noble wants to play{w=0.36} Hide{w=0.51} and{w=0.09} Seek.{w=1.26} Well,{w=0.36} I{w=0.06} wonder what'll happen{w=0.3} if{w=0.03} I{w=0.27} find you.
```

This final line,
```text
Actually,{w=0.39} this{w=0.06} is{w=0.06} fine.{w=0.63} Clearly my noble wants to play{w=0.36} Hide{w=0.51} and{w=0.09} Seek.{w=1.26} Well,{w=0.36} I{w=0.06} wonder what'll happen{w=0.3} if{w=0.03} I{w=0.27} find you.
```

is the wait-adjusted Ren'Py "say" statement that corresponds with that audio file. If you provided multiple commands, each command will correspond to an output block of this format.