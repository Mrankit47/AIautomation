"""Service for generating real video reels from artwork using MoviePy and FFmpeg."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import numpy as np
from moviepy import VideoClip, vfx, AudioFileClip
from PIL import Image, ImageDraw, ImageFont

from backend.core.logging import get_logger

logger = get_logger(__name__)


class ReelGenerator:
    """Service to generate professional short-form vertical video reels from artwork."""

    def validate_ffmpeg_env(self) -> None:
        """Verify that ffmpeg and ffprobe are installed and executable."""
        import shutil
        import subprocess
        
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            raise RuntimeError("ffmpeg binary not found in system PATH.")
            
        ffprobe_path = shutil.which("ffprobe")
        if not ffprobe_path:
            raise RuntimeError("ffprobe binary not found in system PATH.")
            
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except Exception as e:
            raise RuntimeError(f"ffmpeg check failed: {e}")
            
        try:
            subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
        except Exception as e:
            raise RuntimeError(f"ffprobe check failed: {e}")

    def _select_audio_track(self, analysis: dict[str, Any] | None) -> str:
        """Select background audio track dynamically based on artwork analysis."""
        audio_dir = (Path(__file__).parent.parent / "resources" / "audio").resolve().absolute()
        default_track = "ambient_dreamy_space.mp3"
        
        if not analysis:
            logger.info("no_analysis_provided_using_default_audio", default=default_track)
            return str(audio_dir / default_track)
        
        mood = str(analysis.get("mood", "")).lower()
        category = str(analysis.get("category", "")).lower()
        style = str(analysis.get("style", "")).lower()
        description = str(analysis.get("description", "")).lower()
        
        logger.info(
            "selecting_audio_for_artwork",
            mood=mood,
            category=category,
            style=style
        )
        
        # 12 Distinct tracks mapped to various aesthetic reels trends
        if "pixel" in style or "pixel" in mood or "pixel" in description or category == "pixel_art":
            track_name = "retro_arcade_chiptune.mp3"
        elif any(kw in mood for kw in ["cyberpunk", "synthwave", "cyber", "sci-fi", "space", "stars", "tech"]) or any(kw in style for kw in ["cyber", "synthwave", "space"]):
            track_name = "dark_synthwave_cyber.mp3"
        elif any(kw in mood for kw in ["sketch", "drawing", "pencil", "charcoal", "monochrome", "black and white"]) or any(kw in style for kw in ["line art", "sketch", "pencil"]):
            track_name = "chillhop_sketch_beats.mp3"
        elif any(kw in mood for kw in ["piano", "solitude", "melancholy", "classical", "deep", "thoughtful"]) or any(kw in style for kw in ["classical", "portrait"]):
            track_name = "classical_piano_solitude.mp3"
        elif any(kw in mood for kw in ["pop", "funky", "groove", "funk", "caricature", "bright", "colorful"]) or style == "pop_art" or category == "pop_art":
            track_name = "upbeat_pop_funky.mp3"
        elif any(kw in mood for kw in ["acoustic", "indie", "foliage", "plants", "garden", "rustic", "autumn", "spring", "folk"]):
            track_name = "acoustic_indie_nature.mp3"
        elif any(kw in mood for kw in ["tribal", "drums", "ancient", "mystical", "ethnic", "ritual", "statue", "ruins"]):
            track_name = "mystical_tribal_drums.mp3"
        elif any(kw in mood for kw in ["dark", "horror", "suspense", "gothic", "nightmare", "shadows", "surreal"]):
            track_name = "dramatic_suspense_dark.mp3"
        elif any(kw in mood for kw in ["energetic", "dynamic", "neon", "street", "pop", "intense", "action", "phonk", "happy", "fun", "bold", "vibrant"]):
            track_name = "trending_upbeat_phonk.mp3"
        elif any(kw in mood for kw in ["anime", "cartoon", "illustration", "line art", "warm", "cozy", "chill", "relaxed", "cute", "playful", "mellow", "retro", "nostalgic", "lo-fi", "lofi"]) or category == "anime" or category == "illustration" or style == "anime":
            track_name = "aesthetic_lofi_vibes.mp3"
        elif any(kw in mood for kw in ["grand", "majestic", "landscape", "oil painting", "traditional", "epic", "fantasy", "mysterious", "dramatic"]) or category == "photography" or style == "oil_painting" or style == "impressionism":
            track_name = "epic_cinematic_orchestral.mp3"
        elif any(kw in mood for kw in ["calm", "peaceful", "serene", "nature", "spiritual", "soft", "minimal", "watercolor", "pastel", "floral", "sad", "melancholic", "dreamy", "tranquil", "quiet", "forest"]):
            track_name = "ambient_dreamy_space.mp3"
        else:
            # Fallback based on category
            if category in ["anime", "illustration"]:
                track_name = "aesthetic_lofi_vibes.mp3"
            elif category == "photography":
                track_name = "epic_cinematic_orchestral.mp3"
            elif category == "digital_art":
                track_name = "trending_upbeat_phonk.mp3"
            else:
                track_name = default_track

        selected_path = (audio_dir / track_name).resolve().absolute()
        if not selected_path.exists():
            logger.warning("selected_audio_file_not_found_using_fallback", path=str(selected_path), fallback=default_track)
            selected_path = (audio_dir / default_track).resolve().absolute()
            
        logger.info("selected_audio_track", file=selected_path.name)
        return str(selected_path)

    def generate_reel(
        self,
        image_path: str,
        output_path: str,
        reel_script: dict[str, Any],
        analysis: dict[str, Any] | None = None,
        is_static: bool = False,
    ) -> str:
        """Generate a 1080x1920 MP4 reel with background music from an image and script using MoviePy.

        Args:
            image_path: Absolute path to the source image file.
            output_path: Absolute path where the generated MP4 will be saved.
            reel_script: Dictionary containing hook, script, CTA, and duration.
            analysis: Optional dictionary containing visual/emotional artwork analysis.
            is_static: If True, generate a high-performance static video (photo + music) without overlays/motion.

        Returns:
            The output path of the generated video.
        """
        # Validate that the environment is ready for rendering
        self.validate_ffmpeg_env()

        start_time = time.monotonic()
        logger.info("reel_render_started", image_path=image_path, output_path=output_path, is_static=is_static)

        # Initialize resource tracking variables
        img = None
        base_clip = None
        clip = None

        # 1. Create output directory if it does not exist
        out_file = Path(output_path).resolve().absolute()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        # 2. Extract and validate duration
        if is_static:
            duration = 15
        else:
            duration = int(reel_script.get("duration_seconds", 15))
            duration = max(10, min(duration, 60))  # Clamp between 10 and 60 seconds

        # 3. Load and potentially downscale source image to prevent OOM
        resolved_image_path = Path(image_path).resolve().absolute()
        if not resolved_image_path.exists():
            raise FileNotFoundError(f"Source image not found: {resolved_image_path}")

        with Image.open(resolved_image_path) as raw_img:
            img = raw_img.convert("RGB")
        
        orig_w, orig_h = img.size

        # Target vertical video: 720x1280 (Optimised for low-RAM Render Free tier)
        # Scale down original image if it is too large, saving RAM and CPU.
        # For non-static, target crop height of 1500px provides room for 1.12x Ken Burns zoom and pan.
        # For static, we don't need extra margin, so we can crop/resize directly.
        if not is_static:
            target_crop_h = 1500
            orig_crop_h = min(orig_h, int(orig_w * 16 / 9))
            if orig_crop_h > target_crop_h:
                scale_factor = target_crop_h / orig_crop_h
                new_w = int(orig_w * scale_factor)
                new_h = int(orig_h * scale_factor)
                logger.info("downscaling_source_image_for_rendering", original_size=(orig_w, orig_h), new_size=(new_w, new_h))
                img_resized = img.resize((new_w, new_h), Image.Resampling.BILINEAR)
                img.close()
                img = img_resized
                orig_w, orig_h = img.size

        # Vertical target: 720x1280
        target_w = 720
        target_h = 1280

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

        # Font setup (dynamic sizing based on target resolution width)
        font_size = int(target_w * 0.037)  # E.g. 26 for 720w, 40 for 1080w
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            logger.warning("dejavu_font_missing_using_default", font_path=font_path)
            font = ImageFont.load_default()

        # Frame generation function for MoviePy with memory optimization
        frame_counter = 0
        import gc
        
        static_frame = None

        def make_frame(t: float) -> np.ndarray:
            nonlocal frame_counter, static_frame
            frame_counter += 1
            if frame_counter % 24 == 0:
                gc.collect()

            if is_static:
                if static_frame is not None:
                    return static_frame
                
                left = max(0.0, center_x - crop_w / 2)
                top = max(0.0, center_y - crop_h / 2)
                right = min(float(orig_w), left + crop_w)
                bottom = min(float(orig_h), top + crop_h)
                
                frame_img = img.crop((left, top, right, bottom)).resize(
                    (target_w, target_h), Image.Resampling.BILINEAR
                )
                static_frame = np.array(frame_img)
                return static_frame

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

            # Crop and resize using BILINEAR for low-RAM environment compatibility
            frame_img = img.crop((left, top, right, bottom)).resize(
                (target_w, target_h), Image.Resampling.BILINEAR
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
                card_x0 = int(target_w * 0.083)  # Left margin
                card_x1 = int(target_w * 0.917)  # Right margin
                padding = int(target_w * 0.037)  # Padding inside card
                max_text_width = (card_x1 - card_x0) - 2 * padding

                lines = _wrap_text(overlay_text, draw, font, max_text_width)

                # Calculate text dimensions
                try:
                    line_height = font.getbbox("A")[3] - font.getbbox("A")[1] + int(target_w * 0.014)
                except Exception:
                    line_height = int(target_w * 0.046)

                total_text_height = len(lines) * line_height
                card_y1 = int(target_h * 0.885)  # Bottom margin
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
                        w = len(line) * font_size * 0.5
                    x = card_x0 + padding + (max_text_width - w) / 2
                    draw.text((x, y), line, fill=(255, 255, 255, 255), font=font)
                    y += line_height

            return np.array(frame_img)

        # 4. Compile video clip and render using MoviePy
        # Also apply fadein and fadeout (smooth transition)
        temp_silent_path = out_file.with_name(f"temp_silent_{out_file.name}").resolve().absolute()

        audio_attached = False
        try:
            base_clip = VideoClip(make_frame, duration=duration)
            clip = base_clip.with_effects([vfx.FadeIn(1.0), vfx.FadeOut(1.0)])

            # Write to temporary silent MP4 using libx264 (force threads=1 and audio=False for low-RAM stability)
            clip.write_videofile(
                str(temp_silent_path),
                fps=24,
                codec="libx264",
                preset="ultrafast",  # Minimize encoding overhead and CPU/memory usage
                threads=1,           # Force single-threaded rendering to prevent concurrent frame buffering OOM
                audio=False,         # Write silent video first to save memory (no audio decoding subprocess)
                logger=None,         # Suppress moviepy progress bar
            )
            # Explicitly close clips and images before merging audio to free maximum RAM
            clip.close()
            clip = None
            base_clip.close()
            base_clip = None
            img.close()
            img = None
            gc.collect()

            # 5. Merge background music using direct, lightweight FFmpeg subprocess (stream copy)
            try:
                audio_path = self._select_audio_track(analysis)
                if audio_path and os.path.exists(audio_path):
                    logger.info("merging_audio_via_ffmpeg", video_path=str(temp_silent_path), audio_path=audio_path)
                    import subprocess
                    
                    # Combine using copy codec for video (very fast and memory efficient) and recoding audio to AAC
                    # Trim audio to video duration using -shortest
                    cmd = [
                        "ffmpeg", "-y",
                        "-i", str(temp_silent_path),
                        "-i", audio_path,
                        "-map", "0:v",
                        "-map", "1:a",
                        "-c:v", "copy",
                        "-c:a", "aac",
                        "-strict", "-2",
                        "-shortest",
                        str(out_file)
                    ]
                    
                    # Run subprocess and capture output for detailed error logs
                    res = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    if res.returncode != 0:
                        raise RuntimeError(f"ffmpeg failed with exit code {res.returncode}. Stderr: {res.stderr}")
                    logger.info("audio_track_overlay_successful_via_ffmpeg")
                    audio_attached = True
                else:
                    logger.warning("audio_track_not_found_skipping_merge", path=audio_path)
            except Exception as ffmpeg_err:
                logger.error("ffmpeg_audio_merge_failed_falling_back_to_silent", error=str(ffmpeg_err))

            # Fallback: if merging failed or was skipped, use the silent video directly
            if not audio_attached:
                import shutil
                shutil.copy(temp_silent_path, out_file)
                logger.info("fallback_saved_silent_reel")

        finally:
            # Resource cleanup inside finally block to prevent memory/resource leaks
            if clip:
                try:
                    clip.close()
                except Exception:
                    pass
            if base_clip:
                try:
                    base_clip.close()
                except Exception:
                    pass
            if img:
                try:
                    img.close()
                except Exception:
                    pass

            # 6. Cleanup temporary silent file
            try:
                if temp_silent_path.exists():
                    temp_silent_path.unlink()
            except Exception as cleanup_err:
                logger.warning("failed_to_cleanup_temp_silent_file", error=str(cleanup_err))

            # Force garbage collection immediately to release memory
            gc.collect()

        elapsed = (time.monotonic() - start_time) * 1000
        logger.info("reel_render_completed", output_path=output_path, execution_time_ms=elapsed)
        return output_path
