"""
YOLO Detector Node
===================
Subscribes to /phone_camera/image_raw, runs Ultralytics YOLOv8 inference on
each frame, and publishes:

  * /yolo/detections         -> vision_msgs/msg/Detection2DArray
  * /yolo/annotated_image    -> sensor_msgs/msg/Image   (boxes drawn on frame)

Parameters
----------
model        : str   - YOLO weights file (yolov8n.pt by default). The
                      ultralytics library downloads it on first use.
confidence   : float - detection confidence threshold (0.0 - 1.0)
device       : str   - 'cpu' or 'cuda:0' (or any torch device string)
input_topic  : str   - input image topic (default /phone_camera/image_raw)
"""

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Header
from vision_msgs.msg import (
    BoundingBox2D,
    Detection2D,
    Detection2DArray,
    ObjectHypothesisWithPose,
)


class YoloDetectorNode(Node):
    def __init__(self) -> None:
        super().__init__('yolo_detector_node')

        # ---- Parameters ----
        self.declare_parameter('model', 'yolov8n.pt')
        self.declare_parameter('confidence', 0.4)
        self.declare_parameter('device', 'cpu')
        self.declare_parameter('input_topic', '/phone_camera/image_raw')

        self.model_path = self.get_parameter('model') \
            .get_parameter_value().string_value
        self.conf = float(self.get_parameter('confidence')
                          .get_parameter_value().double_value)
        self.device = self.get_parameter('device') \
            .get_parameter_value().string_value
        self.input_topic = self.get_parameter('input_topic') \
            .get_parameter_value().string_value

        # ---- Lazy import so that the node can start even before the model
        #      is fully downloaded.
        from ultralytics import YOLO
        self.model = YOLO(self.model_path)

        self.bridge = CvBridge()

        # ---- Sub / Pub ----
        self.create_subscription(
            Image, self.input_topic, self.image_callback, 10)
        self.det_pub = self.create_publisher(
            Detection2DArray, '/yolo/detections', 10)
        self.vis_pub = self.create_publisher(
            Image, '/yolo/annotated_image', 10)

        self.get_logger().info(
            f'YoloDetectorNode ready. model={self.model_path}  '
            f'conf={self.conf}  device={self.device}  in={self.input_topic}')

    # ------------------------------------------------------------------ #
    def image_callback(self, msg: Image) -> None:
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:  # noqa: BLE001
            self.get_logger().error(f'cv_bridge conversion failed: {e}')
            return

        results = self.model.predict(
            frame, conf=self.conf, device=self.device, verbose=False)

        det_array = Detection2DArray()
        det_array.header = Header()
        det_array.header.stamp = msg.header.stamp
        det_array.header.frame_id = msg.header.frame_id

        annotated = frame
        for r in results:
            annotated = r.plot()  # last result's overlay wins
            for box in r.boxes:
                x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
                cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
                w, h = x2 - x1, y2 - y1

                det = Detection2D()
                det.header = det_array.header
                det.bbox.center.position.x = cx
                det.bbox.center.position.y = cy
                det.bbox.size_x = w
                det.bbox.size_y = h

                cls_id = int(box.cls[0].item())
                score = float(box.conf[0].item())
                hyp = ObjectHypothesisWithPose()
                # class_id is a string in vision_msgs (ObjectHypothesis)
                hyp.hypothesis.class_id = str(cls_id)
                hyp.hypothesis.score = score
                det.results.append(hyp)

                det_array.detections.append(det)

        self.det_pub.publish(det_array)

        try:
            vis_msg = self.bridge.cv2_to_imgmsg(annotated, encoding='bgr8')
            vis_msg.header = det_array.header
            self.vis_pub.publish(vis_msg)
        except Exception as e:  # noqa: BLE001
            self.get_logger().warn(f'annotated publish failed: {e}')


def main(args=None) -> None:
    rclpy.init(args=args)
    node = YoloDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
