# Dockerfile - CPU version
# Builds a development image with ROS 2 Humble + YOLO dependencies.
# Source code is mounted at runtime (see docker-compose.yml), NOT copied.

FROM osrf/ros:humble-desktop

LABEL maintainer="user <user@example.com>"
LABEL description="ROS 2 Humble dev environment + Ultralytics YOLO for phone-yolo-detector"

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble
ENV QT_X11_NO_MITSHM=1
ENV ROS_LOCALHOST_ONLY=0

# ---- System dependencies (apt) ----
RUN apt-get update && apt-get install -y --no-install-recommends \
        ros-${ROS_DISTRO}-cv-bridge \
        ros-${ROS_DISTRO}-vision-msgs \
        ros-${ROS_DISTRO}-image-transport \
        ros-${ROS_DISTRO}-rqt-image-view \
        ros-${ROS_DISTRO}-image-pipeline \
        python3-pip \
        python3-colcon-common-extensions \
        python3-rosdep \
        python3-argcomplete \
        libgl1 \
        libglib2.0-0 \
        vim \
        git \
        wget \
        curl \
        bash-completion \
    && rm -rf /var/lib/apt/lists/*

# Initialize rosdep (idempotent; ignores error if already initialized)
RUN bash -c "source /opt/ros/${ROS_DISTRO}/setup.bash && \
             (rosdep init || true) && rosdep update"

# ---- Python ML dependencies ----
# cv_bridge provides system OpenCV bindings; ultralytics pulls torch (CPU)
RUN pip3 install --no-cache-dir \
        ultralytics \
        opencv-python-headless

# ---- Workspace ----
SHELL ["/bin/bash", "-c"]
WORKDIR /ros2_ws

# Persistent Ultralytics model cache (mounted volume in compose)
ENV YOLO_CONFIG_DIR=/root/.config/Ultralytics

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
