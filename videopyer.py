"""Class for playing and annotating video sources in Python using Tkinter."""
import json
import logging
import pathlib
import datetime

import tkinter
import tkinter.filedialog
import numpy as np
import cv2
import PIL.Image
import PIL.ImageTk

logger = logging.getLogger("VideoPyer")
logging.basicConfig(level=logging.INFO)

# Delay should be changed with caution
# Tkinter event loop gets flooded with delays < 60 ms
DELAY = 60

# Default colour options
BKG_COLOUR = "#3E4149"
COLOUR_MAP = {"blue": "#749CE2", "pink": "#E274CF", "green": "#8CE274"}


class VideoPyer:  # pylint: disable=too-many-instance-attributes

    """Play, pause and record position of mouse clicks on videos."""

    def __init__(self, window: tkinter.Tk, title: str) -> None:
        """Set up video frame and menus of GUI, variables and logging.

        Args:
            window (tkinter.Tk): Main instance of tkinter.Tk.
            title (str): Title of Tk window.
        """
        self.window = window
        self.window.title(title)
        self.window.configure(background=BKG_COLOUR)

        # Frame that will contain the video
        video_frame = tkinter.Frame(self.window)
        video_frame.pack(side=tkinter.TOP, pady=5)
        self.canvas = tkinter.Canvas(video_frame, bg=BKG_COLOUR)
        # Log position of double click on canvas to record salient 'point'
        self.canvas.bind("<Double-1>", self.log_point)
        # Log head direction arrow drawn on press and release of click
        self.canvas.bind("<Button-1>", self.log_click)
        self.canvas.bind("<ButtonRelease-1>", self.draw_line)
        self.arrow_start_x, self.arrow_start_y = None, None  # Store start pos of click
        # Remove a selected tk object on backspace
        self.canvas.bind("<BackSpace>", self.remove_tk_object)
        self.selected_tk_object = None  # Current object user selects
        # Rotate head direction arrow with Up or Down keys
        self.canvas.bind("<KeyPress>", self.rotate)
        self.canvas.focus_set()  # Enable listen to key presses by default
        self.canvas.pack()

        # Frame that will display the menu buttons
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
        # Mini menu to select marker colour for salient 'points'
        colours = list(COLOUR_MAP.keys())
        var = tkinter.StringVar(video_frame)
        var.set(colours[0])
        self.marker_colour = colours[0]
        opt_colour = tkinter.OptionMenu(
            video_frame,
            var,
            *colours,
            command=self.set_colour,
        )
        opt_colour.config(bg=BKG_COLOUR, width=8)
        opt_colour.place(x=3, y=3)

        # Set up some variables for logging (points and arrows are logged independently)
        self.annotation_logs = dict()
        self.tkid_to_idx = dict()
        self.arrow_head_x, self.arrow_head_y = 0, 0
        self.frame_counter, self.mouse_x, self.mouse_y = 0, 0, 0
        self.arrows_log_keys = [
            "frame_counter",
            "arrow_start_x",
            "arrow_start_y",
            "arrow_head_x",
            "arrow_head_y",
            "marker_colour",
        ]
        self.points_log_keys = ["frame_counter", "mouse_x", "mouse_y", "marker_colour"]

        self.filename = None  # File currently loaded
        self.vid = None  # OpenCV capture instance
        self.img = None  # Holds current frame of video

        self.window.mainloop()

    def set_colour(self, value: str) -> None:
        """Set colour of visible marker for double mouse clicks."""
        self.marker_colour = value

    def shrink(self, c_id: int, x: int, y: int, radius: int) -> None:
        """Shrink a Tk circle object over time before finalling removing it.

        Args:
            c_id (int): Integer ID of circle/oval object from Tk.
            x (int): X coord for circle centre.
            y (int): Y coord for circle centre.
            radius (int): Circle radius.
        """
        if radius > 0.0:
            radius -= 0.5
            self.canvas.coords(c_id, x - radius, y - radius, x + radius, y + radius)
            self.canvas.after(100, self.shrink, c_id, x, y, radius)
        else:
            self.canvas.delete(c_id)  # Remove circle entirely

    def log_point(self, event: tkinter.Event) -> None:
        """Log the (x,y) coords of double mouse click during video and the frame number.
        Coordinates are given from top left of canvas. A fading marker becomes visible."""
        logger.info(
            "Point (%d,%d). Frame %d. Colour %s.",
            event.x,
            event.y,
            self.frame_counter,
            self.marker_colour,
        )
        self.mouse_x, self.mouse_y = event.x, event.y
        self.arrow_start_x, self.arrow_start_y = (event.x, event.y)  # Potential arrow

        radius = 8
        c_id = self.canvas.create_oval(
            self.mouse_x - radius,
            self.mouse_y - radius,
            self.mouse_x + radius,
            self.mouse_y + radius,
            fill=COLOUR_MAP[self.marker_colour],
        )
        self.shrink(c_id, self.mouse_x, self.mouse_y, radius)  # Shrink circle over time

        # Add relevant keys to logs for current file
        for key in self.points_log_keys:
            self.annotation_logs[self.filename]["points"].setdefault(key, []).append(
                getattr(self, key)
            )

    def log_click(self, event: tkinter.Event) -> None:
        """Log (x,y) coords of mouse click during video. Check if user is clicking on
        existing line object to get ready for further commands (e.g. remove, rotate)."""
        self.arrow_start_x, self.arrow_start_y = event.x, event.y
        self.selected_tk_object = self.canvas.find_withtag("current")[
            0
        ]  # Top most object under mouse

    def draw_line(self, event: tkinter.Event) -> None:
        """Draw a line between on coords on press and release of click and log.
        The frame number recorded will be that at the time on release of click."""
        self.arrow_head_x, self.arrow_head_y = event.x, event.y
        # Only draw intentional arrows (i.e. not just a result from regular clicks)
        if (
            np.linalg.norm(
                np.array([self.arrow_start_x, self.arrow_start_y])
                - np.array([self.arrow_head_x, self.arrow_head_y])
            )
            > 20
        ):
            l_id = self.canvas.create_line(
                self.arrow_head_x,
                self.arrow_head_y,
                self.arrow_start_x,
                self.arrow_start_y,
                fill="yellow",
                arrow="first",
            )
            logger.info(
                "Arrow %d (%d,%d) -> (%d, %d). Frame %d. Colour %s.",
                l_id,
                self.arrow_start_x,
                self.arrow_start_y,
                self.arrow_head_x,
                self.arrow_head_y,
                self.frame_counter,
                self.marker_colour,
            )
            # Add arrow coordinates to logs
            for key in self.arrows_log_keys:
                self.annotation_logs[self.filename]["arrows"].setdefault(
                    key, []
                ).append(getattr(self, key))
            # Maintain standard indexing starting from 0
            self.tkid_to_idx[l_id] = (
                len(self.annotation_logs[self.filename]["arrows"]["arrow_start_x"]) - 1
            )
        self.arrow_start_x, self.arrow_start_y = None, None

    def remove_tk_object(self, event: tkinter.Event) -> None:
        """Remove the tk object that is currently selected from the canvas and logs
        (only head direction arrows are currently removeable from logs)."""
        if self.selected_tk_object:
            self.canvas.delete(self.selected_tk_object)
            logger.info("Object w/ id %d removed from canvas.", self.selected_tk_object)
            # Remove object from our logs
            remove_idx = self.tkid_to_idx.get(self.selected_tk_object)
            if remove_idx is not None:  # Else not a line object and thus not logged
                # Remove the object's recorded annotations for all keys
                for key in self.arrows_log_keys:
                    self.annotation_logs[self.filename]["arrows"].setdefault(key, [])
                    del self.annotation_logs[self.filename]["arrows"][key][remove_idx]
                # Decrement the indices larger than the object just removed
                for k in self.tkid_to_idx:
                    if k > self.selected_tk_object:
                        self.tkid_to_idx[k] -= 1
                del self.tkid_to_idx[self.selected_tk_object]
            self.selected_tk_object = None
        else:
            logger.info("No object selected to remove via %s.", event.keysym)

    def rotate(self, event: tkinter.Event) -> None:
        """Rotate the selected object by 1 degree (increment or decrement depending
        on Up or Down key press). Currently only head direction arrows can be rotated."""
        if (
            self.selected_tk_object
            and self.canvas.type(self.selected_tk_object) == "line"
        ):
            # Calculate angle between arrow and 0 radians East
            x0, y0, x1, y1 = self.canvas.coords(self.selected_tk_object)
            vec = np.array([x0 - x1, y0 - y1])
            unit_vec = vec / np.linalg.norm(vec)
            theta = np.arctan2(unit_vec[1], unit_vec[0])  # np.arctan2 takes (y, x)
            # Increment or decrement angle
            if event.keysym == "Up":
                theta += np.deg2rad(1)
            elif event.keysym == "Down":
                theta -= np.deg2rad(1)
            # Rotate arrow around it's origin
            radius = np.linalg.norm(np.array([x0, y0]) - np.array([x1, y1]))
            x0 = x1 + radius * np.cos(theta)
            y0 = y1 + radius * np.sin(theta)
            self.canvas.coords(self.selected_tk_object, x0, y0, x1, y1)
            logger.info(
                "Object %d rotated. Theta now %d degrees (w.r.t. East).",
                self.selected_tk_object,
                np.degrees(theta),
            )
            # Update log with new coords of head direction arrow
            arrow_idx = self.tkid_to_idx.get(self.selected_tk_object)
            self.annotation_logs[self.filename]["arrows"]["arrow_start_x"][
                arrow_idx
            ] = x1
            self.annotation_logs[self.filename]["arrows"]["arrow_start_y"][
                arrow_idx
            ] = y1
            self.annotation_logs[self.filename]["arrows"]["arrow_head_x"][
                arrow_idx
            ] = x0
            self.annotation_logs[self.filename]["arrows"]["arrow_head_y"][
                arrow_idx
            ] = y0
        else:
            logger.info("No object selected to move.")

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
        self.annotation_logs[self.filename]["points"] = dict()
        self.annotation_logs[self.filename]["arrows"] = dict()

        # Open video file
        self.vid = cv2.VideoCapture(file)
        if not self.vid.isOpened():
            raise ValueError("Unable to open video source", file)

        # Set appropriate dimensions for canvas
        width = self.vid.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.canvas.config(width=width, height=height)
        logger.info("Canvas set with width %d and height %d", width, height)

        # Reset counters and kick off video loop
        self.arrow_head_x, self.arrow_head_y = 0, 0
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
        return (False, None)  # i.e. no video is open

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

        # Save logs as json
        tstamp = datetime.datetime.now().strftime("%d%m%Y")
        with open(f"annotations-{tstamp}.json", "w", encoding="utf-8") as file:
            json.dump(self.annotation_logs, file, ensure_ascii=False, indent=4)


if __name__ == "__main__":

    VideoPyer(tkinter.Tk(), "VideoPyer")
