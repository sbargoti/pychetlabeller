# Pychet Labeller
A python based annotation/labelling toolbox for images. The program allows the user to
annotate individual objects in images.

## Annotation variants
Currently Pychet labeller supports **Circle Labelling**. This enables the user to
annotate objects in an image with its centroid and its radius. This makes the
annotation toolbox particularly suitable for round objects such as fruits,
balls, coins etc.

## Installation
1. Clone this repository
    git clone https://github.com/sbargoti/pychetlabeller.git pychetlabeller
2. Add base directory (where pychetlabeller is stored) to python path by adding the following line to your ~/.bashrc
    export PYTHONPATH=$PYTHONPATH:$HOME/code/python/development/

## Usage
### Circle labelling toolbox
    python circles/circle_labeler.py
