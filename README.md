# stlr

## Overview

`stlr` is a toolkit designed as a wrapper to [`whisper-timestamped`](https://github.com/linto-ai/whisper-timestamped) and [`stable-whisper`](https://github.com/jianfch/stable-ts) which aims to provide a more convenient interface between them. It serves as the foundation for `stlr-apps` (a suite of tools for automatic subtitle generation, etc.)

## Installation

## Usage

```python
from pathlib import Path
from typing import Iterator

from stlr import Transcription
from stlr.transcribe import WordTiming, Segment

# create a transcription from an audio file
transcription = Transcription.from_audio("path/to/audio.ext")

# Transcription objects are iterable, and they iterate over WordTimings
word_timings: Iterator[WordTiming] = iter(transcription)

# For just the actual words themselves:
words: list[str] = transcription.words
text: str = str(transcription)

# You can also create Segments, which are consecutive words without pauses.
segments: Iterator[Segment] = transcription.get_segments(tolerance=0.0)

# Find the timing for a particular substring of words
segment: Segment = transcription.get_fragment(fragment="...")

# Transcriptions can be exported as json, Audacity cue, or Audition cue
transcription.export(filestem="transcription", mode="json")      # -> transcription.json
transcription.export(filestem="transcription", mode="audacity")  # -> transcription.txt
transcription.export(filestem="transcription", mode="audition")  # -> transcription.csv

# Similarly, Transcriptions can be created from these exported files:
transcription = Transcription.from_json(Path("transcription.json"))
transcription = Transcription.from_audacity_cue(Path("transcription.txt"))
transcription = Transcription.from_audition_cue(Path("transcription.csv"))

# A convenience wrapper around these is also provided:
# `mode` should be one of "audio", "json", "audacity", "audition"
transcription = Transcription.load(Path(...), mode=...)

# Because Transcriptions are constructed out of words, not as segments, direct export
# to SRT is not supported. While it may be preferable to manually (or otherwise) determine
# the proper segment split points, the following can be used:
Transcription.write_srt(segments=transcription.get_segments(), dest="transcription.srt")
```