import subprocess
import signal
import sys
from pathlib import Path
from picamera2 import Picamera2

WIDTH, HEIGHT, FPS = 1280, 720, 30
LOOPBACK = "/dev/video10"
READY_FILE = Path("/tmp/bridge_ready")

picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(
    main={"format": "BGR888", "size": (WIDTH, HEIGHT)},
    controls={"FrameRate": float(FPS)},
))
picam2.start()

ffmpeg = subprocess.Popen(
    [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-pixel_format", "bgr24",
        "-video_size", f"{WIDTH}x{HEIGHT}",
        "-framerate", str(FPS),
        "-i", "pipe:0",
        "-f", "v4l2",
        "-vcodec", "rawvideo",
        "-pix_fmt", "yuv420p",
        LOOPBACK,
    ],
    stdin=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
)


def _shutdown(sig, frame):
    ffmpeg.stdin.close()
    ffmpeg.wait()
    picam2.stop()
    sys.exit(0)


signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT, _shutdown)

frames_sent = 0
print(f"Bridge: {WIDTH}x{HEIGHT}@{FPS}fps → {LOOPBACK}", flush=True)

try:
    while True:
        frame = picam2.capture_array()
        ffmpeg.stdin.write(frame.tobytes())
        frames_sent += 1
        if frames_sent == 5:
            READY_FILE.touch()
            print("Bridge ready.", flush=True)
except BrokenPipeError:
    print("Bridge: ffmpeg pipe fechado.", flush=True)
    _shutdown(None, None)
