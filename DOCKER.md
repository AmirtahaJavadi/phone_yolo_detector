# راهنمای اجرای پروژه با Docker (ROS 2 Humble)

این راهنما نحوه‌ی اجرای پکیج `phone_yolo_detector` را با **ROS 2 Humble داخل Docker** روی Ubuntu 24.04 توضیح می‌دهد.

## چرا Docker؟
ROS 2 Humble روی Ubuntu 24.04 (Noble) به‌صورت رسمی پشتیبانی نمی‌شود. ساده‌ترین راه، اجرای Humble درون یک کانتینر Docker است که روی خود Ubuntu 24.04 نصب می‌شود.

---

## معماری

```
+-----------------------------------------------------+
| Host: Ubuntu 24.04 + Docker                         |
|                                                     |
|   +-----------------------------------------------+ |
|   | Container: osrf/ros:humble-desktop           | |
|   |   - ROS 2 Humble                             | |
|   |   - cv_bridge, vision_msgs, rqt_image_view   | |
|   |   - ultralytics + opencv-python-headless     | |
|   |                                               | |
|   |   /ros2_ws/src/phone_yolo_detector  <-- mount| |
|   |            (read-write bind mount)            | |
|   |                                               | |
|   |   network_mode: host (DDS + phone reachable)  | |
|   +-----------------------------------------------+ |
|         |                                           |
|         | X11 socket: /tmp/.X11-unix               |
|         v                                           |
|   rqt_image_view GUI on host display               |
+-----------------------------------------------------+
        |
        | HTTP MJPEG over Wi-Fi
        v
   +-----------------+
   | Phone: IP Webcam |
   +-----------------+
```

---

## پیش‌نیازها روی Host

### ۱) نصب Docker و Docker Compose
```bash
# نصب Docker Engine
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
newgrp docker   # یا logout و login مجدد

# بررسی نصب
docker --version
docker compose version
```

### ۲) (اختیاری) NVIDIA Container Toolkit برای GPU
فقط اگر GPU انویدیا دارید و می‌خواهید inference را روی GPU اجرا کنید:
```bash
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### ۳) مجوز X11 برای GUI (rqt_image_view)
```bash
xhost +local:docker
```
این دستور را بعد از هر ریستارت X اجرا کنید. برای پایداری می‌توانید آن در `~/.xprofile` قرار دهید.

---

## فایل‌های Docker که ساخته شده‌اند

| فایل | نقش |
|------|-----|
| `Dockerfile` | ایمیج CPU با ROS Humble + ultralytics |
| `Dockerfile.gpu` | ایمیج GPU با PyTorch+CUDA 11.8 |
| `docker-compose.yml` | پیکربندی اصلی (CPU) |
| `docker-compose.gpu.yml` | override برای GPU |
| `entrypoint.sh` | source کردن ROS و workspace |
| `.dockerignore` | جلوگیری از کپی build/install/log |

---

## گردش کار CPU (پیش‌فرض)

### مرحله ۱) ساخت ایمیج
```bash
cd phone_yolo_detector
docker compose build
```
این مرحله حدود ۵-۱۰ دقیقه طول می‌کشد (دانلود ایمیج پایه ~۱.۵GB + نصب پکیج‌ها).

### مرحله ۲) اجرای کانتینر به‌صورت تعاملی
```bash
xhost +local:docker           # یک بار در هر session
docker compose run --rm ros2 bash
```

حالا داخل کانتینر هستید. prompt باید چیزی شبیه `root@<hostname>:/ros2_ws#` باشد.

### مرحله ۳) بیلد workspace داخل کانتینر
```bash
cd /ros2_ws
colcon build --symlink-install
source install/setup.bash
```

> چون فولدر پروژه با `--symlink-install` به `/ros2_ws/src/phone_yolo_detector` مانت شده، اگر سورس را روی host تغییر دهید نیازی به بیلد مجدد نیست (فقط launch یا source مجدد).

### مرحله ۴) اجرای launch file
ابتدا مطمئن شوید اپ IP Webcam روی گوشی اجرا شده و IP آن را دارید (مثلاً `192.168.1.43`).
```bash
ros2 launch phone_yolo_detector detector_launch.py \
    phone_url:=http://192.168.1.43:8080/video \
    model:=yolov8n.pt \
    confidence:=0.4 \
    device:=cpu \
    frame_rate:=15.0
```

### مرحله ۵) دیدن تصویر با کادرهای تشخیص
در یک ترمینال دیگر روی host:
```bash
docker compose exec ros2 bash -c \
    "source /ros2_ws/install/setup.bash && ros2 run rqt_image_view rqt_image_view"
```
سپس در پنجره‌ی rqt، تاییپ `/yolo/annotated_image` را انتخاب کنید.

### مرحله ۶) بررسی تاپیک‌ها (در همان ترمینال دوم)
```bash
docker compose exec ros2 bash -c \
    "source /ros2_ws/install/setup.bash && ros2 topic list"

docker compose exec ros2 bash -c \
    "source /ros2_ws/install/setup.bash && ros2 topic echo /yolo/detections"
```

---

## گردش کار GPU (با NVIDIA)

### ساخت و اجرای ایمیج GPU
```bash
xhost +local:docker
docker compose -f docker-compose.yml -f docker-compose.gpu.yml build
docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --rm ros2 bash
```

### داخل کانتینر:
```bash
cd /ros2_ws
colcon build --symlink-install
source install/setup.bash

# بررسی دسترسی GPU
python3 -c "import torch; print('CUDA available:', torch.cuda.is_available())"

# اجرای launch با device=cuda:0
ros2 launch phone_yolo_detector detector_launch.py \
    phone_url:=http://192.168.1.43:8080/video \
    device:=cuda:0 \
    confidence:=0.4
```

---

## اجرای مستقیم launch بدون ورود به shell

برای automation یا اسکریپت:
```bash
# CPU
docker compose run --rm ros2 bash -c \
    "source /ros2_ws/install/setup.bash && \
     ros2 launch phone_yolo_detector detector_launch.py \
         phone_url:=http://192.168.1.43:8080/video"

# GPU
docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --rm ros2 bash -c \
    "source /ros2_ws/install/setup.bash && \
     ros2 launch phone_yolo_detector detector_launch.py \
         phone_url:=http://192.168.1.43:8080/video device:=cuda:0"
```

---

## توقف و پاکسازی

```bash
# توقف کانتینر در حال اجرا (Ctrl+C یا)
docker compose stop

# پاک کردن کانتینرها
docker compose down

# (احتیاط) پاک کردن ایمیج برای ساخت مجدد از صفر
docker compose down --rmi all

# پس از اتمام کار با GUI:
xhost -local:docker
```

---

## عیب‌یابی Docker

| مشکل | علت | راه‌حل |
|------|------|--------|
| `permission denied while trying to connect to Docker socket` | کاربر در گروه docker نیست | `sudo usermod -aG docker $USER && newgrp docker` |
| `Cannot open MJPEG stream` | شبکه host نباید bridge باشد | `network_mode: host` در compose فعال است؛ `ping 192.168.1.43` داخل کانتینر |
| `rqt_image_view` پنجره باز نمی‌کند | X11 forward فعال نیست | `xhost +local:docker` و `echo $DISPLAY` روی host، سپس `DISPLAY=:0` در env |
| `Could not load GLX_NV_swap_group` | درایور گرافیک | نادیده بگیرید؛ rqt کار می‌کند |
| `cuda unavailable` داخل GPU image | nvidia-container-toolkit نصب نیست | مرحله ۲ نصب را دوباره اجرا کنید |
| `ModelNotFound` اولین اجرا | در حال دانلود yolov8n.pt | حجم ~۶MB؛ آفلاین کار نمی‌کند |
| تغییرات کد اعمال نمی‌شود | بیلد stale | `colcon build --symlink-install` در /ros2_ws (نیازی به rebuild image نیست) |
| `cv_bridge ImportError` | cv_bridge نصب نیست | در Dockerfile هست؛ اگر نبود `apt install ros-humble-cv-bridge` |
| خطای shared memory در PyTorch | /dev/shm کوچک است | `docker compose run --rm --shm-size=2g ros2 bash` |
| DDS discovery نودها را پیدا نمی‌کند | multicast routing | `network_mode: host` ضروری است؛ `ROS_LOCALHOST_ONLY=0` تنظیم شده |

---

## نکات مهم

1. **`network_mode: host`** دو هدف دارد: DDS discovery نودها و دسترسی به گوشی روی Wi-Fi محلی. بدون آن، کانتینر نمی‌تواند با گوشی صحبت کند.

2. **Volume mount** فولدر پروژه به `/ros2_ws/src/phone_yolo_detector` مانت می‌شود. این یعنی هر تغییری در کد روی host بلافاصله در کانتینر قابل‌استفاده است (با `--symlink-install`).

3. **`yolo-cache` volume** وزن‌های مدل YOLO را بین ری‌استارت‌های کانتینر نگه می‌دارد تا هر بار دانلود مجدد نشود.

4. **برای multi-robot یا multi-domain** می‌توانید `ROS_DOMAIN_ID` را در env تنظیم کنید:
   ```bash
   ROS_DOMAIN_ID=42 docker compose run --rm ros2 bash
   ```

5. **برای مصاحبه/debugging** می‌توانید در کانتینر در حال اجرا وارد شوید:
   ```bash
   docker compose exec ros2 bash
   ```

6. **پایداری مدل YOLO** در ARM/Mac M1: ایمیج `osrf/ros:humble-desktop` فقط amd64 دارد. روی Apple Silicon از Rosetta استفاده کنید یا ایمیج arm64 بسازید.
