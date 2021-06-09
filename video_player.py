"""Class for playing and annotating video sources."""
import logging
import PIL.Image, PIL.ImageTk
import cv2
import tkinter

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
        self.canvas.bind("<Button-1>", self.get_click_xy)
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
        )
        self.btn_pause.grid(row=0, column=2)

        self.vid = None
        self.select_and_open_source()
        self.play_video()  # Kick off the video loop

        self.window.mainloop()

    def get_click_xy(self, event: tkinter.Event) -> None:
        """Get the x,y coordinates of a mouse on clicking in the video."""
        logger.info("Position (%d,%d)", event.x, event.y)

    def select_and_open_source(self) -> None:
        """Select and open a video file to play and/or annotate."""
        self.pause = False

        # Select file
        filename = "22_08_2008-1255-SINGLE00.raw.avi"  # TODO
        logger.info("Video file selected: %s.", filename)

        # Open video file
        self.vid = cv2.VideoCapture(filename)
        if not self.vid.isOpened():
            raise ValueError("Unable to open video source", filename)

        # Set appropriate W and H for canvas
        width = self.vid.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.canvas.config(width=width, height=height)
        logger.info("Canvas set with width %d and height %d", width, height)

    def get_frame(self) -> None:
        """Get the next frame from the video currently opened.

        Returns:
            Tuple[bool, Union[frame, None]: Boolean success flag for reading the frame,
                and the frame.
        """
        if self.vid.isOpened():
            ret, frame = self.vid.read()
            if ret:
                return (ret, frame)
        return (False, None)  # No video is open

    def play_video(self) -> None:
        """Play video in a loop if not paused."""
        ret, frame = self.get_frame()
        if ret:
            self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))
            self.canvas.create_image(0, 0, image=self.photo, anchor=tkinter.NW)

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
        """Release the video source when the object is destroyed."""
        if self.vid.isOpened():
            self.vid.release()


if __name__ == "__main__":

    VideoPlayer(tkinter.Tk(), "Video Player")
