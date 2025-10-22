import cv2
from ultralytics import YOLO

model = YOLO("yolov8m.pt")

results = model.track(source="/Users/kyumin/Parking-control-system-Python-Hardware/ShortestPath/tracking_file/도로 영상 2.mp4", show=False, save=True, name="/Users/kyumin/Parking-control-system-Python-Hardware/ShortestPath/tracking_file/test_result", classes=2)