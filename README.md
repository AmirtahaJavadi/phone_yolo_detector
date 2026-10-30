# YOLO Phone Camera Detector — ROS 2

پکیج آماده‌ی تشخیص اشیاء با YOLO روی تصویر دوربین گوشی، برای ROS 2.

## نکته‌ی مهم درباره‌ی Ubuntu 24.04 و ROS 2 Humble

ROS 2 **Humble** به‌طور رسمی روی **Ubuntu 22.04 (Jammy)** ساپورت می‌شود،
نه Ubuntu 24.04 (Noble). روی Ubuntu 24.04 نسخه‌ی رسمی **ROS 2 Jazzy** است.
سه راه برای ادامه دارید:

| راه | مزیت | عیب |
|-----|------|-----|
| **(پیشنهادی) نصب ROS 2 Jazzy** روی Ubuntu 24.04 | کاملاً رسمی و پایدار | باید در فایل‌های `package.xml` کلمه‌ی `cv_bridge` و `vision_msgs` به‌صورت پیش‌فرض کار می‌کنند؛ فقط `rclpy` و نودها یکسان هستند |
| **نصب Humble داخل Docker** روی Ubuntu 24.04 | نسخه‌ی Humble اصلی، ایزوله | نیاز به mount کردن X11/PulseAudio برای rqt/image_view |
| **apt نصب دستی Humble روی Noble** | روی خود سیستم | unsupported، احتمال شکست dependencyها |

> توصیه: اگر تازه شروع می‌کنید و روی Ubuntu 24.04 هستید، **Jazzy** نصب کنید.
> کد این پکیج با هر دو نسخه کار می‌کند.

---

## معماری سیستم

```
          +--------------------+      MJPEG over HTTP      +------------------------+
   Phone  |  "IP Webcam" app   |  =====================>   |  phone_camera_node     |
          +--------------------+                            |  (urllib + cv2)        |
                                                          +-----------+------------+
                                                                      | sensor_msgs/Image
                                                                      | /phone_camera/image_raw
                                                                      v
                                                          +------------------------+
                                                          |  yolo_detector_node    |
                                                          |  Ultralytics YOLOv8    |
                                                          +-----+----------+-------+
                                                                |          |
                                /yolo/detections  <-------------+          |  /yolo/annotated_image
                                (vision_msgs/Detection2DArray)              (sensor_msgs/Image)
```

---

## نصب پیش‌نیازها

### ۱) نصب ROS 2

برای **Jazzy** (روی Ubuntu 24.04):
```bash
sudo apt update && sudo apt install -y software-properties-common
sudo add-apt-repository universe
sudo apt update && sudo apt install -y ros-jazzy-desktop
sudo apt install -y python3-colcon-common-extensions \
                    python3-rosdep python3-argcomplete
source /opt/ros/jazzy/setup.bash
```

اگر اصرار به **Humble** دارید، روی Docker:
```bash
docker run -it --net=host --device=/dev/video0 \
  -v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=$DISPLAY \
  osrf/ros:humble-desktop-full bash
```

### ۲) نصب وابستگی‌های پایتون
```bash
pip install --upgrade pip
pip install ultralytics opencv-python numpy
sudo apt install -y ros-${ROS_DISTRO}-cv-bridge \
                    ros-${ROS_DISTRO}-vision-msgs \
                    ros-${ROS_DISTRO}-image-transport \
                    ros-${ROS_DISTRO}-rqt-image-view
```

### ۳) آماده‌سازی workspace
```bash
mkdir -p ~/ros2_ws/src
cp -r phone_yolo_detector ~/ros2_ws/src/
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
```

---

## راه‌اندازی دوربین گوشی

1. روی اندروید اپ **IP Webcam** را نصب کنید (یا `iPCamera` روی iOS).
2. اپ را باز کنید و **Start server** را بزنید.
3. گوشی و سیستم باید روی یک Wi-Fi باشند.
4. آدرسی که پایین صفحه اپ نمایش داده می‌شود را یادداشت کنید؛ مثلاً:
   `http://192.168.1.43:8080`
5. آدرس استریم MJPEG با اضافه کردن `/video` ساخته می‌شود:
   `http://192.168.1.43:8080/video`

> در مرورگر سیستم می‌توانید همین URL را باز کنید و تصویر را ببینید.

---

## بیلد و اجرا

### بیلد:
```bash
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

### اجرا با launch file:
```bash
ros2 launch phone_yolo_detector detector_launch.py \
    phone_url:=http://192.168.1.43:8080/video \
    model:=yolov8n.pt \
    confidence:=0.4 \
    device:=cpu \
    frame_rate:=15.0
```

### اجرای نودها به‌صورت جدا:
```bash
# Terminal 1
ros2 run phone_yolo_detector phone_camera_node \
    --ros-args -p url:=http://192.168.1.43:8080/video

# Terminal 2
ros2 run phone_yolo_detector yolo_detector_node \
    --ros-args -p model:=yolov8n.pt -p confidence:=0.4 -p device:=cpu
```

---

## بررسی عملکرد

در یک ترمینال جدید:
```bash
# لیست تاپیک‌ها
ros2 topic list

# دیدن تصویر نهایی با کادرهای تشخیص
ros2 run rqt_image_view rqt_image_view
# سپس در GUI، /yolo/annotated_image را انتخاب کنید

# دیدن پیام‌های تشخیص به‌صورت متن
ros2 topic echo /yolo/detections

# دیدن نرخ فریم
ros2 topic hz /phone_camera/image_raw
ros2 topic hz /yolo/annotated_image
```

---

## توضیح فایل‌ها

| مسیر | نقش |
|------|-----|
| `phone_yolo_detector/phone_camera_node.py` | اتصال به استریم MJPEG گوشی، دیکد JPEG و انتشار `sensor_msgs/Image` |
| `phone_yolo_detector/yolo_detector_node.py` | اشتراک روی تصویر، اجرای YOLOv8، انتشار `Detection2DArray` و تصویر annotateشده |
| `launch/detector_launch.py` | اجرای هر دو نود با پارامترهای قابل تنظیم از خط فرمان |
| `package.xml` | تعریف پکیج و وابستگی‌ها |
| `setup.py` | ثبت entry point‌ها و نصب launch/config |

---

## عیب‌یابی رایج

| مشکل | علت احتمالی | راه‌حل |
|------|-------------|--------|
| `Cannot open MJPEG stream` | IP اشتباه یا گوشی در شبکه نیست | `ping 192.168.1.43`؛ مطمئن شوید هر دو روی همان Wi-Fi هستند |
| خطای `cv_bridge` در import | بسته نصب نیست | `sudo apt install ros-${ROS_DISTRO}-cv-bridge` |
| `ModuleNotFoundError: ultralytics` | پکیج پایتون نصب نیست | `pip install ultralytics` |
| اجرای کند روی CPU | مدل سنگین است | از `yolov8n.pt` (nano) استفاده کنید یا `device:=cuda:0` |
| عدم نمایش پنجره rqt | DISPLAY تنظیم نیست | `xhost +local:` و `export DISPLAY=:0` (در Docker) |
| `ModelNotFound` در اولین اجرا | در حال دانلود وزن‌هاست | اولین بار به اینترنت نیاز دارد؛ فایل در `~/.config/Ultralytics/` ذخیره می‌شود |

---

## توسعه‌های پیشنهادی

- اشتراک روی `/yolo/detections` در یک نود کنترلر و ارسال دستور به ربات.
- استفاده از `CompressedImage` برای کاهش پهنای باند (تنظیم `publish_compressed:=true`).
- تبدیل به‌صورت `image_transport` برای پشتیبانی از theora/h264.
- اجرای YOLO روی یک سرویس به‌جای subscription برای کاهش load زمانی.
