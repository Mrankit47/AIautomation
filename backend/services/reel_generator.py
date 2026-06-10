"""Service for generating real video reels from artwork using MoviePy and FFmpeg."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import numpy as np
from moviepy import VideoClip, vfx
from PIL import Image, ImageDraw, ImageFont

from backend.core.logging import get_logger

logger = get_logger(__name__)


class ReelGenerator:
    """Service to generate professional short-form vertical video reels from artwork."""

    def generate_reel(
        self,
        image_path: str,
        output_path: str,
        reel_script: dict[str, Any],
    ) -> str:
        """Generate a 1080x1920 MP4 reel from an image and script using MoviePy.

        Args:
            image_path: Absolute path to the source image file.
            output_path: Absolute path where the generated MP4 will be saved.
            reel_script: Dictionary containing hook, script, CTA, and duration.

        Returns:
            The output path of the generated video.
        """
        start_time = time.monotonic()
        logger.info("reel_render_started", image_path=image_path, output_path=output_path)

        # 1. Create output directory if it does not exist
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        # 2. Extract and validate duration
        duration = int(reel_script.get("duration_seconds", 15))
        duration = max(10, min(duration, 60))  # Clamp between 10 and 60 seconds

        # 3. Load input image
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Source image not found: {image_path}")

        img = Image.open(image_path)
        orig_w, orig_h = img.size

        # Vertical target: 1080x1920
        target_w = 1080
        target_h = 1920

        # Calculate crop boundaries for 9:16 aspect ratio
        crop_h = min(orig_h, int(orig_w * 16 / 9))
        crop_w = int(crop_h * 9 / 16)

        # Center of original image
        center_x = orig_w / 2
        center_y = orig_h / 2

        # Wrap text helper
        def _wrap_text(
            text: str,
            draw: ImageDraw.ImageDraw,
            font: ImageFont.FreeTypeFont,
            max_width: int,
        ) -> list[str]:
            lines: list[str] = []
            words = text.split()
            current_line: list[str] = []
            for word in words:
                test_line = " ".join(current_line + [word])
                w = draw.textlength(test_line, font=font)
                if w <= max_width:
                    current_line.append(word)
                else:
                    lines.append(" ".join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(" ".join(current_line))
            return lines

        # Font setup
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        try:
            font = ImageFont.truetype(font_path, 40)
        except Exception:
            logger.warning("dejavu_font_missing_using_default", font_path=font_path)
            font = ImageFont.load_default()

        # Frame generation function for MoviePy
        def make_frame(t: float) -> np.ndarray:
            p = t / duration  # Progress percentage (0.0 to 1.0)

            # --- Visual Effects: Ken Burns Zoom & Slow Pan ---
            # Zoom: from 1.0 to 1.12
            z = 1.0 + 0.12 * p

            # Pan: shift center slightly left-to-right (horizontal) or top-to-bottom (vertical)
            # We scale the pan offset by the remaining wiggle room
            wiggle_x = max(0, orig_w - crop_w)
            wiggle_y = max(0, orig_h - crop_h)

            pan_x = center_x + (p - 0.5) * wiggle_x * 0.1
            pan_y = center_y + (p - 0.5) * wiggle_y * 0.1

            current_crop_w = crop_w / z
            current_crop_h = crop_h / z

            # Compute bounding box
            left = max(0.0, pan_x - current_crop_w / 2)
            top = max(0.0, pan_y - current_crop_h / 2)
            right = min(float(orig_w), left + current_crop_w)
            bottom = min(float(orig_h), top + current_crop_h)

            # Crop and resize
            frame_img = img.crop((left, top, right, bottom)).resize(
                (target_w, target_h), Image.Resampling.LANCZOS
            )

            # --- Text Overlay (Pillow RGBA Draw) ---
            # Hook text for first 3 seconds, CTA text for last 3 seconds
            overlay_text = None
            if t < 3.0:
                overlay_text = reel_script.get("hook", "")
            elif duration - t < 3.0:
                overlay_text = reel_script.get("cta", "")

            if overlay_text:
                draw = ImageDraw.Draw(frame_img, "RGBA")
                card_x0 = 90
                card_x1 = 990
                padding = 40
                max_text_width = (card_x1 - card_x0) - 2 * padding

                lines = _wrap_text(overlay_text, draw, font, max_text_width)

                # Calculate text dimensions
                try:
                    line_height = font.getbbox("A")[3] - font.getbbox("A")[1] + 15
                except Exception:
                    line_height = 50

                total_text_height = len(lines) * line_height
                card_y1 = 1700
                card_y0 = card_y1 - total_text_height - 2 * padding

                # Draw dark card container
                draw.rounded_rectangle(
                    [card_x0, card_y0, card_x1, card_y1],
                    radius=20,
                    fill=(0, 0, 0, 180),
                )

                # Draw wrapped lines centered
                y = card_y0 + padding
                for line in lines:
                    try:
                        w = draw.textlength(line, font=font)
                    except Exception:
                        w = len(line) * 20
                    x = card_x0 + padding + (max_text_width - w) / 2
                    draw.text((x, y), line, fill=(255, 255, 255, 255), font=font)
                    y += line_height

            return np.array(frame_img)

        # 4. Compile video clip and render using MoviePy
        # Also apply fadein and fadeout (smooth transition)
        clip = VideoClip(make_frame, duration=duration)
        clip = clip.with_effects([vfx.FadeIn(1.0), vfx.FadeOut(1.0)])

        # Write to MP4 using libx264
        clip.write_videofile(
            str(out_file),
            fps=24,
            codec="libx264",
            audio=False,
            logger=None,  # Suppress moviepy progress bar to keep logs clean
        )
        clip.close()

        elapsed = (time.monotonic() - start_time) * 1000
        logger.info("reel_render_completed", output_path=output_path, execution_time_ms=elapsed)
        return output_path
