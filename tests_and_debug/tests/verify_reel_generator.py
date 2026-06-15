"""Verification script to test ReelGenerator execution inside the Docker stack."""

import os
from pathlib import Path
from PIL import Image

from backend.services.reel_generator import ReelGenerator


def main() -> None:
    print("Starting ReelGenerator verification...")

    # 1. Establish paths
    if os.name != 'nt' and Path("/app").exists():
        temp_dir = Path("/app/outputs/temp")
    else:
        temp_dir = Path("outputs/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)

    mock_image_path = temp_dir / "mock_artwork.png"
    output_video_path = temp_dir / "mock_reel.mp4"

    # Clean up previous runs
    if output_video_path.exists():
        output_video_path.unlink()

    # 2. Create a mock image
    print("Creating mock source image...")
    img = Image.new("RGB", (1200, 1600), color=(100, 150, 200))
    img.save(mock_image_path)
    print(f"Mock image saved to: {mock_image_path}")

    # 3. Define a mock script
    reel_script = {
        "duration_seconds": 10,
        "hook": "This is a verified hook for vertical reels!",
        "cta": "Check the link in bio for prints!",
    }

    # 4. Instantiate and run generator
    print("Instantiating ReelGenerator and rendering video...")
    generator = ReelGenerator()
    result_path = generator.generate_reel(
        image_path=str(mock_image_path),
        output_path=str(output_video_path),
        reel_script=reel_script,
    )

    # 5. Assert outcomes
    print("Performing assertions...")
    assert os.path.exists(result_path), f"Output video file does not exist: {result_path}"
    assert os.path.isfile(result_path), f"Output is not a file: {result_path}"
    
    file_size = os.path.getsize(result_path)
    print(f"Generated video size: {file_size} bytes")
    assert file_size > 0, "Output video file is empty (0 bytes)"

    # Clean up temporary mock image
    if mock_image_path.exists():
        mock_image_path.unlink()

    print("\n==================================================")
    print("SUCCESS: ReelGenerator verified successfully!")
    print(f"Video file compiled at: {result_path}")
    print("==================================================")


if __name__ == "__main__":
    main()
