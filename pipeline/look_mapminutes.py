"""Map Minutes look, entry point for the channel-look convention ("look": "mapminutes" in channels/history.json):

    python pipeline/look_mapminutes.py <script.json> <build_dir> <channel.json>   # compose step (after voice.py)
    thumbnail.py imports this module and calls thumbnail(script, channel, out_png)

The look itself lives in pipeline/looks/: mapminutes.py (scenes, captions, sound, thumbnail), mm_pin.py (Pin's rig),
mm_geo.py (projections + public-domain map data), and assets/mapminutes/mm.js (camera, map moves, acting).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "looks"))
sys.path.insert(0, str(HERE))
import mapminutes  # noqa: E402


def thumbnail(script_path, channel_path, out_png):
    return mapminutes.thumbnail(script_path, channel_path, out_png)


def main(script_path, build_dir, channel_path):
    script = json.loads(Path(script_path).read_text())
    channel = json.loads(Path(channel_path).read_text())
    build = Path(build_dir)
    tl = json.loads((build / "timeline.json").read_text())
    return mapminutes.main(script, channel, build, tl)


if __name__ == "__main__":
    main(*sys.argv[1:4])
