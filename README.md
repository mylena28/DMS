# DMS — Driver Monitoring System

Orquestração de dois sistemas de detecção de comportamento do motorista rodando simultaneamente no Raspberry Pi com câmera IMX500, usando Docker Compose.

## Repositórios integrados

| Container | Repositório | Função |
|---|---|---|
| `fatigue-detection` | [euBrunoMelo/FatigueV1](https://github.com/euBrunoMelo/FatigueV1) | Detecção de fadiga por movimentação facial (landmarks, ONNX) |
| `drowsy-driving` | [mylena28/DrowsyDriving](https://github.com/mylena28/DrowsyDriving) | Detecção de comportamentos no volante (pose, objetos, YOLO ONNX) |
| `camera-bridge` | este repositório | Lê a câmera IMX500 e distribui frames para os outros dois |

## O problema que este projeto resolve

O hardware da câmera IMX500 só permite um processo por vez acessando o sensor. Sem orquestração, dois containers tentando abrir a câmera simultaneamente travam.

A solução usa **V4L2 Loopback**: o `camera-bridge` é o único processo que fala com a câmera real via libcamera/picamera2. Ele espelha os frames em `/dev/video10` (dispositivo virtual), e os outros dois containers leem desse espelho via OpenCV — sem conflito e sem perda de qualidade, pois os frames são transmitidos em formato raw (sem reencoding).

```
IMX500 (/dev/video0)
      │
      ▼
camera-bridge  ──── BGR888 via picamera2 ────►  FFmpeg  ──► /dev/video10 (loopback, YUV420P)
                                                                  │               │
                                                                  ▼               ▼
                                                        fatigue-detection   drowsy-driving
                                                        cv2.VideoCapture(0) cv2.VideoCapture(0)
```

Dentro de cada container de aplicação, `/dev/video10` é mapeado como `/dev/video0`, então o código original de cada repositório funciona sem modificação.

## Pré-requisitos

### Hardware
- Raspberry Pi 5
- Câmera Sony IMX500 (Raspberry Pi AI Camera)

### Software no host
- Docker e Docker Compose instalados
- Módulo V4L2 Loopback carregado:

```bash
sudo apt install v4l2loopback-dkms
sudo modprobe v4l2loopback devices=1 video_nr=10 card_label="VirtualCam" exclusive_caps=1
```

Para carregar automaticamente no boot:

```bash
echo "v4l2loopback" | sudo tee -a /etc/modules
echo "options v4l2loopback devices=1 video_nr=10 card_label=VirtualCam exclusive_caps=1" \
    | sudo tee /etc/modprobe.d/v4l2loopback.conf
```

Verificar se o dispositivo virtual foi criado:

```bash
v4l2-ctl --list-devices
# deve aparecer: VirtualCam (/dev/video10)
```

## Estrutura do projeto

```
DMS/
├── docker-compose.yml       # orquestração dos três containers
├── README.md
└── camera-bridge/
    ├── Dockerfile           # imagem mínima: picamera2 + ffmpeg
    └── bridge.py            # captura IMX500 e escreve no loopback
```

O código do `FatigueV1` é clonado automaticamente pelo Docker durante o build. O `DrowsyDriving` é lido do diretório `../DrowsyDriving` (repositório irmão).

## Como usar

### Primeiro uso (build + inicialização)

```bash
docker compose up --build
```

O build do `fatigue-detection` clona o repositório FatigueV1 do GitHub automaticamente.

### Usos seguintes (sem rebuild)

```bash
docker compose up
```

### Rodar em segundo plano

```bash
docker compose up -d
```

### Parar tudo

```bash
docker compose down
```

### Ver logs em tempo real

```bash
# todos os containers
docker compose logs -f

# apenas um
docker compose logs -f camera-bridge
docker compose logs -f fatigue-detection
docker compose logs -f drowsy-driving
```

### Rebuild de um container específico

```bash
docker compose build fatigue
docker compose up fatigue
```

## Ordem de inicialização

O Docker Compose garante a ordem correta automaticamente:

1. `camera-bridge` sobe e começa a capturar a câmera
2. Após 5 frames enviados ao loopback, o bridge sinaliza que está pronto (`/tmp/bridge_ready`)
3. O healthcheck detecta o sinal e libera o início dos outros dois containers
4. `fatigue-detection` e `drowsy-driving` sobem e encontram o loopback já ativo

Se o bridge cair, os outros containers reiniciam automaticamente (`restart: unless-stopped`).

## Resolução e FPS

O bridge captura a **1280×720 @ 30 FPS** para preservar o detalhe necessário para a detecção facial. Ambos os containers de aplicação recebem essa mesma resolução.

## Solução de problemas

### FFmpeg não consegue abrir `/dev/video10`

O flag `exclusive_caps=1` pode conflitar com o FFmpeg em algumas versões. Recarregue sem ele:

```bash
sudo modprobe -r v4l2loopback
sudo modprobe v4l2loopback devices=1 video_nr=10 card_label="VirtualCam"
```

### DrowsyDriving demora ~2 segundos a mais para iniciar

Normal. O código tenta inicializar o picamera2, aguarda 2 segundos, falha (a câmera real está com o bridge) e cai no fallback OpenCV. É um delay de startup único, sem impacto no desempenho em execução.

### Verificar grupos de vídeo no host

Os IDs de grupo `44` (video) e `993` (render) devem corresponder ao host. Para verificar:

```bash
getent group video render
```

Se os IDs forem diferentes, atualize os valores em `group_add` no `docker-compose.yml`.
