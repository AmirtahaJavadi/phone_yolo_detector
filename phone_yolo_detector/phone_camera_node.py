"""
Phone Camera Node
==================
Connects to an MJPEG stream produced by a phone app (e.g. "IP Webcam" on
Android, "iPCamera" on iOS) and republishes each JPEG frame as a ROS 2
sensor_msgs/Image message on /phone_camera/image_raw.

A CompressedImage variant is also published on
/phone_camera/image_raw/compressed when the `publish_compressed` parameter
is True (useful when running across machines with limited bandwidth).

Typical phone-side setup:
    1. Install "IP Webcam" (Android) or "iPCamera" (iOS).
    2. Start the server inside the app; it will print an HTTP URL such as
       http://192.168.1.43:8080
    3. Append /video to obtain the MJPEG stream URL and pass it to this node
       via the `url` parameter or the `phone_url` launch argument.
"""

import urllib.request

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage, Image


class PhoneCameraNode(Node):
    def __init__(self) -> None:
        super().__init__('phone_camera_node')

        # ---- Declare parameters (with sensible defaults) ----
        self.declare_parameter('url', 'http://192.168.1.43:8080/video')
        self.declare_parameter('frame_rate', 15.0)
        self.declare_parameter('publish_compressed', False)

        self.url = self.get_parameter('url').get_parameter_value().string_value
        self.frame_rate = float(
            self.get_parameter('frame_rate').get_parameter_value().double_value)
        self.publish_compressed = bool(
            self.get_parameter('publish_compressed').get_parameter_value().bool_value)

        # ---- Publishers ----
        self.bridge = CvBridge()
        self.image_pub = self.create_publisher(
            Image, '/phone_camera/image_raw', 10)

        if self.publish_compressed:
            self.compressed_pub = self.create_publisher(
                CompressedImage, '/phone_camera/image_raw/compressed', 10)
        else:
            self.compressed_pub = None

        # ---- MJPEG state ----
        self._stream = None
        self._buffer = bytes()

        # ---- Timer ----
        self.timer = self.create_timer(1.0 / self.frame_rate, self._tick)
        self.get_logger().info(
            f'PhoneCameraNode ready. url={self.url}  fps={self.frame_rate}  '
            f'compressed={self.publish_compressed}')

    # ------------------------------------------------------------------ #
    def _open_stream(self) -> bool:
        try:
            self._stream = urllib.request.urlopen(self.url, timeout=5)
            self.get_logger().info('MJPEG stream opened successfully.')
            return True
        except Exception as e:  # noqa: BLE001
            self.get_logger().error(f'Cannot open MJPEG stream: {e}')
            self._stream = None
            return False

    # ------------------------------------------------------------------ #
    def _tick(self) -> None:
        if self._stream is None:
            self._open_stream()
            return

        try:
            # Read until we have at least one complete JPEG frame.
            while True:
                self._buffer += self._stream.read(4096)
                a = self._buffer.find(b'\xff\xd8')  # JPEG SOI
                b = self._buffer.find(b'\xff\xd9')  # JPEG EOI
                if a != -1 and b != -1 and b > a:
                    jpg = self._buffer[a:b + 2]
                    self._buffer = self._buffer[b + 2:]
                    self._publish_jpeg(jpg)
                    break
        except Exception as e:  # noqa: BLE001
            self.get_logger().warn(f'Stream read error: {e}; reconnecting...')
            self._stream = None

    # ------------------------------------------------------------------ #
    def _publish_jpeg(self, jpg_bytes: bytes) -> None:
        frame = cv2.imdecode(
            np.frombuffer(jpg_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            return

        stamp = self.get_clock().now().to_msg()

        img_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        img_msg.header.stamp = stamp
        img_msg.header.frame_id = 'phone_camera'
        self.image_pub.publish(img_msg)

        if self.compressed_pub is not None:
            comp = CompressedImage()
            comp.format = 'jpeg'
            comp.data = jpg_bytes
            comp.header.stamp = stamp
            comp.header.frame_id = 'phone_camera'
            self.compressed_pub.publish(comp)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = PhoneCameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
