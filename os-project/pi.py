import json
import os
import random
import socket
import threading
import time
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageTk


class DisplayController:
    def __init__(self, pc_ip, port=12345, memes_folder="memes", slides_folder="slides"):
        self.pc_ip = pc_ip
        self.port = port
        self.memes_folder = memes_folder
        self.slides_folder = slides_folder

        # Create folders if they don't exist
        os.makedirs(self.memes_folder, exist_ok=True)
        os.makedirs(self.slides_folder, exist_ok=True)

        # Initialize GUI
        self.root = tk.Tk()
        self.root.title("Smart Display - Raspberry Pi")
        self.root.configure(bg="black")

        # Make it fullscreen (uncomment for actual deployment)
        # self.root.attributes('-fullscreen', True)

        # Set window size for testing
        self.root.geometry("800x600")

        # Create label for displaying images
        self.image_label = tk.Label(self.root, bg="black")
        self.image_label.pack(expand=True, fill="both")

        # Status variables
        self.current_mode = None  # 'memes' or 'slides'
        self.current_images = []
        self.current_image_index = 0
        self.slide_timer = None
        self.socket = None
        self.connected = False

        # Load available images
        self.load_images()

        # Bind escape key to exit fullscreen
        self.root.bind("<Escape>", self.exit_fullscreen)
        self.root.bind("<KeyPress-q>", self.quit_app)

    def load_images(self):
        """Load available images from both folders"""
        self.memes = self.get_image_files(self.memes_folder)
        self.slides = self.get_image_files(self.slides_folder)

        print(f"Loaded {len(self.memes)} memes and {len(self.slides)} slides")

        if not self.memes:
            print(f"Warning: No images found in {self.memes_folder} folder")
        if not self.slides:
            print(f"Warning: No images found in {self.slides_folder} folder")

    def get_image_files(self, folder):
        """Get list of image files from a folder"""
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff"}
        images = []

        if os.path.exists(folder):
            for file in os.listdir(folder):
                if any(file.lower().endswith(ext) for ext in image_extensions):
                    images.append(os.path.join(folder, file))

        return images

    def display_image(self, image_path):
        """Display an image on the screen"""
        try:
            # Open and resize image to fit screen
            image = Image.open(image_path)

            # Get screen dimensions
            screen_width = self.root.winfo_width()
            screen_height = self.root.winfo_height()

            if screen_width <= 1 or screen_height <= 1:
                screen_width, screen_height = 800, 600

            # Resize image while maintaining aspect ratio
            image.thumbnail((screen_width, screen_height), Image.Resampling.LANCZOS)

            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(image)

            # Update label
            self.image_label.config(image=photo)
            self.image_label.image = photo  # Keep a reference

            print(f"Displaying: {os.path.basename(image_path)}")

        except Exception as e:
            print(f"Error displaying image {image_path}: {e}")
            self.show_error_message(
                f"Cannot display image: {os.path.basename(image_path)}"
            )

    def show_error_message(self, message):
        """Show error message on screen"""
        self.image_label.config(image="", text=message, fg="white", font=("Arial", 24))
        self.image_label.image = None

    def switch_to_memes(self):
        """Switch to displaying memes"""
        if self.current_mode == "memes":
            return

        print("Switching to memes mode")
        self.current_mode = "memes"
        self.current_images = self.memes
        self.current_image_index = 0

        # Stop slide timer if running
        if self.slide_timer:
            self.slide_timer.cancel()
            self.slide_timer = None

        if self.current_images:
            # Show random meme
            random_meme = random.choice(self.current_images)
            self.display_image(random_meme)
        else:
            self.show_error_message("No memes available!\nAdd images to 'memes' folder")

    def switch_to_slides(self):
        """Switch to displaying slides"""
        if self.current_mode == "slides":
            return

        print("Switching to slides mode")
        self.current_mode = "slides"
        self.current_images = self.slides
        self.current_image_index = 0

        if self.current_images:
            self.show_next_slide()
        else:
            self.show_error_message(
                "No slides available!\nAdd images to 'slides' folder"
            )

    def show_next_slide(self):
        """Show the next slide and schedule the following one"""
        if not self.current_images or self.current_mode != "slides":
            return

        # Display current slide
        self.display_image(self.current_images[self.current_image_index])

        # Move to next slide
        self.current_image_index = (self.current_image_index + 1) % len(
            self.current_images
        )

        # Schedule next slide (5 seconds interval)
        self.slide_timer = threading.Timer(5.0, self.show_next_slide)
        self.slide_timer.start()

    def connect_to_pc(self):
        """Connect to PC and listen for face detection data"""
        while True:
            try:
                print(f"Attempting to connect to PC at {self.pc_ip}:{self.port}")
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.pc_ip, self.port))
                self.connected = True
                print("Connected to PC successfully!")

                # Listen for messages
                buffer = ""
                while self.connected:
                    try:
                        data = self.socket.recv(1024).decode()
                        if not data:
                            break

                        buffer += data
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            if line:
                                self.process_message(line)

                    except socket.error as e:
                        print(f"Socket error: {e}")
                        break

            except Exception as e:
                print(f"Connection error: {e}")
                self.connected = False

                if self.socket:
                    self.socket.close()
                    self.socket = None

                print("Retrying connection in 5 seconds...")
                time.sleep(5)

    def process_message(self, message):
        """Process incoming message from PC"""
        try:
            data = json.loads(message)
            face_detected = data.get("face_detected", False)

            if face_detected:
                # Person is facing the camera - show memes
                self.root.after(0, self.switch_to_memes)
            else:
                # Person is facing away - show slides
                self.root.after(0, self.switch_to_slides)

        except json.JSONDecodeError as e:
            print(f"Error parsing message: {e}")

    def exit_fullscreen(self, event=None):
        """Exit fullscreen mode"""
        self.root.attributes("-fullscreen", False)

    def quit_app(self, event=None):
        """Quit the application"""
        self.cleanup()
        self.root.quit()

    def cleanup(self):
        """Clean up resources"""
        self.connected = False

        if self.slide_timer:
            self.slide_timer.cancel()

        if self.socket:
            self.socket.close()

    def run(self):
        """Start the application"""
        # Start connection thread
        connection_thread = threading.Thread(target=self.connect_to_pc)
        connection_thread.daemon = True
        connection_thread.start()

        # Show initial message
        self.show_error_message("Connecting to PC...")

        # Start GUI
        try:
            self.root.mainloop()
        finally:
            self.cleanup()


if __name__ == "__main__":
    # Replace with your PC's IP address
    PC_IP = "192.168.1.100"  # Change this to your PC's actual IP address

    print("Smart Display Controller for Raspberry Pi")
    print("=========================================")
    print(f"Configured to connect to PC at: {PC_IP}")
    print("\nMake sure:")
    print("1. Your PC is running the face detection program")
    print("2. Both devices are on the same network")
    print("3. You have images in 'memes' and 'slides' folders")
    print("\nPress 'q' or Escape to quit")
    print("Starting display controller...")

    try:
        controller = DisplayController(PC_IP)
        controller.run()
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure you have the required packages installed:")
        print("pip install pillow")
