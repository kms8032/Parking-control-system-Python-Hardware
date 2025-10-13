import os
import tkinter as tk
from PIL import Image, ImageTk
import cv2
from ultralytics import YOLO
import easyocr
import torch
import time
import Jetson.GPIO as GPIO
import threading
import socketio

sio = socketio.Client()

@sio.event
def connect():
    print("Socket.IO 서버에 연결되었습니다.")

@sio.event
def disconnect():
    print("서버 연결이 종료되었습니다.")

SERVER_URL = "http://192.168.0.20:5002"
try:
    sio.connect(SERVER_URL)
except Exception as e:
    print(f"서버 연결 실패: {e}")

engine_path = "/ocryolo/best.engine"
model = YOLO(engine_path)
cap = cv2.VideoCapture(0)
recognizer_model_path = '/ocryolo/custom.pth'
reader = easyocr.Reader(['ko'], recognizer=recognizer_model_path)

zone_x1, zone_y1 = 0, 0
zone_x2, zone_y2 = 640, 480
frame_count = 0

root = tk.Tk()
label = tk.Label(root)
label.pack()

servo_pin = 32
GPIO.setmode(GPIO.BOARD)
GPIO.setup(servo_pin, GPIO.OUT)
servo = GPIO.PWM(servo_pin, 50)
servo.start(0)

def set_servo_angle(angle):
    duty_cycle = 2 + (angle / 18)
    servo.ChangeDutyCycle(duty_cycle)
    time.sleep(0.5)
    servo.ChangeDutyCycle(0)

current_angle = 90
set_servo_angle(current_angle)

def control_servo():
    global current_angle
    target_angle = 180
    set_servo_angle(target_angle)
    print("모터를 위로 올립니다.")
    time.sleep(5)
    set_servo_angle(90)
    current_angle = 90
    print("모터가 90도로 돌아옵니다.")

last_recognized_plate = None
last_recognized_time = 0
block_time = 15

def show_frame():
    global frame_count, last_recognized_plate, last_recognized_time
    ret, frame = cap.read()
    if not ret:
        return
    frame = cv2.resize(frame, (640, 480))
    frame_count += 1
    cv2.rectangle(frame, (zone_x1, zone_y1), (zone_x2, zone_y2), (255, 0, 0), 2)
    if frame_count % 3 == 0:
        results = model(frame)
        for result in results:
            for box in result.boxes:
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                conf = box.conf[0].cpu().numpy()
                if conf > 0.5:
                    x1, y1, x2, y2 = xyxy
                    if (x1 >= zone_x1 and x2 <= zone_x2 and y1 >= zone_y1 and y2 <= zone_y2):
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        plate_texts = reader.readtext(frame[y1:y2, x1:x2])
                        if plate_texts:
                            plate_text_build = "".join([c[1] for c in plate_texts if c[1].strip()])
                            filtered_plate_text = "".join(filter(str.isdigit, plate_text_build))
                            if filtered_plate_text:
                                cv2.putText(frame, filtered_plate_text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36, 255, 12), 2)
                                print(f"인식된 숫자: {filtered_plate_text}")
                                if len(filtered_plate_text) == 4:
                                    current_time = time.time()
                                    if filtered_plate_text != last_recognized_plate or (current_time - last_recognized_time) > block_time:
                                        last_recognized_plate = filtered_plate_text
                                        last_recognized_time = current_time
                                        servo_thread = threading.Thread(target=control_servo)
                                        servo_thread.start()
                                        try:
                                            sio.emit('car_number', {'plate': filtered_plate_text})
                                            print(f"전송됨: {filtered_plate_text}")
                                        except Exception as e:
                                            print(f"전송 실패: {e}")
                                    else:
                                        print(f"{block_time}초 이내 동일 번호 재인식. 무시.")
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(frame_rgb)
    imgtk = ImageTk.PhotoImage(image=img)
    label.imgtk = imgtk
    label.configure(image=imgtk)
    root.after(1, show_frame)

show_frame()
root.mainloop()
cap.release()
cv2.destroyAllWindows()
servo.stop()
GPIO.cleanup()
try:
    sio.disconnect()
except:
    pass