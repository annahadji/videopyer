# :video_camera: videopyer

VideoPyer is a small video player tool built using Python and Tkinter. It can save annotations from a video, including mouse position on clicks for different classes as well as arbitrary head direction arrows connecting two points, and their corresponding time point (i.e. frame number).

<p align="center">
  <img src="doc/example.gif" alt="animated" />
</p>

## Getting started

VideoPyer can be setup by cloning this repository and installing the dependencies in [requirements.txt](https://github.com/annahadji/videopyer/blob/main/requirements.txt) into a virtual environment. VideoPyer is a single Python file project. The following command can be run from the root of the repo,

`python videopyer.py`

This will launch the VideoPyer GUI. The following key bindings are available:

- Position of the mouse is recorded on a `double click`.
- A head direction arrow can be added by `click, hold and release` to draw the arrow; rotated via the `up` or `down` keys; and removed by `backspace` (when first selected via a click).

Annotations are saved in the same directory in [json](https://www.json.org/json-en.html) format, and are also logged to the terminal. Head direction arrows are saved in the form of the X and Y coordinates of both their start point and head. An example json file saved from VideoPyer is as follows:

```json
{
  "22_08_2008-1255-SINGLE00.raw": {
    "points": {
      "frame_counter": [43, 52, 62],
      "mouse_x": [398, 194, 274],
      "mouse_y": [191, 272, 176],
      "marker_colour": ["blue", "blue", "blue"]
    },
    "arrows": {
      "frame_counter": [24, 36],
      "arrow_start_x": [262, 315],
      "arrow_start_y": [396, 297],
      "arrow_head_x": [343, 364],
      "arrow_head_y": [391, 344],
      "marker_colour": ["blue", "blue"]
    }
  }
}
```

## Built with

VideoPyer has been tested on MacOS.

- [tkinter](https://docs.python.org/3/library/tkinter.html#module-tkinter) - Python interface to the Tk GUI toolkit
- [OpenCV](https://docs.opencv.org/master/d6/d00/tutorial_py_root.html) - video frame processing
