"""Class for playing and annotating video sources."""
import json
import logging
import pathlib
import datetime

import tkinter
import tkinter.filedialog
import cv2
import PIL.Image
import PIL.ImageTk

logger = logging.getLogger("VideoPyer")
logging.basicConfig(level=logging.INFO)

# Delay should be changed with caution
# Tkinter event loop gets flooded with delays < 60 ms
DELAY = 60
BKG_COLOUR = "#3E4149"
COLOUR_MAP = {"blue": "#749CE2", "pink": "#E274CF", "green": "#8CE274"}


class VideoPyer:  # pylint: disable=too-many-instance-attributes

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
        self.window.configure(background=BKG_COLOUR)

        # Frame that will contain the video
        video_frame = tkinter.Frame(self.window)
        video_frame.pack(side=tkinter.TOP, pady=5)
        self.canvas = tkinter.Canvas(video_frame, bg=BKG_COLOUR)
        # Log position of mouse click on canvas
        self.canvas.bind("<Button-1>", self.log_click_xy)
        self.canvas.pack()
        # Frame that will display menu buttons
        menu_frame = tkinter.Frame(self.window)
        menu_frame.pack(side=tkinter.BOTTOM, pady=5)

        # Button to select video
        self.btn_select = tkinter.Button(
            menu_frame,
            text="Select video",
            width=10,
            command=self.select_and_open_source,
            highlightbackground=BKG_COLOUR,
        )
        self.btn_select.grid(row=0, column=0)

        # Button to begin play
        self.btn_play = tkinter.Button(
            menu_frame,
            text="Play",
            width=8,
            command=self.resume_video,
            highlightbackground=BKG_COLOUR,
            state="disabled",
        )
        self.btn_play.grid(row=0, column=1)

        # Button to pause
        self.pause = False
        self.btn_pause = tkinter.Button(
            menu_frame,
            text="Pause",
            width=8,
            command=self.pause_video,
            highlightbackground=BKG_COLOUR,
            state="disabled",
        )
        self.btn_pause.grid(row=0, column=2)

        # Button to select marker colour
        colours = list(COLOUR_MAP.keys())
        self.marker_colour = colours[0]
        var = tkinter.StringVar(video_frame)
        var.set(colours[0])  # Default value
        self.opt_colour = tkinter.OptionMenu(
            video_frame, var, *colours, command=self.set_colour
        )
        self.opt_colour.config(bg=BKG_COLOUR, width=8)
        self.opt_colour.place(x=3, y=3)

        # Set up logging
        self.frame_counter, self.mouse_x, self.mouse_y = 0, 0, 0
        self.annotation_logs = dict()
        self.log_keys = ["frame_counter", "mouse_x", "mouse_y", "marker_colour"]

        self.filename = None
        self.vid = None
        self.img = None

        self.window.mainloop()

    def set_colour(self, value) -> None:
        """Set colour of visible marker for mouse clicks."""
        self.marker_colour = value

    def shrink(self, c_id: int, x: int, y: int, radius: int) -> None:
        """Shrink a Tk circle object over time before finalling removing it.

        Args:
            c_id (int): Integer ID of circle/oval object from Tk.
            x (int): X coord for circle centre.
            y (int): Y coord for circle centre.
            radius (int): Circle radius.
        """  # pylint: disable=invalid-name
        if radius > 0.0:
            radius -= 0.5  # Shrink radius
            self.canvas.coords(
                c_id, x - radius, y - radius, x + radius, y + radius
            )  # Change circle size
            self.canvas.after(100, self.shrink, c_id, x, y, radius)
        else:
            self.canvas.delete(c_id)  # Remove circle entirely

    def log_click_xy(self, event: tkinter.Event) -> None:
        """Log the (x,y) coords of mouse click during video and the frame number.
        Coordinates are given from top left."""
        logger.info(
            "Position (%d,%d). Frame %d. Colour %s.",
            event.x,
            event.y,
            self.frame_counter,
            self.marker_colour,
        )
        self.mouse_x = event.x
        self.mouse_y = event.y

        radius = 8  # Circle radius
        c_id = self.canvas.create_oval(
            self.mouse_x - radius,
            self.mouse_y - radius,
            self.mouse_x + radius,
            self.mouse_y + radius,
            fill=COLOUR_MAP[self.marker_colour],
        )
        self.shrink(c_id, self.mouse_x, self.mouse_y, radius)  # Shrink circle over time

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
        tstamp = datetime.datetime.now().strftime("%d%m%Y")
        with open(f"annotations-{tstamp}.json", "w", encoding="utf-8") as file:
            json.dump(self.annotation_logs, file, ensure_ascii=False, indent=4)


if __name__ == "__main__":

    VideoPyer(tkinter.Tk(), "VideoPyer")
