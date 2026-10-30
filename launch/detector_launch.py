"""
Launch file: phone camera + YOLO detector
==========================================

Starts two nodes:
  1) phone_camera_node   - reads MJPEG from the phone and publishes
                            /phone_camera/image_raw
  2) yolo_detector_node  - subscribes, runs YOLOv8 inference, publishes
                            /yolo/detections and /yolo/annotated_image

Usage:
    ros2 launch phone_yolo_detector detector_launch.py \
        phone_url:=http://192.168.1.43:8080/video model:=yolov8n.pt \
        confidence:=0.4 device:=cpu frame_rate:=15.0
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    # ---- Arguments ----
    phone_url_arg = DeclareLaunchArgument(
        'phone_url',
        default_value='http://192.168.1.43:8080/video',
        description='MJPEG URL produced by the IP Webcam app on the phone.')

    model_arg = DeclareLaunchArgument(
        'model',
        default_value='yolov8n.pt',
        description='YOLO weights (yolov8n.pt / yolov8s.pt / yolov8m.pt / ...).')

    conf_arg = DeclareLaunchArgument(
        'confidence',
        default_value='0.4',
        description='Detection confidence threshold (0.0 - 1.0).')

    device_arg = DeclareLaunchArgument(
        'device',
        description="Inference device: 'cpu' or 'cuda:0'.",
        default_value='cpu')

    fps_arg = DeclareLaunchArgument(
        'frame_rate',
        default_value='15.0',
        description='Frame rate at which frames are pulled from the phone.')

    # ---- Nodes ----
    phone_camera_node = Node(
        package='phone_yolo_detector',
        executable='phone_camera_node',
        name='phone_camera_node',
        parameters=[{
            'url': LaunchConfiguration('phone_url'),
            'frame_rate': ParameterValue(
                LaunchConfiguration('frame_rate'), value_type=float),
            'publish_compressed': False,
        }],
        output='screen',
    )

    yolo_detector_node = Node(
        package='phone_yolo_detector',
        executable='yolo_detector_node',
        name='yolo_detector_node',
        parameters=[{
            'model': LaunchConfiguration('model'),
            'confidence': ParameterValue(
                LaunchConfiguration('confidence'), value_type=float),
            'device': LaunchConfiguration('device'),
            'input_topic': '/phone_camera/image_raw',
        }],
        output='screen',
    )

    return LaunchDescription([
        phone_url_arg,
        model_arg,
        conf_arg,
        device_arg,
        fps_arg,
        phone_camera_node,
        yolo_detector_node,
    ])
