import json
import socket
import threading
import time

import cv2


class FaceDetectionServer:
    def __init__(self, host="0.0.0.0", port=12345):
        self.host = host
        self.port = port
        self.socket = None
        self.client_socket = None
        self.running = False

        # Initialize face detection
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.cap = cv2.VideoCapture(0)

        if not self.cap.isOpened():
            raise Exception("Could not open webcam")

    def start_server(self):
        """Start the socket server to communicate with Raspberry Pi"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        print(f"Server listening on {self.host}:{self.port}")

        while self.running:
            try:
                self.client_socket, addr = self.socket.accept()
                print(f"Connected to Raspberry Pi at {addr}")
                break
            except socket.error:
                if self.running:
                    time.sleep(1)

    def detect_faces(self):
        """Detect faces and determine orientation"""
        ret, frame = self.cap.read()
        if not ret:
            return None

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)

        # Show the camera feed with face detection rectangles
        for x, y, w, h in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

        cv2.imshow("Face Detection - PC", frame)

        # Return True if faces are detected (person facing camera)
        return len(faces) > 0

    def send_status(self, face_detected):
        """Send face detection status to Raspberry Pi"""
        if self.client_socket:
            try:
                message = json.dumps({"face_detected": face_detected})
                self.client_socket.send((message + "\n").encode())
            except socket.error as e:
                print(f"Error sending data: {e}")
                self.client_socket = None

    def run(self):
        """Main loop"""
        self.running = True

        # Start server in a separate thread
        server_thread = threading.Thread(target=self.start_server)
        server_thread.daemon = True
        server_thread.start()

        print("Face detection started. Press 'q' to quit.")
        print(
            "Make sure your Raspberry Pi program is running and connects to this PC's IP address."
        )

        try:
            while self.running:
                face_detected = self.detect_faces()

                if face_detected is not None:
                    self.send_status(face_detected)

                # Check for quit command
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

                time.sleep(0.1)  # Small delay to prevent excessive CPU usage

        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        self.running = False

        if self.cap:
            self.cap.release()

        if self.client_socket:
            self.client_socket.close()

        if self.socket:
            self.socket.close()

        cv2.destroyAllWindows()
        print("Cleanup completed.")


if __name__ == "__main__":
    try:
        detector = FaceDetectionServer()
        detector.run()
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure you have a webcam connected and OpenCV is properly installed.")
        print("Install required packages with: pip install opencv-python")
