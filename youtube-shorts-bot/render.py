import argparse
import json
import os
import re
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFile, ImageFont, ImageOps, ImageStat

from workflow_common import (
    END_TAIL_SECONDS, OUTPUT_DIR, PRODUCTION_MAX_SECONDS, atomic_write_json,
    env_bool, expected_video_config, load_json,
)

ImageFile.LOAD_TRUNCATED_IMAGES = True
BASE = Path(__file__).parent
ASSETS = BASE / "assets"
UI_ASSETS = ASSETS / "ui"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
EMOJI_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf",
]
CARD_TRANSITION_SECONDS = 0.30

# Wacky Dramas production layout is permanently 720x1280. Keep all UI
# geometry in native output pixels so safe-space rules are explicit.
VIDEO_WIDTH = 720
VIDEO_HEIGHT = 1280

CAPTION_MARGIN_X = 85
CAPTION_MAX_WIDTH = VIDEO_WIDTH - (2 * CAPTION_MARGIN_X)  # 550px
CAPTION_FONT_SIZE = 52
CAPTION_MIN_FONT_SIZE = 39
CAPTION_MAX_LINES = 3
CAPTION_OUTLINE = 5
CAPTION_SHADOW = 1

CARD_BOX = (37, 157, 683, 537)
CARD_RADIUS = 24
CARD_SHADOWS = ((7, 55), (12, 25))
CARD_BORDER_WIDTH = 3
AVATAR_SIZE = 88
AVATAR_POS = (55, 193)
CHANNEL_NAME_POS = (157, 190)
CHANNEL_NAME_FONT_SIZE = 27
VERIFIED_ICON_SIZE = 25
VERIFIED_ICON_GAP = 12
VERIFIED_ICON_Y_OFFSET = 3
EMOJI_ROW_Y = 233
EMOJI_STEP_X = 51
EMOJI_TARGET_SIZE = 44
EMOJI_CELL_SIZE = 39
HOOK_POS = (57, 303)
HOOK_MAX_WIDTH = 600
HOOK_MAX_HEIGHT = 147
HOOK_MAX_FONT_SIZE = 43
HOOK_MIN_FONT_SIZE = 27
HOOK_LINE_GAP = 6
FOOTER_Y = 495
FOOTER_FONT_SIZE = 20
LIKE_ICON_SIZE = 20
COMMENT_ICON_SIZE = 21
SHARE_ICON_SIZE = 19
LIKE_X = 55
COMMENT_X = 143
SHARE_X = 579
FOOTER_TEXT_GAP = 7
HANDLE_PILL = (190, 840, 530, 889)
SUBSCRIBE_PILL = (240, 899, 480, 945)
HANDLE_FONT_SIZE = 28
SUBSCRIBE_FONT_SIZE = 25
PILL_OUTLINE_WIDTH = 1
CARD_BOB_AMPLITUDE = 4


def run(cmd):
    subprocess.run(cmd, check=True)


def font_px(path, size):
    return ImageFont.truetype(path, int(size))


def fit_text(draw, text, path, max_size, min_size, max_width):
    for size in range(max_size, min_size - 1, -1):
        font = font_px(path, size)
        if draw.textlength(text, font=font) <= max_width:
            return font
    return font_px(path, min_size)


def wrap_by_width(draw, text, font, max_width):
    words = str(text).split()
    lines = []
    current = []
    for word in words:
        candidate = " ".join(current + [word])
        if not current or draw.textlength(candidate, font=font) <= max_width:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def fit_hook(draw, text, max_width, max_height):
    for size in range(HOOK_MAX_FONT_SIZE, HOOK_MIN_FONT_SIZE - 1, -1):
        font = font_px(FONT_BOLD, size)
        lines = wrap_by_width(draw, text, font, max_width)
        bbox = draw.textbbox((0, 0), "Ag", font=font)
        line_height = bbox[3] - bbox[1] + HOOK_LINE_GAP
        if lines and len(lines) * line_height <= max_height:
            return font, lines, line_height
    font = font_px(FONT_BOLD, HOOK_MIN_FONT_SIZE)
    lines = wrap_by_width(draw, text, font, max_width)
    bbox = draw.textbbox((0, 0), "Ag", font=font)
    line_height = bbox[3] - bbox[1] + HOOK_LINE_GAP
    if len(lines) * line_height > max_height:
        raise SystemExit("story.hook does not fit the opening card at the minimum font size")
    return font, lines, line_height


def centered_text(draw, box, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = box[0] + (box[2] - box[0] - w) / 2 - bbox[0]
    y = box[1] + (box[3] - box[1] - h) / 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=fill)


def load_ui_icon(name, size):
    path = UI_ASSETS / name
    if not path.exists():
        raise SystemExit(f"Missing required UI asset: {path}")
    with Image.open(path) as src:
        src.load()
        image = src.convert("RGBA").copy()
    return image.resize((size, size), Image.Resampling.LANCZOS)


def paste_icon_centered(canvas, icon, x, center_y):
    y = int(center_y - icon.height / 2)
    canvas.alpha_composite(icon, (int(x), y))
    return int(x) + icon.width


def draw_text_centered_y(draw, x, center_y, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    h = bbox[3] - bbox[1]
    y = center_y - h / 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=fill)


def _emoji_font_path():
    return next((Path(p) for p in EMOJI_FONT_CANDIDATES if Path(p).exists()), None)


def render_emoji(emoji, target_size=EMOJI_TARGET_SIZE):
    font_path = _emoji_font_path()
    if not font_path:
        raise SystemExit("Noto emoji font is required for card emojis")
    # Noto Color Emoji has fixed bitmap strikes; 109px is the native size on
    # Debian and avoids Pillow's "invalid pixel size" failure.
    native_size = 109 if font_path.name == "NotoColorEmoji.ttf" else max(72, target_size * 2)
    font = ImageFont.truetype(str(font_path), native_size)
    scratch = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
    draw = ImageDraw.Draw(scratch)
    bbox = draw.textbbox((0, 0), emoji, font=font, embedded_color=True)
    if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
        raise SystemExit(f"Emoji could not be rendered: {emoji!r}")
    draw.text((-bbox[0] + 12, -bbox[1] + 12), emoji, font=font, embedded_color=True)
    alpha = scratch.getchannel("A")
    content = alpha.getbbox()
    if not content:
        raise SystemExit(f"Emoji rendered blank: {emoji!r}")
    cropped = scratch.crop(content)
    cropped.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)
    return cropped


def caption_layout(text):
    text = str(text).upper().strip()
    if not text:
        return "", CAPTION_FONT_SIZE
    for size in range(CAPTION_FONT_SIZE, CAPTION_MIN_FONT_SIZE - 1, -1):
        font = font_px(FONT_BOLD, size)
        draw = ImageDraw.Draw(Image.new("L", (1, 1)))
        words = text.split()
        lines = []
        current = []
        failed = False
        for word in words:
            if draw.textlength(word, font=font) > CAPTION_MAX_WIDTH:
                failed = True
                break
            candidate = " ".join(current + [word])
            if not current or draw.textlength(candidate, font=font) <= CAPTION_MAX_WIDTH:
                current.append(word)
            else:
                lines.append(" ".join(current))
                current = [word]
        if current:
            lines.append(" ".join(current))
        if not failed and len(lines) <= CAPTION_MAX_LINES:
            return "\n".join(lines), size
    raise ValueError(f"Caption cannot fit inside {CAPTION_MAX_WIDTH}px safe width: {text!r}")


def wrap_caption(text):
    return caption_layout(text)[0]


def caption_ass_text(text):
    wrapped, size = caption_layout(text)
    escaped = wrapped.replace("{", "\\{").replace("}", "\\}")
    return f"{{\\fs{size}}}" + escaped.replace("\n", r"\N")


def build_ass_header():
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {VIDEO_WIDTH}
PlayResY: {VIDEO_HEIGHT}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Main,DejaVu Sans,{CAPTION_FONT_SIZE},&H00FFFFFF,&H00FFFFFF,&H00000000,&H5A000000,-1,0,0,0,100,100,0,0,1,{CAPTION_OUTLINE},{CAPTION_SHADOW},5,{CAPTION_MARGIN_X},{CAPTION_MARGIN_X},0,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""


def ass_time(seconds):
    seconds = max(0.0, float(seconds))
    centis = int(round(seconds * 100))
    h, rem = divmod(centis, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def story_body_without_repeated_hook(script, hook):
    body = str(script).strip()
    opening = str(hook).strip()
    if opening and body.startswith(opening):
        body = body[len(opening):].lstrip(" \t\r\n-—:;,.!?\"")
    return body


def synthesize(pipeline, text, voice, speed, max_seconds=None):
    chunks = []
    segments = []
    samples = 0
    limit = None if max_seconds is None else max(1, int(round(float(max_seconds) * 24000)))
    for _gs, ps, audio in pipeline(text, voice=voice, speed=speed):
        arr = np.asarray(audio, dtype=np.float32).reshape(-1)
        if arr.size == 0:
            continue
        if limit is not None:
            remaining = limit - samples
            if remaining <= 0:
                break
            if arr.size > remaining:
                arr = arr[:remaining]
        chunks.append(arr)
        segments.append((str(ps).strip(), int(arr.size)))
        samples += int(arr.size)
        if limit is not None and samples >= limit:
            break
    if not chunks:
        raise SystemExit("Kokoro returned no narration audio")
    return np.concatenate(chunks), segments


def choose_test_narration(pipeline, text, voice, speed, max_seconds):
    words = str(text).split()
    if not words:
        raise SystemExit("No story words available for the test excerpt")
    low, high = 1, len(words)
    best = None
    while low <= high:
        mid = (low + high) // 2
        candidate = " ".join(words[:mid])
        audio, segments = synthesize(pipeline, candidate, voice, speed, max_seconds=max_seconds)
        duration = len(audio) / 24000.0
        if duration <= max_seconds + 0.01:
            best = (candidate, audio, segments)
            low = mid + 1
        else:
            high = mid - 1
    if not best:
        candidate = words[0]
        audio, segments = synthesize(pipeline, candidate, voice, speed, max_seconds=max_seconds)
        best = (candidate, audio, segments)
    return best


def phrase_chunks(text, max_words=3):
    words = str(text).split()
    return [" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words)]


def caption_events(text, tts_segments, speech_duration, start_offset=0.0):
    events = []
    cursor = 0.0
    segment_words = sum(len(seg.split()) for seg, samples in tts_segments if seg and samples > 0)
    total_words = max(1, len(str(text).split()))
    coverage = segment_words / total_words
    usable = [(seg, samples) for seg, samples in tts_segments if seg and samples > 0]
    if usable and coverage >= 0.75:
        for seg_text, samples in usable:
            seg_start = cursor
            seg_duration = min(samples / 24000.0, max(0.0, speech_duration - seg_start))
            if seg_duration <= 0:
                break
            chunks = phrase_chunks(seg_text, 3)
            weights = [max(1, sum(len(w.strip(".,!?;:\"()[]{}")) for w in c.split())) for c in chunks]
            total = max(1, sum(weights))
            local = seg_start
            for idx, (chunk, weight) in enumerate(zip(chunks, weights)):
                end = min(speech_duration, seg_start + seg_duration if idx == len(chunks) - 1 else local + seg_duration * weight / total)
                if end > local + 0.03:
                    events.append(f"Dialogue: 0,{ass_time(start_offset + local)},{ass_time(start_offset + end)},Main,,0,0,0,,{caption_ass_text(chunk.upper())}")
                local = end
            cursor = min(speech_duration, seg_start + seg_duration)
    else:
        chunks = phrase_chunks(text, 3)
        weights = [max(1, sum(len(w.strip(".,!?;:\"()[]{}")) for w in c.split())) for c in chunks]
        total = max(1, sum(weights))
        for idx, (chunk, weight) in enumerate(zip(chunks, weights)):
            end = speech_duration if idx == len(chunks) - 1 else min(speech_duration, cursor + speech_duration * weight / total)
            if end > cursor + 0.03:
                events.append(f"Dialogue: 0,{ass_time(start_offset + cursor)},{ass_time(start_offset + end)},Main,,0,0,0,,{caption_ass_text(chunk.upper())}")
            cursor = end
    return events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    args = parser.parse_args()
    request = load_json(args.request)
    selection_path = OUTPUT_DIR / "background_selection.json"
    background = OUTPUT_DIR / "background.asset"
    if not selection_path.exists() or not background.exists():
        raise SystemExit("Render requires resolved output/background_selection.json and background.asset")

    cfg = expected_video_config()
    fps = cfg["fps"]
    if (cfg["width"], cfg["height"]) != (VIDEO_WIDTH, VIDEO_HEIGHT):
        raise SystemExit("Wacky Dramas renderer requires fixed 720x1280 production dimensions")
    if fps <= 0:
        raise SystemExit("VIDEO_FPS must be positive")
    W, H = VIDEO_WIDTH, VIDEO_HEIGHT

    story = request["story"]
    narration_cfg = request["narration"]
    script = str(story["script"]).strip()
    hook = str(story["hook"]).strip()
    channel_name = request["channel"]["name"]
    handle = request["channel"]["handle"]
    voice = narration_cfg["voice"]
    speed = float(narration_cfg["speed"])
    test_mode = env_bool("STORY_TEST_MODE", False)
    test_max = float(os.getenv("STORY_RENDER_MAX_SECONDS", "5"))
    if test_mode and not 1.0 <= test_max <= 15.0:
        raise SystemExit("STORY_RENDER_MAX_SECONDS must be 1-15 seconds in test mode")

    from kokoro import KPipeline
    import soundfile as sf

    pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    story_text = story_body_without_repeated_hook(script, hook)
    if not story_text:
        raise SystemExit("story.script must contain story narration after the opening card hook")

    # Phase 1: read the complete card hook while the card is fully visible.
    # There are deliberately no subtitle events for this audio.
    intro_audio, _intro_segments = synthesize(pipeline, hook, voice, speed)
    intro_duration = len(intro_audio) / 24000.0

    # Phase 2: reserve a short silent transition while the card fades away.
    # Phase 3 begins only after the card has completely left the frame.
    story_budget = test_max - intro_duration - CARD_TRANSITION_SECONDS if test_mode else None
    if test_mode:
        if story_budget < 1.0:
            raise SystemExit(
                f"Opening card narration ({intro_duration:.3f}s) leaves too little room for a story excerpt "
                f"inside STORY_RENDER_MAX_SECONDS={test_max:.3f}s; shorten story.hook for testability."
            )
        narration_text, story_audio, tts_segments = choose_test_narration(
            pipeline, story_text, voice, speed, story_budget
        )
    else:
        narration_text = story_text
        story_audio, tts_segments = synthesize(pipeline, story_text, voice, speed)

    story_duration = len(story_audio) / 24000.0
    transition_samples = int(round(CARD_TRANSITION_SECONDS * 24000))
    transition_audio = np.zeros(max(1, transition_samples), dtype=np.float32)
    speech_audio = np.concatenate([intro_audio, transition_audio, story_audio])
    story_start = intro_duration + CARD_TRANSITION_SECONDS
    speech_duration = len(speech_audio) / 24000.0
    final_duration = speech_duration + END_TAIL_SECONDS
    if test_mode:
        if speech_duration > test_max + 0.05:
            raise SystemExit(f"Test narration {speech_duration:.3f}s exceeds STORY_RENDER_MAX_SECONDS={test_max:.3f}s")
    elif final_duration > PRODUCTION_MAX_SECONDS:
        raise SystemExit(
            f"Production duration {final_duration:.3f}s exceeds hard ceiling {PRODUCTION_MAX_SECONDS:.0f}s. "
            "Do not trim; create a shorter story with a new content_id."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    narration = OUTPUT_DIR / "narration.wav"
    sf.write(narration, speech_audio, 24000)

    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    brand = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dc, db = ImageDraw.Draw(card), ImageDraw.Draw(brand)

    box = CARD_BOX
    for offset, alpha in CARD_SHADOWS:
        shadow = (box[0] + offset, box[1] + offset, box[2] + offset, box[3] + offset)
        dc.rounded_rectangle(shadow, radius=CARD_RADIUS, fill=(0, 0, 0, alpha))
    dc.rounded_rectangle(
        box,
        radius=CARD_RADIUS,
        fill=(251, 251, 251, 252),
        outline=(28, 28, 28, 255),
        width=CARD_BORDER_WIDTH,
    )

    logo_path = ASSETS / "channel-avatar.png"
    if not logo_path.exists():
        raise SystemExit(f"Missing required asset: {logo_path}")
    with Image.open(logo_path) as src:
        src.load()
        logo = src.convert("RGBA").copy()
    rgb = logo.convert("RGB")
    stat = ImageStat.Stat(rgb)
    extrema = rgb.getextrema()
    if max(stat.mean) < 18 or sum(hi - lo for lo, hi in extrema) < 90:
        raise SystemExit("channel-avatar.png appears blank or corrupt")
    avatar = logo.resize((AVATAR_SIZE, AVATAR_SIZE), Image.Resampling.LANCZOS)
    mask = Image.new("L", (AVATAR_SIZE, AVATAR_SIZE), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, AVATAR_SIZE - 1, AVATAR_SIZE - 1), fill=255)
    clipped = Image.new("RGBA", (AVATAR_SIZE, AVATAR_SIZE), (0, 0, 0, 0))
    clipped.paste(avatar, (0, 0), mask)
    card.alpha_composite(clipped, AVATAR_POS)

    name_x, name_y = CHANNEL_NAME_POS
    name_font = font_px(FONT_BOLD, CHANNEL_NAME_FONT_SIZE)
    dc.text((name_x, name_y), channel_name, font=name_font, fill=(18, 18, 18, 255))
    name_bb = dc.textbbox((name_x, name_y), channel_name, font=name_font)
    verified = load_ui_icon("verified-blue.png", VERIFIED_ICON_SIZE)
    card.alpha_composite(
        verified,
        (int(name_bb[2] + VERIFIED_ICON_GAP), int(name_y + VERIFIED_ICON_Y_OFFSET)),
    )

    emojis = story.get("card_emojis", [])[:6]
    ix = name_x
    for emoji in emojis:
        img = render_emoji(str(emoji), EMOJI_TARGET_SIZE)
        x = int(ix + (EMOJI_CELL_SIZE - img.width) / 2)
        y = int(EMOJI_ROW_Y + (EMOJI_CELL_SIZE - img.height) / 2)
        card.alpha_composite(img, (x, y))
        ix += EMOJI_STEP_X

    hook_x, hook_y = HOOK_POS
    hook_font, hook_lines, line_height = fit_hook(
        dc, hook, HOOK_MAX_WIDTH, HOOK_MAX_HEIGHT
    )
    for i, line in enumerate(hook_lines):
        dc.text((hook_x, hook_y + i * line_height), line, font=hook_font, fill=(8, 8, 8, 255))

    light = (110, 110, 110, 255)
    meta_font = font_px(FONT_REG, FOOTER_FONT_SIZE)
    like = load_ui_icon("like.png", LIKE_ICON_SIZE)
    comment = load_ui_icon("comment.png", COMMENT_ICON_SIZE)
    share = load_ui_icon("share.png", SHARE_ICON_SIZE)
    end = paste_icon_centered(card, like, LIKE_X, FOOTER_Y)
    draw_text_centered_y(dc, end + FOOTER_TEXT_GAP, FOOTER_Y, "99+", meta_font, light)
    end = paste_icon_centered(card, comment, COMMENT_X, FOOTER_Y)
    draw_text_centered_y(dc, end + FOOTER_TEXT_GAP, FOOTER_Y, "99+", meta_font, light)
    end = paste_icon_centered(card, share, SHARE_X, FOOTER_Y)
    draw_text_centered_y(dc, end + FOOTER_TEXT_GAP, FOOTER_Y, "Share", meta_font, light)

    def pill(draw, box, text, fnt, fill):
        draw.rounded_rectangle(
            box,
            radius=(box[3] - box[1]) // 2,
            fill=(0, 0, 0, 225),
            outline=(255, 255, 255, 70),
            width=PILL_OUTLINE_WIDTH,
        )
        centered_text(draw, box, text, fnt, fill)

    pill(db, HANDLE_PILL, handle, font_px(FONT_BOLD, HANDLE_FONT_SIZE), (255, 255, 255, 255))
    pill(
        db,
        SUBSCRIBE_PILL,
        "SUBSCRIBE",
        font_px(FONT_BOLD, SUBSCRIBE_FONT_SIZE),
        (255, 214, 40, 255),
    )

    card_path = OUTPUT_DIR / "story-card.png"
    brand_path = OUTPUT_DIR / "branding.png"
    card.save(card_path)
    brand.save(brand_path)

    events = caption_events(narration_text, tts_segments, story_duration, start_offset=story_start)
    ass = OUTPUT_DIR / "captions.ass"
    ass.write_text(build_ass_header() + "\n".join(events) + "\n", encoding="utf-8")

    video = OUTPUT_DIR / "short.mp4"
    card_fade_start = intro_duration
    card_fade_dur = CARD_TRANSITION_SECONDS
    filter_complex = (
        f"[0:v]fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},eq=brightness=-0.03:saturation=1.03[bg];"
        f"[1:v]format=rgba,fade=t=out:st={card_fade_start:.2f}:d={card_fade_dur:.2f}:alpha=1[card];"
        "[2:v]format=rgba[brand];"
        f"[bg][card]overlay=x=0:y='-{CARD_BOB_AMPLITUDE}*sin(PI*t/2)'[tmp1];"
        "[tmp1][brand]overlay=0:0[tmp2];"
        f"[tmp2]subtitles='{ass.as_posix()}'[v]"
    )
    run([
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", str(background),
        "-loop", "1", "-i", str(card_path),
        "-loop", "1", "-i", str(brand_path),
        "-i", str(narration),
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "3:a:0",
        "-t", f"{final_duration:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(video),
    ])
    meta = {
        "content_id": request["content_id"],
        "narration_voice": voice,
        "narration_speed": speed,
        "narration_seconds": round(speech_duration, 6),
        "card_title_text": hook,
        "card_title_seconds": round(intro_duration, 6),
        "card_transition_seconds": CARD_TRANSITION_SECONDS,
        "story_start_seconds": round(story_start, 6),
        "story_narration_seconds": round(story_duration, 6),
        "video_seconds": round(final_duration, 6),
        "resolution": f"{W}x{H}",
        "fps": fps,
        "end_tail_seconds": END_TAIL_SECONDS,
        "production_ceiling_seconds": PRODUCTION_MAX_SECONDS,
        "test_mode": test_mode,
        "test_render_max_seconds": test_max if test_mode else None,
        "narration_excerpt": narration_text if test_mode else None,
    }
    atomic_write_json(OUTPUT_DIR / "render-metadata.json", meta)
    print(json.dumps(meta, ensure_ascii=False))
    print(video)


if __name__ == "__main__":
    main()
