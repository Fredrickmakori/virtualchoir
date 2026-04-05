from __future__ import annotations

from pathlib import Path
from typing import Any

from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo


DEFAULT_TICKS_PER_BEAT = 480
DEFAULT_VELOCITY = 72
CHOIR_AAHS_PROGRAM = 52
AVAILABLE_CHANNELS = [channel for channel in range(16) if channel != 9]


def _parse_time_signature(value: str | None) -> tuple[int, int] | None:
    if not value or "/" not in value:
        return None

    numerator, denominator = value.split("/", maxsplit=1)
    try:
        return int(numerator), int(denominator)
    except ValueError:
        return None


def _create_conductor_track(parsed_score: dict[str, Any]) -> MidiTrack:
    track = MidiTrack()

    tempo_bpm = int(parsed_score.get("tempo_bpm") or 120)
    track.append(MetaMessage("set_tempo", tempo=bpm2tempo(tempo_bpm), time=0))

    time_signature = _parse_time_signature(parsed_score.get("time_signature"))
    if time_signature:
        numerator, denominator = time_signature
        track.append(
            MetaMessage(
                "time_signature",
                numerator=numerator,
                denominator=denominator,
                clocks_per_click=24,
                notated_32nd_notes_per_beat=8,
                time=0,
            )
        )

    title = parsed_score.get("title")
    if title:
        track.append(MetaMessage("track_name", name=str(title), time=0))

    track.append(MetaMessage("end_of_track", time=0))
    return track


def _create_part_track(part: dict[str, Any], channel: int) -> MidiTrack:
    track = MidiTrack()
    track_name = str(part.get("name") or f"Part {channel + 1}")

    track.append(MetaMessage("track_name", name=track_name, time=0))
    track.append(Message("program_change", program=CHOIR_AAHS_PROGRAM, channel=channel, time=0))

    scheduled_events: list[tuple[int, int, Message]] = []
    for note_event in part.get("notes", []):
        pitch = note_event.get("pitch")
        if note_event.get("is_rest") or pitch is None:
            continue

        duration = float(note_event.get("duration", 0))
        if duration <= 0:
            continue

        start_tick = max(0, int(round(float(note_event.get("offset", 0)) * DEFAULT_TICKS_PER_BEAT)))
        end_tick = start_tick + max(1, int(round(duration * DEFAULT_TICKS_PER_BEAT)))

        scheduled_events.append(
            (
                start_tick,
                1,
                Message(
                    "note_on",
                    note=int(pitch),
                    velocity=DEFAULT_VELOCITY,
                    channel=channel,
                    time=0,
                ),
            )
        )
        scheduled_events.append(
            (
                end_tick,
                0,
                Message(
                    "note_off",
                    note=int(pitch),
                    velocity=0,
                    channel=channel,
                    time=0,
                ),
            )
        )

    scheduled_events.sort(key=lambda event: (event[0], event[1], event[2].note))

    last_tick = 0
    for absolute_tick, _, message in scheduled_events:
        delta = absolute_tick - last_tick
        track.append(message.copy(time=delta))
        last_tick = absolute_tick

    track.append(MetaMessage("end_of_track", time=0))
    return track


def create_midi_file(parsed_score: dict[str, Any], output_path: str | Path) -> Path:
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    parts = parsed_score.get("parts") or []
    if not parts:
        raise ValueError("Parsed score does not contain any parts.")

    midi_file = MidiFile(type=1, ticks_per_beat=DEFAULT_TICKS_PER_BEAT)
    midi_file.tracks.append(_create_conductor_track(parsed_score))

    for index, part in enumerate(parts):
        channel = AVAILABLE_CHANNELS[index % len(AVAILABLE_CHANNELS)]
        midi_file.tracks.append(_create_part_track(part, channel))

    midi_file.save(target_path)
    return target_path
