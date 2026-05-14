FROM debian:bookworm-slim

# Raspberry Pi archive — libcamera com PiSP (obrigatório para Pi 5) e picamera2
RUN apt-get update \
    && apt-get install -y --no-install-recommends gnupg curl ca-certificates \
    && curl -fsSL https://archive.raspberrypi.com/debian/raspberrypi.gpg.key \
       | gpg --dearmor -o /usr/share/keyrings/raspberrypi.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/raspberrypi.gpg] \
       http://archive.raspberrypi.com/debian/ bookworm main" \
       > /etc/apt/sources.list.d/raspi.list \
    && printf 'Package: libcamera* libpisp* python3-picamera2\nPin: origin archive.raspberrypi.com\nPin-Priority: 1001\n' \
       > /etc/apt/preferences.d/raspberrypi \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-picamera2 \
        libpisp1 \
        libcamera-apps \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY bridge.py .

CMD ["python3", "bridge.py"]
