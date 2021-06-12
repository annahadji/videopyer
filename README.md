# :video_camera: videopyer

VideoPyer is a small video player tool built using Python and Tkinter. It can also be used to save annotations from a video, including mouse position on clicks for different classes as well as arbitrary head direction arrows connecting two points, and their corresponding point in the video (i.e. frame number).

## Getting started

VideoPyer can be setup by cloning this repository and installing the dependencies specified in `requirements.txt` into a virtual environment. VideoPyer is a single Python file project. The following command can be run within the environment and from the root of the repo,

`python videopyer.py`

This will launch the VideoPyer GUI. The following key bindings are available:

- Position of the mouse is recorded on a `double click`.
- A head direction arrow can be added by `click, hold and release` to draw the arrow; rotated via the `up` or `down` keys; and removed by `backspace` (when first selected via a click).

Annotations are saved in the same directory in [json](https://www.json.org/json-en.html) format.

## Built with

- [tkinter](https://docs.python.org/3/library/tkinter.html#module-tkinter) - Python interface to the Tk GUI toolkit
- [OpenCV](https://docs.opencv.org/master/d6/d00/tutorial_py_root.html) - video frame processing
