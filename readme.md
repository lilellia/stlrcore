# stlr

## Overview

`stlr` is a toolkit designed to assist in the development of voice-acted visual novels. It comes with these components:

### ※ stlr.py
`stlr.py` can transcribe the audio of a line and output a Ren'Py say statement with the pauses between words notated in an effort to have the text scroll alongside the audio.

Choose a number of files, and stlr will populate its UI with textboxes for each line. After pressing "Transcribe", the boxes will fill with timing-adjusted say statements, example:

```Actually,{w=0.39} this{w=0.06} is{w=0.06} fine.{w=0.63} Clearly my noble wants to play{w=0.36} hide{w=0.51} and{w=0.09} seek.{w=1.26} Well,{w=0.36} I{w=0.06} wonder what'll happen{w=0.3} if{w=0.03} I{w=0.27} find you.```

**NOTE:** `astral` is the better developed of the two main components. This project was developed in collaboration with a particular VN developer, and she decided to scrap the text-scrolling aspect of her game and focus more on the animations. As such, `stlr` saw an indefinite pause in development.

### ※ astral.py

`astral.py` is designed to assist with animations. She can determine the timing of words spoken in an audio file, then generate Ren'Py ATL to alternate between a closed-mouth and open-mouth image so that these line up with the beginnings and ends of words.

Select an audio file, as well as the two image files, then press "Generate ATL". The toggles on the right side of the UI are as follows:

- *Detailed Annotations* — show the exact timing of every line, as well as the start and end of every word with boundaries given. This can be useful for debugging, but can also be cluttered.
- *Full Image Paths* — when checked, enter the image filenames into the ATL exactly as they appear in the textboxes. When unchecked, trim to `images/...`.
- *let astral-chan try ♥* — when checked, use astral's "smart" ATL generation to make sure the animations line up as best as she can. when unchecked, simply alternate open/closed images every 0.2 seconds for the entire duration of the audio


### ※ impatient.py
`impatient.py` is designed to remove all Ren'Py `{w=...}` wait tags from a script.


### ※ étoile.py

`étoile.py` is designed to simply output the detailed timing data for a transcription. Can accept a file parameter from command line: if not provided, will launch file selection window.


## Installation

After cloning this repository, simply run

```sh
python3 -m pip install ttkbootstrap loguru more-itertools openai-whisper pyyaml tabulate[wide-chars] git+https://github.com/linto-ai/whisper-timestamped
```