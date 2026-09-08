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


def run(cmd):
    subprocess.run(cmd, check=True)


def ass_time(seconds):
    cs = int(round(max(0.0, seconds) * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def escape_ass(text):
    return str(text).replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")


def phrase_chunks(text, max_words=3):
    words = text.split()
    return [" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words)]


def sentence_prefixes(text, max_words=42):
    sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+", text.strip()) if x.strip()]
    prefixes = []
    words = []
    for sentence in sentences:
        sw = sentence.split()
        if words and len(words) + len(sw) > max_words:
            break
        words.extend(sw)
        prefixes.append(" ".join(words))
        if len(words) >= max_words:
            break
    if not prefixes:
        words = text.split()[:max_words]
        if words:
            prefixes = [" ".join(words)]
    return prefixes


def synthesize(pipeline, text, voice, speed):
    audio_parts, segments = [], []
    for gs, _ps, segment_audio in pipeline(text, voice=voice, speed=speed):
        part = np.asarray(segment_audio, dtype=np.float32)
        if not part.size:
            continue
        audio_parts.append(part)
        segments.append((str(gs).strip() if gs is not None else "", len(part)))
    if not audio_parts:
        raise RuntimeError("Kokoro produced no audio")
    return np.concatenate(audio_parts), segments


def choose_test_narration(pipeline, script, voice, speed, max_seconds):
    prefixes = sentence_prefixes(script, max_words=42)
    target_low = max(1.5, max_seconds - 0.8)
    best = None
    for excerpt in prefixes:
        audio, segments = synthesize(pipeline, excerpt, voice, speed)
        duration = len(audio) / 24000.0
        best = (excerpt, audio, segments, duration)
        if duration >= target_low:
            break
    if best is None:
        raise RuntimeError("Could not derive a test excerpt")
    excerpt, audio, segments, duration = best
    if duration <= max_seconds:
        return excerpt, audio, segments

    words = excerpt.split()
    keep = max(3, int(len(words) * (max_seconds - 0.15) / duration))
    shorter = " ".join(words[:keep]).rstrip(",;:-")
    audio, segments = synthesize(pipeline, shorter, voice, speed)
    duration = len(audio) / 24000.0
    if duration > max_seconds:
        keep = max(3, int(keep * (max_seconds - 0.15) / duration))
        shorter = " ".join(words[:keep]).rstrip(",;:-")
        audio, segments = synthesize(pipeline, shorter, voice, speed)
    return shorter, audio, segments


def pick_existing(paths):
    for path in paths:
        if Path(path).exists():
            return path
    return None


def scaled(value, scale):
    return int(round(value * scale))


def font(path, base_size, scale):
    return ImageFont.truetype(path, max(12, scaled(base_size, scale)))


def wrap_pixels(draw, text, fnt, max_width, max_lines=3):
    lines, current = [], ""
    for word in str(text).split():
        trial = f"{current} {word}".strip()
        width = draw.textbbox((0, 0), trial, font=fnt)[2]
        if current and width > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines[:max_lines], len(lines) <= max_lines


def fit_hook(draw, text, max_width, max_height, scale):
    for base_size in range(64, 39, -2):
        fnt = font(FONT_BOLD, base_size, scale)
        lines, fits = wrap_pixels(draw, text, fnt, max_width, 6)
        bb = draw.textbbox((0, 0), "Ag", font=fnt)
        line_height = (bb[3] - bb[1]) + scaled(9, scale)
        widths_fit = all(draw.textlength(line, font=fnt) <= max_width for line in lines)
        if fits and widths_fit and len(lines) * line_height <= max_height:
            return fnt, lines, line_height
    raise ValueError("Complete opening hook cannot fit card bounds; refusing to truncate text")


def wrap_caption(text):
    cfg = expected_video_config()
    scale = cfg["width"] / 1080.0
    fnt = font(FONT_BOLD, 78, scale)
    max_width = cfg["width"] - 2 * scaled(156, scale) - 2 * scaled(9, scale)
    draw = ImageDraw.Draw(Image.new("L", (1, 1)))
    lines, current = [], ""
    for word in text.split():
        if draw.textlength(word, font=fnt) > max_width:
            raise ValueError("Caption word exceeds safe horizontal bounds")
        trial = (current + " " + word).strip()
        if current and draw.textlength(trial, font=fnt) > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    if len(lines) > 3:
        raise ValueError("Caption exceeds central three-line region")
    return "\n".join(lines)


def centered_text(draw, box, text, fnt, fill):
    x1, y1, x2, y2 = box
    bb = draw.textbbox((0, 0), text, font=fnt)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text((x1 + (x2 - x1 - tw) / 2, y1 + (y2 - y1 - th) / 2 - 2), text, font=fnt, fill=fill)


def load_ui_icon(name, target_size):
    path = UI_ASSETS / name
    if not path.exists():
        raise RuntimeError(f"Missing required UI asset: {path}")
    with Image.open(path) as source:
        source.load()
        icon = source.convert("RGBA").copy()
    bbox = icon.getchannel("A").getbbox()
    if not bbox:
        raise RuntimeError(f"UI asset has no visible pixels: {path}")
    icon = icon.crop(bbox)
    return ImageOps.contain(icon, (target_size, target_size), method=Image.Resampling.LANCZOS)


def paste_icon_centered(canvas, icon, x, center_y):
    y = int(round(center_y - icon.height / 2))
    canvas.alpha_composite(icon, (int(x), y))
    return int(x + icon.width)


def draw_text_centered_y(draw, x, center_y, text, fnt, fill):
    bb = draw.textbbox((0, 0), text, font=fnt)
    y = center_y - (bb[3] - bb[1]) / 2 - bb[1]
    draw.text((x, y), text, font=fnt, fill=fill)
    return bb[2] - bb[0]


def render_emoji(icon, target_size, scale):
    # NotoColorEmoji on Debian is a bitmap font with a native 109px strike.
    # Render at that supported size first, then downscale the bitmap for
    # the configured canvas. Scaling the font size itself makes Pillow
    # reject the strike at 720p and previously caused every emoji to fall
    # back to an identical dot.
    for emoji_font in EMOJI_FONT_CANDIDATES:
        if not Path(emoji_font).exists():
            continue
        try:
            tile_size = 150
            tile = Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(tile)
            preferred_size = 109 if "ColorEmoji" in emoji_font else 96
            fnt = ImageFont.truetype(emoji_font, preferred_size)
            bb = draw.textbbox((0, 0), icon, font=fnt, embedded_color=True)
            x = (tile_size - (bb[2] - bb[0])) / 2 - bb[0]
            y = (tile_size - (bb[3] - bb[1])) / 2 - bb[1]
            draw.text((x, y), icon, font=fnt, embedded_color=True)
            bbox = tile.getbbox()
            if bbox:
                tile = tile.crop(bbox)
                return ImageOps.contain(tile, (target_size, target_size), method=Image.Resampling.LANCZOS)
        except (OSError, ValueError):
            continue
    raise RuntimeError(f"Unable to render requested card emoji: {icon}")

def caption_events(text, tts_segments, speech_duration):
    events = []
    usable = [(t, n) for t, n in tts_segments if t and n > 0]
    segment_words = sum(len(t.split()) for t, _ in usable)
    text_words = len(text.split())
    use_segments = bool(usable) and segment_words >= max(1, int(text_words * 0.75))
    cursor = 0.0
    if use_segments:
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
                    events.append(f"Dialogue: 0,{ass_time(local)},{ass_time(end)},Main,,0,0,0,,{escape_ass(wrap_caption(chunk.upper()))}")
                local = end
            cursor = min(speech_duration, seg_start + seg_duration)
    else:
        chunks = phrase_chunks(text, 3)
        weights = [max(1, sum(len(w.strip(".,!?;:\"()[]{}")) for w in c.split())) for c in chunks]
        total = max(1, sum(weights))
        for idx, (chunk, weight) in enumerate(zip(chunks, weights)):
            end = speech_duration if idx == len(chunks) - 1 else min(speech_duration, cursor + speech_duration * weight / total)
            if end > cursor + 0.03:
                events.append(f"Dialogue: 0,{ass_time(cursor)},{ass_time(end)},Main,,0,0,0,,{escape_ass(wrap_caption(chunk.upper()))}")
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
    W, H, fps = cfg["width"], cfg["height"], cfg["fps"]
    if W <= 0 or H <= 0 or fps <= 0:
        raise SystemExit("VIDEO_WIDTH, VIDEO_HEIGHT and VIDEO_FPS must be positive")
    sx, sy = W / 1080.0, H / 1920.0
    scale = min(sx, sy)

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

    pipeline = KPipeline(lang_code="a")
    if test_mode:
        narration_text, speech_audio, tts_segments = choose_test_narration(pipeline, script, voice, speed, test_max)
    else:
        narration_text = script
        speech_audio, tts_segments = synthesize(pipeline, script, voice, speed)

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

    box = tuple(scaled(v, sx if i % 2 == 0 else sy) for i, v in enumerate((56, 235, 1024, 805)))
    radius = scaled(36, scale)
    for off_base, alpha in ((10, 55), (18, 25)):
        offx, offy = scaled(off_base, sx), scaled(off_base, sy)
        shadow = (box[0] + offx, box[1] + offy, box[2] + offx, box[3] + offy)
        dc.rounded_rectangle(shadow, radius=radius, fill=(0, 0, 0, alpha))
    dc.rounded_rectangle(box, radius=radius, fill=(251, 251, 251, 252), outline=(28, 28, 28, 255), width=max(2, scaled(5, scale)))

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
    avatar_size = scaled(132, scale)
    avatar = logo.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (avatar_size, avatar_size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, avatar_size - 1, avatar_size - 1), fill=255)
    clipped = Image.new("RGBA", (avatar_size, avatar_size), (0, 0, 0, 0))
    clipped.paste(avatar, (0, 0), mask)
    card.alpha_composite(clipped, (scaled(82, sx), scaled(290, sy)))

    name_x, name_y = scaled(235, sx), scaled(285, sy)
    name_font = font(FONT_BOLD, 40, scale)
    dc.text((name_x, name_y), channel_name, font=name_font, fill=(18, 18, 18, 255))
    name_bb = dc.textbbox((name_x, name_y), channel_name, font=name_font)
    verified = load_ui_icon("verified-blue.png", scaled(38, scale))
    card.alpha_composite(verified, (int(name_bb[2] + scaled(18, sx)), int(name_y + scaled(4, sy))))

    emojis = story.get("card_emojis", [])[:6]
    icon_y = scaled(350, sy)
    ix = name_x
    icon_step = scaled(76, sx)
    icon_target = scaled(66, scale)
    for emoji in emojis:
        img = render_emoji(str(emoji), icon_target, scale)
        x = int(ix + (scaled(58, sx) - img.width) / 2)
        y = int(icon_y + (scaled(58, sy) - img.height) / 2)
        card.alpha_composite(img, (x, y))
        ix += icon_step

    hook_x, hook_y = scaled(86, sx), scaled(455, sy)
    hook_width, hook_height = scaled(900, sx), scaled(220, sy)
    hook_font, hook_lines, line_height = fit_hook(dc, hook, hook_width, hook_height, scale)
    for i, line in enumerate(hook_lines):
        dc.text((hook_x, hook_y + i * line_height), line, font=hook_font, fill=(8, 8, 8, 255))

    foot_y = scaled(742, sy)
    light = (110, 110, 110, 255)
    meta_font = font(FONT_REG, 30, scale)
    like = load_ui_icon("like.png", scaled(30, scale))
    comment = load_ui_icon("comment.png", scaled(31, scale))
    share = load_ui_icon("share.png", scaled(29, scale))
    end = paste_icon_centered(card, like, scaled(82, sx), foot_y)
    draw_text_centered_y(dc, end + scaled(10, sx), foot_y, "99+", meta_font, light)
    end = paste_icon_centered(card, comment, scaled(214, sx), foot_y)
    draw_text_centered_y(dc, end + scaled(10, sx), foot_y, "99+", meta_font, light)
    end = paste_icon_centered(card, share, scaled(868, sx), foot_y)
    draw_text_centered_y(dc, end + scaled(10, sx), foot_y, "Share", meta_font, light)

    def pill(draw, coords, text, fnt, fill):
        b = (scaled(coords[0], sx), scaled(coords[1], sy), scaled(coords[2], sx), scaled(coords[3], sy))
        draw.rounded_rectangle(b, radius=(b[3] - b[1]) // 2, fill=(0, 0, 0, 225), outline=(255, 255, 255, 70), width=max(1, scaled(2, scale)))
        centered_text(draw, b, text, fnt, fill)

    pill(db, (285, 1260, 795, 1334), handle, font(FONT_BOLD, 42, scale), (255, 255, 255, 255))
    pill(db, (360, 1348, 720, 1418), "SUBSCRIBE", font(FONT_BOLD, 38, scale), (255, 214, 40, 255))

    card_path = OUTPUT_DIR / "story-card.png"
    brand_path = OUTPUT_DIR / "branding.png"
    card.save(card_path)
    brand.save(brand_path)

    events = caption_events(narration_text, tts_segments, speech_duration)
    ass = OUTPUT_DIR / "captions.ass"
    font_size = scaled(78, scale)
    outline = max(3, scaled(7, scale))
    shadow = max(1, scaled(2, scale))
    margin_lr = scaled(156, sx)
    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Main,DejaVu Sans,{font_size},&H00FFFFFF,&H00FFFFFF,&H00101010,&H35000000,-1,0,0,0,100,100,0,0,1,{outline},{shadow},5,{margin_lr},{margin_lr},0,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    ass.write_text(ass_header + "\n".join(events) + "\n", encoding="utf-8")

    video = OUTPUT_DIR / "short.mp4"
    card_fade_start = min(1.70, max(0.0, final_duration - 0.30))
    card_fade_dur = min(0.30, max(0.05, final_duration - card_fade_start))
    filter_complex = (
        f"[0:v]fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},eq=brightness=-0.03:saturation=1.03[bg];"
        f"[1:v]format=rgba,fade=t=out:st={card_fade_start:.2f}:d={card_fade_dur:.2f}:alpha=1[card];"
        "[2:v]format=rgba[brand];"
        f"[bg][card]overlay=x=0:y='-{scaled(6, sy)}*sin(PI*t/2)'[tmp1];"
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
