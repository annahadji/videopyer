"""Class for playing and annotating video sources."""
import json
import logging
import pathlib
import datetime

import cv2
import PIL.Image, PIL.ImageTk
import tkinter
import tkinter.filedialog

logger = logging.getLogger("VideoPlayer")
logging.basicConfig(level=logging.INFO)

# Delay should be changed with caution
# Tkinter event loop gets flooded with delays < 60 ms
DELAY = 60


class VideoPlayer:

    """Play, pause and record position of mouse clicks on videos."""

    def __init__(self, window: tkinter.Tk, title: str) -> None:
        """Set up video frame and menus. Default behaviour loads default video file
        and kicks off video loop.

        Args:
            window (tkinter.Tk): Main instance of tkinter.Tk.
            title (str): Title of Tk window.
        """
        # Set window title
        self.window = window
        self.window.title(title)
        self.window.configure(background="#3E4149")

        # Frame that will contain the video
        video_frame = tkinter.Frame(self.window)
        video_frame.pack(side=tkinter.TOP, pady=5)
        self.canvas = tkinter.Canvas(video_frame)
        # Log position of mouse click on canvas
        self.canvas.bind("<Button-1>", self.log_click_xy)
        self.canvas.pack()
        # Frame that will display menu buttons
        menu_frame = tkinter.Frame(self.window)
        menu_frame.pack(side=tkinter.BOTTOM, pady=5)

        # Button to select video
        self.btn_select = tkinter.Button(
            menu_frame,
            text="Select video source",
            width=15,
            command=self.select_and_open_source,
            highlightbackground="#3E4149",
        )
        self.btn_select.grid(row=0, column=0)

        # Button to begin play
        self.btn_play = tkinter.Button(
            menu_frame,
            text="Play",
            width=15,
            command=self.resume_video,
            highlightbackground="#3E4149",
            state="disabled",
        )
        self.btn_play.grid(row=0, column=1)

        # Button to pause
        self.pause = False
        self.btn_pause = tkinter.Button(
            menu_frame,
            text="Pause",
            width=15,
            command=self.pause_video,
            highlightbackground="#3E4149",
            state="disabled",
        )
        self.btn_pause.grid(row=0, column=2)

        # Set up logging
        self.frame_counter, self.mouse_x, self.mouse_y = 0, 0, 0
        self.annotation_logs = dict()
        self.log_keys = ["frame_counter", "mouse_x", "mouse_y"]

        self.filename = None
        self.vid = None
        self.img = None

        self.window.mainloop()

    def shrink(self, c: int, x: int, y: int, r: int) -> None:
        """Shrink a Tk circle object over time before finalling removing it.

        Args:
            c (int): Integer ID of circle/oval object from Tk.
            x (int): X coord for circle centre.
            y (int): Y coord for circle centre.
            r (int): Circle radius.
        """
        if r > 0.0:
            r -= 0.5  # Shrink radius
            self.canvas.coords(c, x - r, y - r, x + r, y + r)  # Change circle size
            self.canvas.after(100, self.shrink, c, x, y, r)
        else:
            self.canvas.delete(c)  # Remove circle entirely

    def log_click_xy(self, event: tkinter.Event) -> None:
        """Log the (x,y) coords of mouse click during video and the frame number.
        Coordinates are given from top left."""
        logger.info("Position (%d,%d). Frame %d.", event.x, event.y, self.frame_counter)
        self.mouse_x = event.x
        self.mouse_y = event.y

        r = 8  # Circle radius
        c = self.canvas.create_oval(
            self.mouse_x - r,
            self.mouse_y - r,
            self.mouse_x + r,
            self.mouse_y + r,
            fill="#E274CF",
        )
        self.shrink(c, self.mouse_x, self.mouse_y, r)  # Shrink circle over time

        # Add all relevant keys to logs for current file
        for key in self.log_keys:
            self.annotation_logs[self.filename].setdefault(key, []).append(
                getattr(self, key)
            )

    def select_and_open_source(self) -> None:
        """Select and open a video file to play and/or annotate."""
        self.pause = False

        # Select file
        file = tkinter.filedialog.askopenfilename(
            title="Select video source",
            filetypes=(
                ("MP4 files", "*.mp4"),
                ("AVI files", "*.avi"),
            ),
        )
        logger.info("Video file selected: %s.", file)

        # Save annotations for diff files as new dict entry
        # Warning: will overwrite existing annotations for a file if loaded again
        self.filename = pathlib.Path(file).stem
        self.annotation_logs[self.filename] = dict()

        # Open video file
        self.vid = cv2.VideoCapture(file)
        if not self.vid.isOpened():
            raise ValueError("Unable to open video source", file)

        # Set appropriate W and H for canvas
        width = self.vid.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.canvas.config(width=width, height=height)
        logger.info("Canvas set with width %d and height %d", width, height)

        # Reset counters and kick off video loop
        self.frame_counter, self.mouse_x, self.mouse_y = 0, 0, 0
        self.btn_pause["state"] = "normal"
        self.btn_play["state"] = "disabled"
        self.play_video()

    def get_frame(self) -> None:
        """Get the next frame from the video currently opened.

        Returns:
            Tuple[bool, Union[frame, None]: Boolean success flag for reading the frame,
                and the frame.
        """
        if self.vid.isOpened():
            ret, frame = self.vid.read()
            if ret:
                self.frame_counter += 1
                return (ret, frame)
        return (False, None)  # No video is open

    def play_video(self) -> None:
        """Play video in a loop if not paused."""
        ret, frame = self.get_frame()
        if ret:
            self.img = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))
            img_uid = self.canvas.create_image(0, 0, image=self.img, anchor=tkinter.NW)
            self.canvas.lower(img_uid)  # Allows marker for clicks to be visible

        if not self.pause:
            self.window.after(DELAY, self.play_video)
        else:
            # To make sure user doesn't click play after pausing faster than DELAY
            self.btn_play["state"] = "normal"

    def resume_video(self) -> None:
        """Enables pausing and resumes play function calls."""
        self.pause = False
        self.btn_pause["state"] = "normal"
        self.btn_play["state"] = "disabled"
        self.window.after(DELAY, self.play_video)

    def pause_video(self) -> None:
        """Set pause equals True."""
        self.pause = True
        self.btn_pause["state"] = "disabled"

    def __del__(self) -> None:
        """Release the video source when the object is destroyed, and save logs."""
        if self.vid.isOpened():
            self.vid.release()

        # Save logs
        dt = datetime.datetime.now().strftime("%d%m%Y")
        with open(f"annotations-{dt}.json", "w", encoding="utf-8") as f:
            json.dump(self.annotation_logs, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":

    VideoPlayer(tkinter.Tk(), "Video Player")
