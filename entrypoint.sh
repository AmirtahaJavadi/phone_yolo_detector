#!/bin/bash
# Entrypoint for phone-yolo ROS 2 Humble container.
# Sources ROS and the workspace (if built), then exec's the user command.

set -e

echo "[entrypoint] Sourcing ROS 2 Humble ..."
source /opt/ros/humble/setup.bash

if [ -f /ros2_ws/install/setup.bash ]; then
    echo "[entrypoint] Sourcing workspace (install/setup.bash) ..."
    source /ros2_ws/install/setup.bash
else
    echo "[entrypoint] Workspace not built yet."
    echo "[entrypoint] Run inside container:"
    echo "[entrypoint]   cd /ros2_ws && colcon build --symlink-install"
    echo "[entrypoint]   source install/setup.bash"
fi

exec "$@"
