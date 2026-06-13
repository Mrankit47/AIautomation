import os
import urllib.request

audio_dir = "backend/resources/audio"
os.makedirs(audio_dir, exist_ok=True)

tracks = {
    "ambient_dreamy_space.mp3": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
    "trending_upbeat_phonk.mp3": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
    "aesthetic_lofi_vibes.mp3": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
    "epic_cinematic_orchestral.mp3": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3",
    "dark_synthwave_cyber.mp3": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3",
    "chillhop_sketch_beats.mp3": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3",
    "classical_piano_solitude.mp3": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-7.mp3",
    "upbeat_pop_funky.mp3": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3",
    "acoustic_indie_nature.mp3": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-9.mp3",
    "mystical_tribal_drums.mp3": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-10.mp3",
    "retro_arcade_chiptune.mp3": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-11.mp3",
    "dramatic_suspense_dark.mp3": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-12.mp3"
}

for name, url in tracks.items():
    path = os.path.join(audio_dir, name)
    if not os.path.exists(path):
        print(f"Downloading {name}...")
        try:
            urllib.request.urlretrieve(url, path)
            print(f"Downloaded {name} successfully.")
        except Exception as e:
            print(f"Error downloading {name}: {e}")
    else:
        print(f"{name} already exists.")

