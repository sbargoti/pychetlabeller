# Pychet Labeller
A python based annotation/labelling toolbox for images. The program allows the user to
annotate individual objects in images.

## Annotation variants
Currently the pychet labeller supports **Circle Annotation** and **Rectangle
Annotation**.

The circle annotation enables the user to annotate objects in an image with its centroid and its radius. This makes the
annotation toolbox particularly suitable for round objects such as fruits, balls, coins etc.

The rectangle annotation annotates a box with top left position and its width
and height. This is more standard to what is used in the ML community where a
bounding box is scribed around objects.

## Why this toolbox
There are other examples out there (which also use PyQt) for labelling images.
Generally I found that they offered a lot of flexibility in the types of annotations
that could be done. However, this also meant that labelling very basic things
was very slow. For example, many tools allow you to annotate the vertices of
polygons and then type in the object name. However, the dataset I created this
for contained circular objects. All I wanted was to annotate a centroid and
object radius. For the rectangles, I didn't want to click on the vertices, which
can be difficult for complex shaped objects.

Additionally, I wanted a toolbox where you could see your bounding box/bounding
region live while moving the mouse around. And wanted some simple shortcuts to
changes its size and change the labelling output. Pychet Labeller aims to
address these features.

## Installation
1. Clone this repository
2. Add base directory (where pychetlabeller is stored) to python path by adding the line below to your ~/.bashrc

    git clone https://github.com/sbargoti/pychetlabeller.git pychetlabeller
    export PYTHONPATH=$PYTHONPATH:$HOME/code/python/development/

## Usage
### Circle labelling toolbox
    python circles/circle_labeler.py

### Rectangle labelling toolbox
    python rectangles/rectangle_labeler.py

### Labelling multiple images
Pychet Labeller makes it very easy to label a group of images in a folder, one
after the other. Simply run the labeller and open up the images directory form the push button on
the top right.

Annotations are made by simple clickin on the image. The user has the option to
move the image, change the size of the annotation tool, zoom in/out of the
image, change the object label, save the label or go to the next image. Press F1
to view the shortcuts for these things.

For circles, the size is the radius, and for rectangles, the size is the width
and height.

A few notes:
* Currently the program will automatically detect any .jpg and .png files.
* All images in a folder need to be of the same size. This is because image
  scale and position gets stored between images.
* When labelling multiple images, can enable save_label to automatically save
  the labels - otherwise press ctrl-x to save current annotations
* Individual annotations can be deleted by selecting them on the table and
  pressing delete.

### Annotations
The annotations are saved in csv format with the same name as the input image
file. The csv entries are *item, centre-x, centre-y, radius, label id*.

By default the annotations are saved in the image parent directory under a new
folder: circle-labels. The user can choose to manually set a different folder
for the labels.

### Single images
We can also edit circles/circle_labeler.py or rectangles/rectangle_labeler.py to quickly label one image. Under the object
MainWindow, uncomment self.quickview(), then under function quickview() set your image path.

## Future work
Extentions to labeller - coming soon:
* Currently the annotations are saved as csv files. A more standard format would
  be to use .xml format.
* The rectangle annotation toolbox has not been thoroughly tested - could have
  bugs.

## Bugs
Please contact author to report bugs @ bargoti.suchet@gmail.com
