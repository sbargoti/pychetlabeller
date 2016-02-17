#! /usr/bin/python

__author__ = 'suchet'
__date__ = '17/02/16'

"""
Image annotation tool.
Annotate using rectangular shapes
"""

import sys, os, csv
import numpy as np

from PyQt4 import QtGui, QtCore
from pychetlabeller.rectangles.rectangle_labeller_ui import Ui_MainWindow

_colors = [[137,   0, 255],
           [255,   0,   0],
           [179, 179,   0],
           [  0, 255, 151],
           [  0, 193, 255],
           [  0,  27, 255],
           [137,   0, 255],
           [255, 165,   0],
           [255,   0,  41],
           [ 13, 255,   0],
           [255,   0, 207]]

class RectangleDrawPanel(QtGui.QGraphicsPixmapItem):
    """
    Establish a pixmap item on which labelling (painting) will be performed
    """
    def __init__(self, pixmap=None, parent=None, scene=None):
        super(RectangleDrawPanel, self).__init__()

        # Initialise variables
        # Class variables
        self.x, self.y = -1, -1 # Location of cursor
        self.parent = parent # Parent class - ui mainwindow
        self.current_scale = 1.
        self.defaultColorPixmap = None

        # Annotation parameters
        self.dx, self.dy = float(20), float(20)
        self.opacity = 60 # Opacity of annotation
        self.highlight_opacity = 100
        self.label = 1 # Label of annotation

        # Annotation results
        self.annotations = np.zeros((1000, 5), dtype=float) # x,y,xwidth,yheight,label
        self.object_counter = 0
        self.changeMade = None
        self.changeHeight = False
        self.changeWidth = False

        # Annotation drawing
        self.pen = QtGui.QPen(QtCore.Qt.SolidLine)
        self.pen.setColor(QtCore.Qt.black)
        self.pen.setWidth(1)
        self.num_labels = 9
        self.setBrushes()
        self.highlight_annotation = -1 # Index of highlighted annotation

        # Set up options
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable, True)
        self.setAcceptHoverEvents(True)
        self.MovingMode = False # Check if image is being moved

    def setBrushes(self):
        """
        Set the brushes for normal view, annotated view, highlighted view
        """
        self.testbursh =  QtGui.QBrush(QtGui.QColor(255, 255, 0, self.opacity))

        self.savebrush = QtGui.QBrush(QtGui.QColor(255, 0, 0, self.opacity))

        self.savebrushes = [QtGui.QBrush(QtGui.QColor(_colors[label_no][0],
                                                      _colors[label_no][1],
                                                      _colors[label_no][2],
                                                      self.opacity)) for label_no in range(10)]

        self.highlightbrush = QtGui.QBrush(QtGui.QColor(0, 0, 255, self.opacity))

        self.highlightbrushes = [QtGui.QBrush(QtGui.QColor(_colors[label_no][0],
                                                           _colors[label_no][1],
                                                           _colors[label_no][2],
                                                           self.highlight_opacity)) for label_no in range(10)]

    def paint(self, QPainter, QStyleOptionGraphicsItem, QWidget):
        """
        Painter to draw annotations
        """

        # Set image and pen
        QPainter.drawPixmap(0, 0, self.pixmap())
        QPainter.setPen(self.pen)

        # Draw a Rectangle at the current position of the mouse
        if self.x >= 0 and self.y >= 0:
            QPainter.setBrush(self.testbursh)
            # QPainter.drawEllipse(self.x-self.radius, self.y-self.radius, 2*self.radius, 2*self.radius)
            QPainter.drawRect(self.x, self.y, self.dx, self.dy)

        # Draw the annotated rectangles
        if self.object_counter > 0:
            for cc in range(self.object_counter):
                x, y, dx, dy = self.annotations[cc, :4] * self.current_scale
                l = self.annotations[cc, 4]
                QPainter.setBrush(self.savebrushes[int(l)])
                # QPainter.drawEllipse(i-r, j-r, 2*r, 2*r)
                QPainter.drawRect(x, y, dx, dy)

        # Draw the highlighted rectangles
        if self.highlight_annotation >= 0:
            x, y, r, l = self.annotations[self.highlight_annotation, :4] * self.current_scale
            l = self.highlight_annotation[cc,4]
            QPainter.setBrush(self.highlightbrushes[int(l)])
            # QPainter.drawEllipse(i-r, j-r, 2*r, 2*r)
            QPainter.drawRect(x, y, dx, dy)

    # Set events for mouse hovers - As the mouse enters the image, change to cross cursor,
    # and as it leaves the image, change to arrow cursor
    def hoverEnterEvent(self, QGraphicsSceneHoverEvent):
        self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))

    def hoverMoveEvent(self, QGraphicsSceneHoverEvent):
        """
        While moving inside the picture, update x,y position for drawing annotation tool
        If instead in moving mode (grab and move image), do nothing.
        """
        if not self.MovingMode:
            self.x=QGraphicsSceneHoverEvent.pos().x()
            self.y=QGraphicsSceneHoverEvent.pos().y()
            self.update()

    def hoverLeaveEvent(self, QGraphicsSceneHoverEvent):
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        # Reset position to stop drawing annotation circle outside the image
        self.x, self.y = -1, -1
        self.update()

    def mousePressEvent(self, QGraphicsSceneMouseEvent):
        """
        Record the annotation when mouse is clicked.
        If Image is in moving mode, prepare to move image
        """
        if self.MovingMode is False:
            self.setFlag(QtGui.QGraphicsItem.ItemIsMovable, False)
            self.annotations[self.object_counter, :] = self.x / self.current_scale, self.y / self.current_scale, \
                                                       self.dx / self.current_scale, self.dy / self.current_scale, \
                                                       self.label
            self.object_counter += 1
            self.changeMade = True

            # Add centroids to the parent tree widget
            self.parent.updateTree()
        else:
            self.setFlag(QtGui.QGraphicsItem.ItemIsMovable, True)
            print self.scenePos()
            self.setCursor(QtGui.QCursor(QtCore.Qt.ClosedHandCursor))

    def mouseReleaseEvent(self, QGraphicsSceneMouseEvent):
        """
        If image was in moving more, change cursor grab icon
        """
        if self.MovingMode is True:
            self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))

        QtGui.QGraphicsPixmapItem.mouseReleaseEvent(self, QGraphicsSceneMouseEvent)

    def setAnnotations(self, data):
        """
        Given a set of data, a nx4 dim numpy array, set the annotations
        Annotations order: centre-x, centre-y, raidus, label
        """
        self.annotations = np.zeros((1000, self.annotations.shape[1]), dtype=float) # x,y,width,height
        self.object_counter = data.shape[0]
        self.annotations[:self.object_counter, :] = data

    def resetAnnotations(self):
        """
        Reset all annotations for this pixmap
        """
        self.x, self.y = -1, -1
        self.annotations = np.zeros((1000, self.annotations.shape[1]), dtype=float) # x,y,width, height
        self.object_counter = 0
        self.highlight_annotation = -1
        # Note: we keep the scale and radius variables as they stay constant as moving through images

class MainWindow(QtGui.QMainWindow):
    """
    The main window of the GUI - designed using Qt Designer
    """
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        # Set up the under interface - as designed in Qt Designer
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.connectSignals()

        # Initialise parameters/variables
        self.original_size = None
        self.firstImage = True
        self.labelFolder = None
        self.imageFolder = None
        self.multiplier = None
        self.scene = None
        self.imagePanel = None
        self.image_index = None
        self.default_directory = None
        self.imagesFolder = None
        self.pixmap = None

        # Define key and mouse function names
        self.keyPressEvent = self.mainKeyPressEvent
        self.keyReleaseEvent = self.mainKeyReleaseEvent
        self.ui.treeWidget.keyPressEvent = self.treeKeyPress
        self.ui.treeWidget.mousePressEvent = self.treeMousePress

        # Redefine graphics view with new class
        self.ui.graphicsView = FitImageGraphicsView(self.ui.centralwidget)
        self.ui.graphicsView.setObjectName(QtCore.QString.fromUtf8("graphicsView"))
        self.ui.gridLayout_3.addWidget(self.ui.graphicsView, 0, 0, 1, 3)

        # Initialise status
        self.ui.statusBar.showMessage('Welcome to the future of image annotation..!')

        # Set graphics screen properties
        self.setscreenproperties()

        # Get initial graphics view size
        # self.graphicsView_size = self.ui.graphicsView.size()

        # self.ui.graphicsView.viewport().installEventFilter(self)

        # For debuging
        # self.quickview()

    def connectSignals(self):
        """ Connect all the components on the GUI to respective functions """
        # Folder/image navigation
        self.connect(self.ui.browse_btn, QtCore.SIGNAL("clicked()"), self.openImageDirectory)
        self.connect(self.ui.label_folder_btn, QtCore.SIGNAL("triggered()"), self.setLabelFolder)
        self.connect(self.ui.prev_btn, QtCore.SIGNAL("clicked()"), self.previousImage)
        self.connect(self.ui.next_btn, QtCore.SIGNAL("clicked()"), self.nextImage)
        self.connect(self.ui.imageComboBox, QtCore.SIGNAL("currentIndexChanged(QString)"), self.changeImage)
        self.connect(self.ui.save_btn, QtCore.SIGNAL("clicked()"), self.saveAnnotations)

        # Menu bar
        self.connect(self.ui.actionOpen_Folder, QtCore.SIGNAL("triggered()"), self.openImageDirectory)
        self.connect(self.ui.actionSave_Label, QtCore.SIGNAL("triggered()"), self.saveAnnotations)
        self.ui.actionSave_Label.setShortcut(QtGui.QKeySequence("Ctrl+s"))
        self.ui.actionExit_3.setStatusTip('Exit Application')
        self.ui.actionExit_3.setShortcut(QtCore.Qt.Key_Escape)
        self.connect(self.ui.actionExit_3, QtCore.SIGNAL("triggered()"), self.close)
        self.connect(self.ui.actionAbout, QtCore.SIGNAL("triggered()"), self.aboutWindow)
        self.ui.actionAbout.setShortcut(QtCore.Qt.Key_F1)
        self.connect(self.ui.actionLoad_Label, QtCore.SIGNAL("triggered()"), self.loadFromFile)
        self.ui.actionLoad_Label.setShortcut(QtGui.QKeySequence("Ctrl+l"))

        # Annotation tool
        self.connect(self.ui.opacity_slider, QtCore.SIGNAL('valueChanged(int)'), self.change_opacity)

        # Imaging properties
        self.connect(self.ui.brightness_slider, QtCore.SIGNAL('valueChanged(int)'), self.change_brightness)
        self.connect(self.ui.contrast_slider, QtCore.SIGNAL('valueChanged(int)'), self.change_contrast)

    def setscreenproperties(self):
        """
        Set scene properties - disable scrolling
        """

        self.ui.graphicsView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.ui.graphicsView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.ui.graphicsView.setFocusPolicy(QtCore.Qt.NoFocus)

    def eventFilter(self, QObject, QEvent):
        """
        Filter out wheel event from the window - we want to reserve the wheel for other commands
        """
        if QObject == self.ui.graphicsView.viewport() and QEvent.type() == QtCore.QEvent.Wheel:
            return True
        return False

    def wheelEvent(self, QWheelEvent):
        """
        The mouse wheel controls:
        - Ctrl + : Image zoom
        - Alt + : Annotation radius
        """
        # See which modifier is pressed
        modifiers = QtGui.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.AltModifier:
            # Change cursor radius
            # self.imagePanel.radius += np.sign(QWheelEvent.delta())
            self.imagePanel.dx += np.sign(QWheelEvent.delta())
            self.imagePanel.dy += np.sign(QWheelEvent.delta())
            self.imagePanel.dy = np.max((1, self.imagePanel.dy))
            self.imagePanel.dx = np.max((1, self.imagePanel.dx))
            self.imagePanel.update()
        elif modifiers == QtCore.Qt.ControlModifier:
            # Zoom in and out of the image
            if np.sign(QWheelEvent.delta()) > 0:
                self.zoomIn()
            if np.sign(QWheelEvent.delta()) < 0:
                self.zoomOut()

        # Change different dimensions of the rectangle
        if self.imagePanel.changeHeight:
            self.imagePanel.dy += np.sign(QWheelEvent.delta())
            self.imagePanel.dy = np.max((1, self.imagePanel.dy))
        elif self.imagePanel.changeWidth:
            self.imagePanel.dx += np.sign(QWheelEvent.delta())
            self.imagePanel.dx = np.max((1, self.imagePanel.dx))
            self.imagePanel.update()

    def mainKeyPressEvent(self, event):
        # Moving the image
        if event.key() == QtCore.Qt.Key_Shift:
            self.imagePanel.x, self.imagePanel.y = -1, -1
            self.update()
            self.imagePanel.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))
            self.imagePanel.MovingMode = True

        # Change annotation size
        if event.key() == QtCore.Qt.Key_BracketRight:
            # self.imagePanel.radius += 1
            self.imagePanel.dx += 1
            self.imagePanel.dy += 1
        if event.key() == QtCore.Qt.Key_BracketLeft:
            # self.imagePanel.radius -= 1
            self.imagePanel.dx -= 1
            self.imagePanel.dy -= 1

        # Change annotation size of each dimension with key modifiers
        if event.key() == QtCore.Qt.Key_Q:
            self.imagePanel.changeWidth = True
        if event.key() == QtCore.Qt.Key_A:
            self.imagePanel.changeHeight = True


        # Zoom in and out of the image
        if event.key() == QtCore.Qt.Key_Equal or event.key() == QtCore.Qt.Key_Plus:
            self.zoomIn()
        if event.key() == QtCore.Qt.Key_Minus:
            self.zoomOut()

        # Annotate current position (if for some reason clicking is too hard)
        if event.key() == QtCore.Qt.Key_Space:
            if self.imagePanel.x >= 0:
                x, y, dx, dy, s = self.imagePanel.x, self.imagePanel.y, self.imagePanel.dx, self.imagePanel.dy, \
                                  self.imagePanel.current_scale
                self.imagePanel.annotations[self.imagePanel.object_counter, ...] = x/s, y/s, dx/s, dy/s, \
                                                                                   self.imagePanel.label
                self.imagePanel.object_counter += 1
                self.imagePanel.changeMade = True
                self.updateTree()

        # Change label options
        for num in range(9)[1:]:
            if QtCore.QString(QtCore.QChar(event.key())) == str(num):
                self.imagePanel.label = num
                self.ui.item_label_txt.setText(str(num))

        # Browse images, prev <-> next
        if event.key() == QtCore.Qt.Key_Period:
            self.ui.next_btn.animateClick()
        if event.key() == QtCore.Qt.Key_Comma:
            self.ui.prev_btn.animateClick()

    def mainKeyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Shift:
            # Releasing the mouse button after dragging the image
            self.imagePanel.MovingMode = False
            self.imagePanel.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))

        # Change annotation size of each dimension with key modifiers
        if event.key() == QtCore.Qt.Key_Q:
            self.imagePanel.changeWidth = False
        if event.key() == QtCore.Qt.Key_A:
            self.imagePanel.changeHeight = False

    def zoomIn(self):
        """ Rescale pixmap to simulate a zooming in motion """
        # increment scale multiplier
        self.multiplier += 0.1

        # Evaluate new size of the pixmap
        previous_size = np.array((self.imagePanel.pixmap().width(), self.imagePanel.pixmap().height()), dtype=float)
        new_size = np.array((self.original_size[0]*self.multiplier, self.original_size[1]*self.multiplier), dtype=float)
        ratio = np.mean(new_size/previous_size)

        # Reset pixmap from its original shape (stored as self.pixmap)
        pixmap = self.pixmap.scaled(QtCore.QSize(self.original_size[0]*self.multiplier, self.original_size[1]*self.multiplier),
                                    QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.imagePanel.setPixmap(pixmap)
        self.imagePanel.defaultColorPixmap = pixmap
        self.change_brightness_contrast()

        # Save scale properties into graphics item
        self.imagePanel.current_scale = self.multiplier
        self.imagePanel.dx *= ratio
        self.imagePanel.dy *= ratio
        self.imagePanel.x = -1

    def zoomOut(self):
        """ Rescale pixmap to simulate a zooming out motion """
        # decrement scale multiplier
        self.multiplier -= 0.1

        # Evaluate new size of the pixmap
        previous_size = np.array((self.imagePanel.pixmap().width(), self.imagePanel.pixmap().height()), dtype=float)
        new_size = np.array((self.original_size[0]*self.multiplier, self.original_size[1]*self.multiplier), dtype=float)
        ratio = np.mean(new_size/previous_size)

        # Reset pixmap from its original shape (stored as self.pixmap)
        pixmap = self.pixmap.scaled(QtCore.QSize(self.original_size[0]*self.multiplier, self.original_size[1]*self.multiplier),
                                    QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.imagePanel.setPixmap(pixmap)
        self.imagePanel.defaultColorPixmap = pixmap
        self.change_brightness_contrast()

        # Save scale properties into graphics item
        self.imagePanel.current_scale = self.multiplier
        self.imagePanel.dx *= ratio
        self.imagePanel.dy *= ratio
        self.imagePanel.x = -1

    def treeMousePress(self, event):
        """ Mouse events on the tree - select annotations """

        # Check if mouse selected gives a valid item
        item = self.ui.treeWidget.indexAt(event.pos())
        if item.isValid():
            # Select if valid
            QtGui.QTreeWidget.mousePressEvent(self.ui.treeWidget, event)
            selected_item = self.ui.treeWidget.currentItem()
            selected_index = int(selected_item.text(0))-1
        else:
            # Clear previous selections if invalid
            self.ui.treeWidget.clearSelection()
            selected_index = -1

        # Feel selected index to graphics item to highlight item
        self.imagePanel.highlight_annotation = selected_index
        self.imagePanel.update()

    def treeKeyPress(self, event):
        """ Keyboard events on the tree - move through annotations or delete them """

        # Delete selected item
        if event.key() == QtCore.Qt.Key_Delete:
            selected_item = self.ui.treeWidget.currentItem()
            selected_index = int(selected_item.text(0))-1
            self.imagePanel.object_counter -= 1
            self.imagePanel.annotations = np.delete(self.imagePanel.annotations, selected_index, axis=0)
            self.updateTree()
            self.imagePanel.highlight_annotation = -1
            self.imagePanel.update()

        # Navigate through items - highlighting the current selection on the image
        if event.key() == QtCore.Qt.Key_Down:
            item = self.ui.treeWidget.currentItem()
            self.ui.treeWidget.setCurrentItem(self.ui.treeWidget.itemBelow(item))
            selected_item = self.ui.treeWidget.currentItem()
            selected_index = int(selected_item.text(0))-1
            self.imagePanel.highlight_annotation = selected_index
            self.imagePanel.update()

        if event.key() == QtCore.Qt.Key_Up:
            item = self.ui.treeWidget.currentItem()
            self.ui.treeWidget.setCurrentItem(self.ui.treeWidget.itemAbove(item))
            selected_item = self.ui.treeWidget.currentItem()
            selected_index = int(selected_item.text(0))-1
            self.imagePanel.highlight_annotation = selected_index
            self.imagePanel.highlight_annotation = selected_index
            self.imagePanel.update()

    def updateTree(self):
        """ Update the tree when a new annotation is added """
        # Clear previous values
        self.ui.treeWidget.clear()

        # Go through the Rectangles and add the data points
        for i in range(self.imagePanel.object_counter):
            column = QtGui.QTreeWidgetItem(self.ui.treeWidget)
            column.setText(0, str(i+1))
            column.setText(1, ','.join(['{0:.0f}'.format(x) for x in self.imagePanel.annotations[i, :2]]))
            column.setText(2, ','.join(['{0:.0f}'.format(x) for x in self.imagePanel.annotations[i, 2:4]]))
            column.setText(3, str(self.imagePanel.annotations[i, 4]))

    def change_opacity(self, value):
        """ From the slider, change the opacity of the current annotations """
        self.ui.opacityBox.setTitle('Label Opacity: {}'.format(value))
        self.imagePanel.opacity = value
        self.imagePanel.setBrushes()
        self.imagePanel.update()

    def change_brightness_contrast(self):
        """ Grab slider values and change brightness and contrast of the image """
        # Get current contrast and brightness
        b_value = self.ui.brightness_slider.value()
        c_value = self.ui.contrast_slider.value()

        # Apply transformation
        pixmap = adjustPixmap(self.imagePanel.defaultColorPixmap, brightness=b_value, contrast=c_value)
        self.imagePanel.setPixmap(pixmap)

    def change_brightness(self, value):
        """ From the slider, change the brightness of the current image """
        self.ui.brightness_box.setTitle('Brightness: {}'.format(value))
        self.change_brightness_contrast()

    def change_contrast(self, value):
        """ From the slider, change the contrast of the current image """
        self.ui.contrast_box.setTitle('Contrast: {}'.format(value))
        self.change_brightness_contrast()

    def initImage(self, pixmap):
        """ Load the first image onto graphics view - initialise graphics item """

        # Save original image size
        self.original_size = pixmap.width(), pixmap.height()
        self.multiplier = float(1)
        self.firstImage = False

        # Set scene and add to graphics view
        self.scene = QtGui.QGraphicsScene()
        self.imagePanel = RectangleDrawPanel(scene=self.scene, parent=self)
        self.imagePanel.setPixmap(self.pixmap)
        self.imagePanel.defaultColorPixmap = self.pixmap
        self.change_brightness_contrast()
        self.scene.addItem(self.imagePanel)
        # self.ui.graphicsView.resize(self.graphicsView_size)
        self.ui.graphicsView.setScene(self.scene)
        # print self.ui.graphicsView.size().width(), self.ui.graphicsView.size().height()
        # print self.scene.itemsBoundingRect()
        self.ui.graphicsView.setSceneRect(0, 0,
                                          self.ui.graphicsView.size().width()-10,
                                          self.ui.graphicsView.size().height()-10)
        # self.ui.graphicsView.setSceneRect(self.scene.itemsBoundingRect())

    def loadImage(self,image_path):
        """ Given an image path, load image onto graphics item """

        # Get current pixmap
        self.pixmap = QtGui.QPixmap(image_path)
        pixmap = self.pixmap
        if self.original_size is not None:
            assert pixmap.width() == self.original_size[0] and \
                   pixmap.height() == self.original_size[1], \
                "Images in the folder need to be of the same size"

        # Resize according to previous shape/size
        if self.original_size is not None:
            pixmap = pixmap.scaled(QtCore.QSize(self.original_size[0]*self.multiplier, self.original_size[1]*self.multiplier),
                                   QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)

        # If its the first time, initialise graphics item
        if self.firstImage:
            self.initImage(pixmap)
        else:
            # Otherwise update previously set graphics item
            self.imagePanel.setPixmap(pixmap)
            self.imagePanel.defaultColorPixmap = pixmap
            self.change_brightness_contrast()
            self.imagePanel.resetAnnotations()
            self.updateTree()

        # Reset change status - To allow for auto saving of images without any fruits
        self.imagePanel.changeMade = True

        # Load annotation if on already exists (and if autoload is ticked)
        if self.ui.autoload_chk.isChecked():
            self.loadAnnotations()

    def previousImage(self):
        """ Navigate to previous image in the folder """
        # Save annotations if needed
        if self.ui.autosave_chk.isChecked() and self.imagePanel.changeMade:
            self.saveAnnotations()

        # Change entry in combobox
        index = self.ui.imageComboBox.currentIndex() - 1
        if index < 0:
            index = 0
        self.ui.imageComboBox.setCurrentIndex(index)

    def nextImage(self):
        """ Navigate to next image in the folder """
        # Save annotations if needed
        if self.ui.autosave_chk.isChecked() and self.imagePanel.changeMade:
            self.saveAnnotations()

        # Change entry in combobox
        index = self.ui.imageComboBox.currentIndex() + 1
        if index < 0:
            index = 0
        self.ui.imageComboBox.setCurrentIndex(index)

    def changeImage(self, text):
        """ Call load image and set new image as title, combo box entry and image # """
        self.loadImage("%s/%s" % (self.imagesFolder, text))
        self.setWindowTitle("%s - Pychet Annotator" % (self.ui.imageComboBox.currentText()))
        self.image_index = self.ui.imageComboBox.currentIndex()
        self.ui.image_index_label.setText('{:.0f}/{:.0f}'.format(self.image_index+1, self.ui.imageComboBox.count()))

    def openImageDirectory(self, imagesFolder=None):
        """ Open browser containing the set of images to be labelled """

        if imagesFolder is None:
            # Specify default folder for quick access
            self.default_directory = "/media/suchet/d-drive/data/processed/2013-03-20-melbourne-apple-farm/shrimp/Run4-5/ladybug/appleBinaryCombined"
            self.default_directory = "/media/suchet/d-drive/Dropbox/ACFR PhD/Experimental-Results/mango-labelling-2016/"

            # Get output from browser
            self.imagesFolder = str(QtGui.QFileDialog.getExistingDirectory(self, "Open directory", self.default_directory))
        else:
            self.imagesFolder = imagesFolder

        # Grab images and set up combobox
        allFiles = os.listdir(self.imagesFolder)
        extensions = ['.png', '.jpg']
        imageFiles = sorted([x for x in allFiles if os.path.splitext(x)[-1] in extensions])
        self.ui.imageComboBox.clear()
        self.ui.imageComboBox.addItems(imageFiles)

        # Reset window title to current image
        self.setWindowTitle("%s - Pychet Annotator" % (self.ui.imageComboBox.currentText()))

    def setLabelFolder(self):
        """ Pick folder to save annotations into """
        self.labelFolder = str(QtGui.QFileDialog.getExistingDirectory(self, "Open directory", self.default_directory))

    def saveAnnotations(self):
        """
        Save annotations as .csv files
        Entries contains item cx, cy, width, height, label
        By default, save to same level as images, into folder named labels-rectangles
        """

        # Get the current image file name
        filename = os.path.splitext(str(self.ui.imageComboBox.currentText()))[0]
        if self.labelFolder is None:
            self.labelFolder = os.path.join(self.imagesFolder, '../labels-rectangles/')

        # Create label folder
        if not os.path.exists(self.labelFolder):
            self.ui.statusBar.showMessage('Created a Label Directory')
            os.makedirs(self.labelFolder)

        # Establish save file
        save_file = os.path.join(self.labelFolder, filename+'.csv')

        # If save file already exists, Ask user if they want to overwrite
        if os.path.exists(save_file):
            overwrite_msg = 'Label file already exists for {}, overwrite?'.format(filename)
            reply = QtGui.QMessageBox.question(self, 'File already exists', overwrite_msg, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.Yes:
                self.ui.statusBar.showMessage('Overwriting previous label')
            else:
                # If they say no - don't save
                return 0

        # Annotation header and data
        header = ['item','x','y','dx','dy','label']
        data = self.imagePanel.annotations[:self.imagePanel.object_counter, :]

        # If there is data, add item numbers for the first column
        if data.size > 0:
            data = np.hstack((np.arange(data.shape[0])[:,None], data))

        # Saving format
        fmt = '%.0f,%3.2f,%3.2f,%3.2f,%3.2f,%.0f'

        # Diplay saving status and save to file (headeer first)
        self.ui.statusBar.showMessage('Saved to {}'.format(filename))
        with open(save_file, 'wb') as f:
            f.write(bytes('# '+','.join(header)+'\n'))

        # If data if it exists
        if data.size > 0:
            np.savetxt(save_file, data, delimiter=',', fmt=fmt, header=','.join(header))

    def loadFromFile(self, filename=None):
        """
        Given a file name, load the .csv file and the associated annotations
        """

        # If its an empty call, prompt open file
        if filename is None:
            filters = "Text files (*.csv);;All (*)"
            f = QtGui.QFileDialog.getOpenFileNameAndFilter(self, "Open Label File", '.', filters)
            filename = str(f[0])

        # Open file
        with open(filename, 'r') as f:
            # Skip header
            next(f)

            # Read csv data
            reader = csv.reader(f)
            data = np.array(list(reader)).astype(float)

        # If there is some data, add to image annotations
        if data.size>0:
            self.imagePanel.setAnnotations(data[:,1:])

        # Update annotation list
        self.updateTree()

    def aboutWindow(self):
        """ Display information about the software """

        message = 'About the Rectangle Annotator:\t\t\n\n'
        message += 'Rectangle annotation tool.\n'
        message += 'Pick image directory (containing .jpg or .png files) and start labelling! Labels saved as .csv in the same parent folder as the images, under folder labels-rectangles. '
        message += 'The Labels are stored in format item, x, y, width, height, label #.\nIf Auto save is selected, ' \
                   'the annotations will be saved upon clicking next/previous image (or by ctrl + s). '
        message += 'If Auto Load is selected, when an image loads, so will its annotations in the labels folder if they exist.\n'
        message += 'To delete an annotation, select is from the annotation list and press delete.\n\n'
        message += 'Controls:\n\n'
        message += 'Zoom in/out: \t-/+ or Ctrl + Wheel Button\n'
        message += 'Move Image: \tShift + Wheel Button\n'
        message += 'Rectangle Size: \t\Alt + Wheel Button:\n'
        message += 'Rectangle width, height: \tQ,A + Wheel Button:\n'
        message += 'Label ID: \t\t[1-9]\n'
        message += 'Annotate: \t\tSpace or Left Click\n'
        message += 'Previous/Next Image: \t</>\n'
        message += 'Save Annotation: \tCtrl + s\n'
        message += 'Exit application: \tESC\n'
        QtGui.QMessageBox.information(self, 'About Pychet Rectangle Annotator', message)

    def loadAnnotations(self):
        """
        Look for annotation file in label folder and load data
        """

        # Get current file name
        filename = os.path.splitext(str(self.ui.imageComboBox.currentText()))[0]
        if self.labelFolder is None:
            self.labelFolder = os.path.join(self.imagesFolder, '../labels-rectangles/')

        # Get load file name
        loadfile = os.path.join(self.labelFolder, filename+'.csv')
        if os.path.exists(loadfile):
            self.ui.statusBar.showMessage('Loading previous label from {}.csv'.format(filename))
        else:
            self.ui.statusBar.showMessage('No label file exists')
            return 0

        # Load data
        self.loadFromFile(filename=loadfile)

        # If labels are loaded then toggle changeMade to False
        self.imagePanel.changeMade = False

    def quickview(self):
        """
        Show an image without selecting any folder - debug mode
        """

        # Manually set image to load
        folder_path = '/media/suchet/d-drive/data/processed/2013-03-20-melbourne-apple-farm/shrimp/Run4-5/ladybug/appleBinaryCombined/images/'
        image_path = os.path.join(folder_path , '20130320T013717.962834_44.png')
        folder_path = '/media/suchet/d-drive/Dropbox/ACFR PhD/Experimental-Results/mango-labelling-2016/circle-labels/images'
        image_path = os.path.join(folder_path , '20151124T025455.360524.png')

        # Load image and set original size
        self.pixmap = QtGui.QPixmap(image_path)
        self.original_size = self.pixmap.width(), self.pixmap.height()
        self.multiplier = float(1)
        print self.original_size

        # Set graphics scene and add image
        self.scene = QtGui.QGraphicsScene()
        self.imagePanel = RectangleDrawPanel(scene=self.scene, parent=self)
        self.imagePanel.setPixmap(self.pixmap)
        self.imagePanel.defaultColorPixmap = self.pixmap
        self.change_brightness_contrast()
        self.scene.addItem(self.imagePanel)
        # print self.ui.graphicsView.size().width(), self.ui.graphicsView.size().height()
        self.ui.graphicsView.setScene(self.scene)
        # print self.ui.graphicsView.size().width(), self.ui.graphicsView.size().height()
        # print self.scene.itemsBoundingRect()
        self.ui.graphicsView.setSceneRect(self.scene.itemsBoundingRect())


class FitImageGraphicsView(QtGui.QGraphicsView):
    """
    Resize function for window to properly fit an image.
    """

    def showEvent(self, QShowEvent):
        self.fitInView(self.sceneRect(), QtCore.Qt.KeepAspectRatio)



def convertQImageToMat(incomingImage):
    '''  Converts a QImage into an opencv MAT format  '''

    incomingImage = incomingImage.convertToFormat(4)

    width = incomingImage.width()
    height = incomingImage.height()

    ptr = incomingImage.bits()
    ptr.setsize(incomingImage.byteCount())
    arr = np.array(ptr).reshape(height, width, 4)  #  Copies the data
    return arr

def convertMattoQImage(im, copy=False):
    if im is None:
        return QtGui.QImage()

    gray_color_table = [QtGui.qRgb(i, i, i) for i in range(256)]

    if im.dtype == np.uint8:
        if len(im.shape) == 2:
            qim = QtGui.QImage(im.data, im.shape[1], im.shape[0], im.strides[0], QtGui.QImage.Format_Indexed8)
            qim.setColorTable(gray_color_table)
            return qim.copy() if copy else qim

        elif len(im.shape) == 3:
            if im.shape[2] == 3:
                qim = QtGui.QImage(im.data, im.shape[1], im.shape[0], im.strides[0], QtGui.QImage.Format_RGB888);
                return qim.copy() if copy else qim
            elif im.shape[2] == 4:
                qim = QtGui.QImage(im.data, im.shape[1], im.shape[0], im.strides[0], QtGui.QImage.Format_ARGB32);
                return qim.copy() if copy else qim

    raise NotImplementedError

def adjustPixmap(pixmap, brightness=0, contrast=0):
    """ Adjust the brightness and contrast of a QPixmap """

    # Convert to QImage
    im = pixmap.toImage()

    # Convert to numpy array and adjust
    imcv = np.clip(convertQImageToMat(im)*(1+contrast/100.), 0, 255)
    imcv = np.clip(imcv+brightness, 0, 255)

    # Convert back to pixmap
    im = convertMattoQImage(imcv.astype('uint8'))
    pixmap = QtGui.QPixmap.fromImage(im)

    return pixmap


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    main = MainWindow()
    main.show()

    if len(sys.argv) == 2:
        main.openImageDirectory()

    sys.exit(app.exec_())

