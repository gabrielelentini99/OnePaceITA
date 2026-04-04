#!/usr/bin/env python3
"""
Extract hardcoded subtitles from anime video (optimized for One Piece / One Pace)
using Tesseract OCR and generate an SRT file.

Optimizations:
- Narrow bottom ROI (15%) targeting subtitle region only
- Color-based text isolation (white & yellow subtitle text)
- 3x upscaling for small text
- Confidence-based OCR word filtering
- Aggressive garbage text removal
- Smart segment merging with fuzzy matching
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
import pytesseract


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass
class SubtitleSegment:
    start: float
    end: float
    text: str


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="OCR hardcoded anime subtitles → SRT  (tuned for One Piece / One Pace)",
    )
    p.add_argument("input_video", type=Path, help="Input video path")
    p.add_argument("-o", "--output", type=Path, default=None,
                   help="Output SRT path (default: <video>.srt)")
    p.add_argument("--lang", default="eng",
                   help="Tesseract language(s), e.g. 'eng' or 'eng+ita' (default: eng)")
    p.add_argument("--sample-fps", type=float, default=2.0,
                   help="Frames per second to sample (default: 2)")
    p.add_argument("--bottom-ratio", type=float, default=0.12,
                   help="Bottom portion of frame to scan (default: 0.12)")
    p.add_argument("--side-crop", type=float, default=0.05,
                   help="Fraction to crop from left & right edges (default: 0.05)")
    p.add_argument("--similarity", type=float, default=0.60,
                   help="Fuzzy text similarity threshold (default: 0.60)")
    p.add_argument("--min-duration", type=float, default=0.8,
                   help="Drop segments shorter than this (seconds, default: 0.8)")
    p.add_argument("--merge-gap", type=float, default=0.75,
                   help="Merge identical consecutive subs within this gap (default: 0.75)")
    p.add_argument("--min-confidence", type=int, default=55,
                   help="Tesseract word confidence threshold 0-100 (default: 55)")
    p.add_argument("--max-seconds", type=float, default=None,
                   help="Stop after N seconds of video (for quick tests)")
    p.add_argument("--upscale", type=int, default=3,
                   help="Upscale factor for subtitle ROI (default: 3)")
    p.add_argument("--tesseract-cmd", default=None,
                   help="Path to tesseract executable if not in PATH")
    p.add_argument("--debug-frames", type=Path, default=None,
                   help="Save processed ROI frames to this directory for debugging")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Time formatting
# ---------------------------------------------------------------------------

def fmt_srt(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ---------------------------------------------------------------------------
# Image preprocessing  – tuned for white/yellow anime subtitles
# ---------------------------------------------------------------------------

def extract_subtitle_roi(frame: np.ndarray, bottom_ratio: float, side_crop: float) -> np.ndarray:
    """Crop the subtitle region from a video frame."""
    h, w = frame.shape[:2]
    y_top = int(h * (1.0 - bottom_ratio))
    x_left = int(w * side_crop)
    x_right = int(w * (1.0 - side_crop))
    return frame[y_top:h, x_left:x_right]


def make_white_text_mask(roi_bgr: np.ndarray) -> np.ndarray:
    """Isolate bright white subtitle text via HSV thresholding."""
    hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
    # White text: any hue, low saturation, high value
    lower = np.array([0, 0, 180], dtype=np.uint8)
    upper = np.array([180, 60, 255], dtype=np.uint8)
    return cv2.inRange(hsv, lower, upper)


def make_yellow_text_mask(roi_bgr: np.ndarray) -> np.ndarray:
    """Isolate bright yellow subtitle text (used for emphasis/names)."""
    hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
    lower = np.array([18, 80, 180], dtype=np.uint8)
    upper = np.array([35, 255, 255], dtype=np.uint8)
    return cv2.inRange(hsv, lower, upper)


def _remove_small_components(mask: np.ndarray, min_area: int, min_width: int) -> np.ndarray:
    """Remove connected components that are too small to be subtitle text."""
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    cleaned = np.zeros_like(mask)
    for i in range(1, n_labels):  # skip background
        area = stats[i, cv2.CC_STAT_AREA]
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]
        if area < min_area:
            continue
        if w < min_width:
            continue
        # Very tall thin components are unlikely subtitle text
        if h > 0 and w / h < 0.15:
            continue
        cleaned[labels == i] = 255
    return cleaned


def preprocess_for_ocr(
    frame: np.ndarray,
    bottom_ratio: float,
    side_crop: float,
    upscale: int,
) -> np.ndarray:
    """Full pipeline: crop → color filter → upscale → denoise → clean."""
    roi = extract_subtitle_roi(frame, bottom_ratio, side_crop)

    # Combine white + yellow text masks
    white = make_white_text_mask(roi)
    yellow = make_yellow_text_mask(roi)
    mask = cv2.bitwise_or(white, yellow)

    # Upscale for better OCR on small glyphs
    if upscale > 1:
        mask = cv2.resize(mask, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_CUBIC)
        _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    # Remove small noise blobs (not text-sized)
    min_area = 40 * upscale * upscale   # scale with upscale factor
    min_width = 4 * upscale
    mask = _remove_small_components(mask, min_area, min_width)

    # Close small gaps in character strokes
    kern_close = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kern_close, iterations=1)

    # Smooth edges
    mask = cv2.GaussianBlur(mask, (3, 3), 0)
    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    # Tesseract prefers black text on white background
    return cv2.bitwise_not(mask)


# ---------------------------------------------------------------------------
# OCR with per-word confidence
# ---------------------------------------------------------------------------

def ocr_with_confidence(image: np.ndarray, lang: str, min_conf: int) -> str:
    """Run Tesseract and keep only words above the confidence threshold."""
    config = "--oem 3 --psm 6"
    data = pytesseract.image_to_data(image, lang=lang, config=config, output_type=pytesseract.Output.DICT)

    lines: dict[int, list[str]] = {}
    confs: dict[int, list[int]] = {}
    for i, word in enumerate(data["text"]):
        word = word.strip()
        if not word:
            continue
        conf = int(data["conf"][i])
        if conf < min_conf:
            continue
        # Skip single non-alpha characters (common OCR noise)
        if len(word) == 1 and not word.isalpha():
            continue
        line_num = data["line_num"][i]
        lines.setdefault(line_num, []).append(word)
        confs.setdefault(line_num, []).append(conf)

    result = []
    for ln in sorted(lines):
        line_text = " ".join(lines[ln])
        # Skip lines where average confidence is very low
        avg_conf = sum(confs[ln]) / len(confs[ln]) if confs[ln] else 0
        if avg_conf < min_conf + 10:
            continue
        # Skip very short lines (likely noise)
        alpha_chars = sum(1 for c in line_text if c.isalpha())
        if alpha_chars < 3:
            continue
        result.append(line_text)
    return "\n".join(result)


# ---------------------------------------------------------------------------
# Text quality filtering  – remove OCR garbage
# ---------------------------------------------------------------------------

_RE_MOSTLY_ALNUM = re.compile(r"[A-Za-z0-9]")
_RE_JUNK_CHARS = re.compile(r"[^A-Za-z0-9\s\'\"\-\.\,\!\?\:\;\…\—\–\(\)]")


def _line_is_garbage(line: str) -> bool:
    """Return True if the line is clearly not a valid subtitle."""
    stripped = line.strip()
    if len(stripped) < 3:
        return True
    alpha_count = sum(1 for c in stripped if c.isalpha())
    # Must have at least 3 alphabetic characters
    if alpha_count < 3:
        return True
    # Alphabetic ratio must be reasonable for subtitle text
    if alpha_count / len(stripped) < 0.40:
        return True
    # Ratio of junk characters should not dominate
    junk = len(_RE_JUNK_CHARS.findall(stripped))
    if len(stripped) > 0 and junk / len(stripped) > 0.35:
        return True
    # Must contain at least one word of 2+ alpha chars
    words = re.findall(r"[A-Za-z]{2,}", stripped)
    if not words:
        return True
    return False


def clean_ocr_text(raw: str) -> str:
    """Clean and filter OCR output, returning empty string for garbage."""
    text = raw.replace("\r", "\n")
    text = re.sub(r"[\u200b\ufeff]", "", text)

    lines = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        # Normalize whitespace
        ln = re.sub(r"\s+", " ", ln)
        # Reduce repeated dashes / dots
        ln = re.sub(r"-{3,}", "--", ln)
        ln = re.sub(r"\.{4,}", "...", ln)
        # Strip leading junk symbols (common OCR noise at line start)
        ln = re.sub(r"^[^A-Za-z0-9\"\'(]*", "", ln).strip()
        if _line_is_garbage(ln):
            continue
        lines.append(ln)

    result = "\n".join(lines).strip()

    # Final check: entire block must have enough real characters
    alpha_total = sum(1 for c in result if c.isalpha())
    if alpha_total < 4:
        return ""

    # Must have at least one word of 3+ letters
    real_words = re.findall(r"[A-Za-z]{3,}", result)
    if not real_words:
        return ""

    return result


# ---------------------------------------------------------------------------
# Fuzzy similarity (normalized)
# ---------------------------------------------------------------------------

def _normalize_for_cmp(text: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation for comparison."""
    t = text.lower()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, _normalize_for_cmp(a), _normalize_for_cmp(b)).ratio()


# ---------------------------------------------------------------------------
# Segment merging
# ---------------------------------------------------------------------------

def merge_segments(
    segments: list[SubtitleSegment],
    sim_thresh: float,
    merge_gap: float,
) -> list[SubtitleSegment]:
    if not segments:
        return []

    merged: list[SubtitleSegment] = [segments[0]]
    for seg in segments[1:]:
        prev = merged[-1]
        gap = seg.start - prev.end
        sim = similarity(prev.text, seg.text)
        if sim >= sim_thresh and gap <= merge_gap:
            # Extend, keeping the longer (presumably better) OCR text
            prev.end = max(prev.end, seg.end)
            if len(seg.text) > len(prev.text):
                prev.text = seg.text
        else:
            merged.append(seg)

    return merged


# ---------------------------------------------------------------------------
# Main extraction loop
# ---------------------------------------------------------------------------

def extract_subtitles(
    video_path: Path,
    lang: str,
    sample_fps: float,
    bottom_ratio: float,
    side_crop: float,
    sim_thresh: float,
    min_duration: float,
    merge_gap: float,
    min_confidence: int,
    max_seconds: float | None,
    upscale: int,
    debug_dir: Path | None,
) -> list[SubtitleSegment]:

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_step = max(1, int(round(fps / max(sample_fps, 0.1))))
    duration = total / fps if fps > 0 else 0

    if debug_dir:
        debug_dir.mkdir(parents=True, exist_ok=True)

    print(f"Video: {fps:.1f} fps, ~{duration:.0f}s, sampling every {frame_step} frames "
          f"({fps / frame_step:.1f} effective fps)")

    segments: list[SubtitleSegment] = []
    cur_text = ""
    cur_start = 0.0
    last_time = 0.0
    frames_processed = 0

    idx = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % frame_step != 0:
                idx += 1
                continue

            t = idx / fps
            if max_seconds is not None and t > max_seconds:
                break

            processed = preprocess_for_ocr(frame, bottom_ratio, side_crop, upscale)

            if debug_dir and frames_processed < 50:
                cv2.imwrite(str(debug_dir / f"frame_{idx:06d}.png"), processed)

            raw = ocr_with_confidence(processed, lang, min_confidence)
            text = clean_ocr_text(raw)

            if not cur_text and text:
                cur_text = text
                cur_start = t
            elif cur_text and not text:
                segments.append(SubtitleSegment(cur_start, t, cur_text))
                cur_text = ""
            elif cur_text and text:
                if similarity(cur_text, text) >= sim_thresh:
                    # Keep longer/better version
                    if len(text) > len(cur_text):
                        cur_text = text
                else:
                    segments.append(SubtitleSegment(cur_start, t, cur_text))
                    cur_text = text
                    cur_start = t

            last_time = t
            idx += 1
            frames_processed += 1

            if frames_processed % 100 == 0:
                pct = (t / duration * 100) if duration else 0
                print(f"  {frames_processed} frames processed ({t:.0f}s / {duration:.0f}s, {pct:.0f}%) "
                      f"→ {len(segments)} segments so far", flush=True)
    finally:
        cap.release()

    if cur_text:
        segments.append(SubtitleSegment(cur_start, last_time + (1.0 / max(sample_fps, 0.5)), cur_text))

    print(f"  Raw segments: {len(segments)}")

    # Post-processing
    segments = [s for s in segments if (s.end - s.start) >= min_duration and s.text.strip()]
    segments = merge_segments(segments, sim_thresh, merge_gap)

    print(f"  After merge/filter: {len(segments)}")
    return segments


# ---------------------------------------------------------------------------
# SRT writer
# ---------------------------------------------------------------------------

def write_srt(segments: list[SubtitleSegment], path: Path) -> None:
    lines: list[str] = []
    for i, seg in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{fmt_srt(seg.start)} --> {fmt_srt(seg.end)}")
        lines.append(seg.text)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_args()

    video: Path = args.input_video
    if not video.exists():
        raise FileNotFoundError(f"Input video not found: {video}")

    output = args.output or video.with_suffix(".srt")

    if args.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = args.tesseract_cmd

    segments = extract_subtitles(
        video_path=video,
        lang=args.lang,
        sample_fps=args.sample_fps,
        bottom_ratio=args.bottom_ratio,
        side_crop=args.side_crop,
        sim_thresh=args.similarity,
        min_duration=args.min_duration,
        merge_gap=args.merge_gap,
        min_confidence=args.min_confidence,
        max_seconds=args.max_seconds,
        upscale=args.upscale,
        debug_dir=args.debug_frames,
    )

    write_srt(segments, output)
    print(f"\nDone — {len(segments)} subtitle segments → {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
