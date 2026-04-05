from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from music21 import chord, converter, meter, note, tempo


DEFAULT_TEMPO_BPM = 120


@dataclass(slots=True)
class ParsedNoteEvent:
    pitch: int | None
    duration: float
    offset: float
    is_rest: bool = False


@dataclass(slots=True)
class ParsedPart:
    name: str
    notes: list[ParsedNoteEvent]


@dataclass(slots=True)
class ParsedScore:
    title: str | None
    tempo_bpm: int
    time_signature: str | None
    parts: list[ParsedPart]

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "tempo_bpm": self.tempo_bpm,
            "time_signature": self.time_signature,
            "parts": [
                {
                    "name": part.name,
                    "notes": [asdict(note_event) for note_event in part.notes],
                }
                for part in self.parts
            ],
        }


def _extract_tempo_bpm(score: Any) -> int:
    for tempo_mark in score.recurse().getElementsByClass(tempo.MetronomeMark):
        quarter_bpm = tempo_mark.getQuarterBPM()
        if quarter_bpm:
            return int(round(quarter_bpm))

    return DEFAULT_TEMPO_BPM


def _extract_time_signature(score: Any) -> str | None:
    for time_signature in score.recurse().getElementsByClass(meter.TimeSignature):
        return time_signature.ratioString

    return None


def _extract_note_events(part_stream: Any) -> list[ParsedNoteEvent]:
    note_events: list[ParsedNoteEvent] = []

    for element in part_stream.flatten().notesAndRests:
        duration = float(element.duration.quarterLength)
        offset = float(element.offset)

        if duration <= 0:
            continue

        if isinstance(element, note.Rest):
            note_events.append(
                ParsedNoteEvent(
                    pitch=None,
                    duration=duration,
                    offset=offset,
                    is_rest=True,
                )
            )
            continue

        if isinstance(element, chord.Chord):
            for pitch in element.pitches:
                note_events.append(
                    ParsedNoteEvent(
                        pitch=pitch.midi,
                        duration=duration,
                        offset=offset,
                    )
                )
            continue

        if isinstance(element, note.Note):
            note_events.append(
                ParsedNoteEvent(
                    pitch=element.pitch.midi,
                    duration=duration,
                    offset=offset,
                )
            )

    return note_events


def parse_musicxml(file_path: str | Path) -> dict[str, Any]:
    source_path = Path(file_path)
    if not source_path.exists():
        raise FileNotFoundError(f"MusicXML file not found: {source_path}")

    score = converter.parse(str(source_path))
    score_parts = list(score.parts) if score.parts else [score]

    parsed_parts: list[ParsedPart] = []
    for index, part_stream in enumerate(score_parts, start=1):
        part_name = part_stream.partName or getattr(part_stream, "id", None) or f"Part {index}"
        parsed_parts.append(
            ParsedPart(
                name=part_name,
                notes=_extract_note_events(part_stream),
            )
        )

    parsed_score = ParsedScore(
        title=score.metadata.title if score.metadata and score.metadata.title else source_path.stem,
        tempo_bpm=_extract_tempo_bpm(score),
        time_signature=_extract_time_signature(score),
        parts=parsed_parts,
    )

    return parsed_score.to_dict()
