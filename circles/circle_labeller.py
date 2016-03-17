#! /usr/bin/python
"""
Image annotation tool.
Annotate using circular shapes
"""
__author__ = 'suchet'
__date__ = '28/10/15'

import sys, os, csv
import numpy as np
import svgwrite
from PyQt4 import QtGui, QtCore
from pychetlabeller.circles.circle_labeller_ui import Ui_MainWindow
from shapely.geometry import Point, Polygon

my_colormap = [\
[137, 0, 255], 
[255, 0, 0], 
[179, 179, 0], 
[0, 255, 151], 
[0, 193, 255], 
[0, 27, 255], 
[137, 0, 255], 
[255, 165, 0], 
[255, 0, 41], 
[13, 255, 0], 
[255, 0, 207]]
label_dataset = None

class LabelDataset(object):
    '''shape-label dataset class'''
    def __init__(self, image_path, image_size):
        self.data = []
        self.image_size = image_size
        self.image_path = image_path
        self.label_path = None
    def add(self, datum):
        ''' add a LabelShape to the dataset'''
        assert isinstance(datum, LabelShape)
        self.data.append(datum)
    def remove(self, datum):
        '''remove a LabelShape to the dataset'''
        assert isinstance(datum, LabelShape)
        self.data.remove(datum)
    def save(self, label_basename):
        '''Save the dataset'''
        self.saveSVG(label_basename + '.svg')
        self.saveCSV(label_basename + '.csv')
    def saveSVG(self, output_filename):
        """Save the shapes in SVG format"""
        dwg = svgwrite.Drawing(output_filename
            , profile='tiny', size=self.image_size)
        for datum in self.data:
            dwg.add(datum.svg_shape())
        dwg.save()
    def saveCSV(self, output_filename
        , field_delimiter=',', line_delimiter='\n'):
        """Save the shapes as CSV"""
        with open(output_filename, 'w') as f:
            for datum in self.data:
                serialized = [str(i) for i in datum.serialize()]
                f.write(field_delimiter.join(serialized) + line_delimiter)
    def load(self, label_path):
        '''try load the default path, or given label_path'''
        self.label_path = label_path
        try:
            label_file = open(self.label_path, 'r')
        except IOError:
            return False # Couldn't find file
        for line in csv.reader(label_file):
            try:
                is_circle = True #TODO: complete stub
                if is_circle:
                    self.add(LabelCircle(int(line[4])
                        , float(line[1]), float(line[2]), float(line[3])))
            except ValueError:
                # Things that don't convert will be skipped
                print "WARNING: Skipped a line (ValueError)"
        label_file.close()
    def find(self, labelshape_id):
        '''find a LabelShape given by ID'''
        results = [datum for datum in self.data if datum.id == labelshape_id]
        if len(results):
            return results[0]
        return None
    def data_at(self, position):
        '''return all the data that lie at a point'''
        point = Point(position[0], position[1])
        results = [datum for datum in self.data if point.within(datum.shape)]
        return results

class Tool(object):
    def __init__(self):
        label = None
        pass
    def click(self, x, y, button):
        pass
    def wheel(self, delta):
        pass
    def set_label(self, label):
        self.label = label

class Tool_Circle(Tool):
    defaults = {
        'radius': 10,
        'radius_scroll_delta': 1
    }
    def __init__(self):
        self.radius = Tool_Circle.defaults['radius']
    def click(self, x, y, button):
        if button == 'l':
            return LabelCircle(self.label, x, y, radius)
        return None
    def wheel(self, delta):
        self.radius += delta * defaults['radius_scroll_delta']

class Tool_Polygon(Tool):
    defaults = {}
    def __init__(self):
        self.points = []
    def click(self, x, y, button):
        if button == 'l':
            self.points.append((x, y))
            #TODO: Update view
        elif button == 'r' and len(self.points) > 3:
            return Polygon(self.points)
            #TODO: Possible yield

class LabelShape(object):
    instances = 0
    def __init__(self, label, shape):
        self.label = label
        self.shape = shape
        self.id = LabelShape.instances
        LabelShape.instances += 1
    def populate_view(self, view, **kwargs):
        pass
    def __hash__(self):
        return self.id
    def __cmp__(self, other):
        if self.id > other.id:
            return 1
        elif self.id < other.id:
            return -1
        return 0
    def serialize(self):
        raise Exception("serialize UNIMPLEMENTED for this type")

class LabelCircle(LabelShape):
    enum = 1
    def __init__(self, label, x, y, radius):
        circle = Point(x,y).buffer(radius)
        circle.x, circle.y, circle.radius = x, y, radius
        super(LabelCircle, self).__init__(label, circle)
    def populate_view(self, view, **kwargs):
        if isinstance(view, QtGui.QTreeWidgetItem):
            view.setText(0, str(self.id))
            view.setText(1, "%d, %d" % (self.shape.x, self.shape.y))
            view.setText(2, str(self.shape.radius))
            view.setText(3, str(self.label))
        elif isinstance(view, QtGui.QPainter):
            scale = kwargs['scale']
            x, y = tuple((i - self.shape.radius) * scale \
                for i in (self.shape.x, self.shape.y))
            side_width = 2*self.shape.radius * scale
            view.drawEllipse(x, y, side_width, side_width)
    def serialize(self):
        return (LabelCircle.enum, self.shape.x, self.shape.y
                , self.shape.radius, self.label)
    def svg_shape(self):
        '''return the SVG shape that this object represents'''
        r, g, b = my_colormap[self.label]
        return svgwrite.shapes.Circle(center=(self.shape.x, self.shape.y)
            , r=self.shape.radius, stroke=svgwrite.rgb(r, g, b, 'RGB')
            , fill=svgwrite.rgb(r, g, b, 'RGB'))

class SelectDropType(QtGui.QDialog):
    def __init__(self, parent=None):
        super(SelectDropType, self).__init__(parent)

        msgBox = QtGui.QMessageBox()
        msgBox.setText('Which folder is this?')
        msgBox.addButton(QtGui.QPushButton('Cancel'), QtGui.QMessageBox.RejectRole)
        msgBox.addButton(QtGui.QPushButton('Labels'), QtGui.QMessageBox.NoRole)
        msgBox.addButton(QtGui.QPushButton('Images'), QtGui.QMessageBox.YesRole)

        self.selection = msgBox.exec_()

class CircleDrawPanel(QtGui.QGraphicsPixmapItem):
    """Establish a pixmap item on which labelling (painting) will be performed"""
    def __init__(self, pixmap=None, parent=None, scene=None):
        super(CircleDrawPanel, self).__init__()
        # Initialise variables
        # Class variables
        self.MAX_DATA_POINTS = 1000
        self.x, self.y = -1, -1 # Location of cursor
        self.parent = parent # Parent class - ui mainwindow
        self.current_scale = 1.
        self.defaultColorPixmap = None
        # Annotation parameters
        self.radius = 10.0
        self.opacity = 60 # Opacity of annotation
        self.highlight_opacity = 100
        self.label = 1 # Label of circle
        # Annotation results
        self.changeMade = None
        # Annotation drawing
        self.pen = QtGui.QPen(QtCore.Qt.SolidLine)
        self.pen.setColor(QtCore.Qt.black)
        self.pen.setWidth(1)
        self.num_labels = 9
        self.setBrushes()
        self.highlight_centroid = None # Index of highlighted annotation
        # Set up options
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable, True)
        self.setAcceptHoverEvents(True)
        self.MovingMode = False # Check if image is being moved
    def setBrushes(self):
        """Set the brushes for normal view, annotated view, highlighted view"""
        self.testbursh =  QtGui.QBrush(QtGui.QColor(255, 255, 0, self.opacity))
        self.savebrush = QtGui.QBrush(QtGui.QColor(255, 0, 0, self.opacity))
        self.savebrushes = [QtGui.QBrush(QtGui.QColor(my_colormap[label_no][0],
                                                      my_colormap[label_no][1],
                                                      my_colormap[label_no][2],
                                                      self.opacity)) for label_no in range(10)]
        self.highlightbrush = QtGui.QBrush(QtGui.QColor(0, 0, 255, self.opacity))
        self.highlightbrushes = [QtGui.QBrush(QtGui.QColor(my_colormap[label_no][0],
                                                           my_colormap[label_no][1],
                                                           my_colormap[label_no][2],
                                                           self.highlight_opacity)) for label_no in range(10)]
    def paint(self, QPainter, QStyleOptionGraphicsItem, QWidget):
        """Painter to draw annotations"""
        # Set image and pen
        QPainter.drawPixmap(0, 0, self.pixmap())
        QPainter.setPen(self.pen)
        # Draw a circle at the current position of the mouse
        if self.x >= 0 and self.y >= 0:
            QPainter.setBrush(self.testbursh)
            QPainter.drawEllipse(
                self.x-self.radius, self.y-self.radius
                , 2*self.radius, 2*self.radius)
        # Draw the annotated shapes
        for datum in label_dataset.data:
            if datum.id == -1: #TODO: highlighted
                QPainter.setBrush(self.highlightbrushes[datum.label])
            else:
                QPainter.setBrush(self.savebrushes[datum.label])
            datum.populate_view(QPainter, scale=self.current_scale)

    def hoverEnterEvent(self, event): #QGraphicsSceneHoverEvent
        '''Set events for mouse hovers.
        As the mouse enters the image, change to cross cursor,
        and as it leaves the image, change to arrow cursor'''
        self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
    def hoverMoveEvent(self, event): #QGraphicsSceneHoverEvent
        '''While moving inside the picture, update x,y position for drawing annotation tool
        If instead in moving mode (grab and move image), do nothing.'''
        if not self.MovingMode:
            self.x = event.pos().x()
            self.y = event.pos().y()
            self.update()
    def hoverLeaveEvent(self, event): #QGraphicsSceneHoverEvent
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        # Reset position to stop drawing annotation circle outside the image
        self.x, self.y = -1, -1
        self.update()
    def mousePressEvent(self, event): # QGraphicsSceneMouseEvent
        """Record the annotation when mouse is clicked.
        If Image is in moving mode, prepare to move image"""
        if self.MovingMode is False:
            self.setFlag(QtGui.QGraphicsItem.ItemIsMovable, False)
            point = (self.x/self.current_scale, self.y/self.current_scale)
            if event.button() == 1:
                radius = self.radius/self.current_scale
                self.add(point, radius, self.label)
                self.setFocus()
                # Add centroids to the parent tree widget
                # self.parent.populateTree()
            elif event.button() == 2: # make selection if right clicked pressed
                datum = sorted(label_dataset.data_at(point))
                if not datum:
                    return
                item = self.parent.ui.treeWidget.findItems(
                    str(datum[0].id), QtCore.Qt.MatchExactly, 0)[0]
                self.parent.ui.treeWidget.setCurrentItem(item)
                self.update()
                self.parent.ui.treeWidget.setFocus()
        else:
            self.setFlag(QtGui.QGraphicsItem.ItemIsMovable, True)
            self.setCursor(QtGui.QCursor(QtCore.Qt.ClosedHandCursor))
    def mouseReleaseEvent(self, event): # QGraphicsSceneMouseEvent
        """If image was in moving more, change cursor grab icon"""
        if self.MovingMode is True:
            self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))

        QtGui.QGraphicsPixmapItem.mouseReleaseEvent(self, event)
    def add(self, point, radius, label, tool='circle'):
        if tool == 'circle':
            shape = LabelCircle(label, point[0], point[1], radius)
        elif tool == 'polygon':
            pass # TODO
        label_dataset.add(shape)
        shape.populate_view(QtGui.QTreeWidgetItem(self.parent.ui.treeWidget))
        self.changeMade = True


class MainWindow(QtGui.QMainWindow):
    """
    The main window of the GUI - designed using Qt Designer
    """
    def __init__(self):
        self.scroll_zoom_delta = 0.1
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
        self.images = None
        self.default_directory = None
        self.folder_image = None
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

        # self.ui.graphicsView.viewport().installEventFilter(self)

        # For debuging
        # self.quickview()

    def connectSignals(self):
        """ Connect all the components on the GUI to respective functions """

        # Folder/image navigation
        self.connect(self.ui.browse_btn, QtCore.SIGNAL("clicked()"), self.openImageDirectory)
        self.connect(self.ui.label_folder_btn, QtCore.SIGNAL("clicked()"), self.setLabelDirectory)
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

        # Drag and drop data
        self.setAcceptDrops(True)

    def dragEnterEvent(self, QDragEnterEvent):
        """
        Dragging in folders
        """
        if QDragEnterEvent.mimeData().hasUrls:
            QDragEnterEvent.accept()
        else:
            QDragEnterEvent.ignore()

    def dropEvent(self, QDropEvent):
        """
        Drop a folder and ask user to select if image folder or label folder
        """
        if QDropEvent.mimeData().hasUrls:

            QDropEvent.setDropAction(QtCore.Qt.CopyAction)
            QDropEvent.accept()

            promptuser = SelectDropType()
            promptuser.show()

            if promptuser.selection == 1:
                urls = QDropEvent.mimeData().urls()
                assert len(urls) == 1
                self.labelFolder = str(urls[0].toString()[7:])
            if promptuser.selection == 2:
                urls = QDropEvent.mimeData().urls()
                assert len(urls) == 1
                imageFolder = str(urls[0].toString()[7:])
                self.openImageDirectory(folder_image=imageFolder)
        else:
            QDropEvent.ignore()

    def setscreenproperties(self):
        """
        Set scene properties - disable scrolling
        """
        self.ui.graphicsView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.ui.graphicsView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        # self.ui.graphicsView.setFocusPolicy(QtCore.Qt.NoFocus)

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
        if modifiers == QtCore.Qt.ControlModifier:
            # Zoom in and out of the image
            if np.sign(QWheelEvent.delta()) > 0:
                self.zoom(self.scroll_zoom_delta)
            if np.sign(QWheelEvent.delta()) < 0:
                self.zoom(-self.scroll_zoom_delta)
        else:
            # Change cursor radius
            self.imagePanel.radius += np.sign(QWheelEvent.delta())
            self.imagePanel.update()

    def mainKeyPressEvent(self, event):
        # Moving the image
        key = event.key()
        if key == QtCore.Qt.Key_Shift:
            self.imagePanel.x, self.imagePanel.y = -1, -1
            self.update()
            self.imagePanel.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))
            self.imagePanel.MovingMode = True
        elif key == QtCore.Qt.Key_BracketRight:
            # Change annotation size
            self.imagePanel.radius += 1
        elif key == QtCore.Qt.Key_BracketLeft:
            self.imagePanel.radius -= 1
        elif key == QtCore.Qt.Key_Equal or key == QtCore.Qt.Key_Plus:
            # Zoom in and out of the image
            self.zoomIn()
        elif key == QtCore.Qt.Key_Minus:
            self.zoomOut()
        elif key == QtCore.Qt.Key_Space:
            # Annotate current position (if for some reason clicking is too hard)
            if self.imagePanel.x >= 0:
                point = (self.imagePanel.x/self.imagePanel.current_scale, self.imagePanel.y/self.imagePanel.current_scale)
                radius = self.imagePanel.radius/self.imagePanel.current_scale
                self.add(point, radius, self.imagePanel.label)
                # self.populateTree()
        elif key == QtCore.Qt.Key_Period:
        # Browse images, prev <-> next
            self.ui.next_btn.animateClick()
        elif key == QtCore.Qt.Key_Comma:
            self.ui.prev_btn.animateClick()
        elif key == QtCore.Qt.Key_Backspace and len(label_dataset.data):
            shape = label_dataset.data[-1]
            label_dataset.remove(shape)
            # self.populateTree()
            self.update()
        else:
            # Change label options
            for num in range(1, 9):
                if QtCore.QString(QtCore.QChar(key)) == str(num):
                    self.imagePanel.label = num
                    self.ui.item_label_txt.setText(str(num))

    def mainKeyReleaseEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Shift:
            # Releasing the mouse button after dragging the image
            self.imagePanel.MovingMode = False
            self.imagePanel.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))

    def zoom(self, delta):
        """ Rescale pixmap to simulate a zooming motion by delta percent"""
        # increment scale multiplier
        self.multiplier += delta

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
        self.imagePanel.radius *= ratio
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
        self.imagePanel.highlight_centroid = selected_index
        self.imagePanel.update()

    def treeKeyPress(self, event):
        """ Keyboard events on the tree - move through annotations or delete them """
        selected_item = self.ui.treeWidget.currentItem()
        if selected_item is None:
            return
        key = event.key()
        datum = label_dataset.find(int(selected_item.text(0)))
        do_update = True
        if key == QtCore.Qt.Key_Delete and datum is not None:
            label_dataset.remove(datum)
            next_item = self.ui.treeWidget.itemAbove(selected_item)
            if next_item:
                self.ui.treeWidget.setCurrentItem(next_item)
                self.imagePanel.highlight_centroid = int(next_item.text(0)) - 1
            else:
                self.imagePanel.highlight_centroid = None
            self.ui.treeWidget.takeTopLevelItem(self.ui.treeWidget.indexOfTopLevelItem(selected_item))
        elif key in [QtCore.Qt.Key_Down, QtCore.Qt.Key_Up]:
            # Navigate through items - highlighting the current selection on the image
            if key == QtCore.Qt.Key_Up:
                next_item = self.ui.treeWidget.itemAbove(selected_item)
            else:
                next_item = self.ui.treeWidget.itemBelow(selected_item)
            if next_item:
                self.ui.treeWidget.setCurrentItem(next_item)
                self.imagePanel.highlight_centroid = int(next_item.text(0)) - 1
        else:
            do_update = False
        if do_update:
            # self.populateTree()
            self.update()
            self.imagePanel.update()
            self.ui.treeWidget.update()
    def populateTree(self):
        """ Update the tree when a new annotation is added """
        self.ui.treeWidget.clear()
        for datum in label_dataset.data:
            datum.populate_view(QtGui.QTreeWidgetItem(self.ui.treeWidget))            
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
        self.imagePanel = CircleDrawPanel(scene=self.scene, parent=self)
        self.imagePanel.setPixmap(self.pixmap)
        self.imagePanel.defaultColorPixmap = self.pixmap
        self.change_brightness_contrast()
        self.scene.addItem(self.imagePanel)
        self.ui.graphicsView.setScene(self.scene)
        self.ui.graphicsView.setSceneRect(0, 0,
            self.ui.graphicsView.size().width()-10,
            self.ui.graphicsView.size().height()-10)
    def loadImage(self, image_path):
        """ Given an image path, load image onto graphics item """
        global label_dataset
        # Get current pixmap
        self.pixmap = QtGui.QPixmap(image_path)
        pixmap = self.pixmap
        label_dataset = LabelDataset(image_path, image_size=(pixmap.height(), pixmap.width()))
        if self.original_size is not None:
            assert pixmap.width() == self.original_size[0] and \
                   pixmap.height() == self.original_size[1], \
                "Images in the folder need to be of the same size"

        # Resize according to previous shape/size
        if self.original_size is not None:
            pixmap = pixmap.scaled(QtCore.QSize(self.original_size[0]*self.multiplier, self.original_size[1]*self.multiplier),
                                   QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)

        # If its the first time, initialise graphics item
        #@TODO: Edit this to allow multiple-sized images @prority:low
        if self.firstImage:
            self.initImage(pixmap)
        # Otherwise update previously set graphics item
        self.imagePanel.setPixmap(pixmap)
        self.imagePanel.defaultColorPixmap = pixmap
        self.change_brightness_contrast()
        # Reset change status - To allow for auto saving of images without any fruits
        self.imagePanel.changeMade = True
        # Load annotation if on already exists (and if autoload is ticked)
        #@TODO: First image does not auto-load annotations because UI is not init'd yet @priority: low
        if self.ui.autoload_chk.isChecked():
            self.loadAnnotations()

    def previousImage(self):
        """ Navigate to previous image in the folder """
        self.nextImage(delta=-1)

    def nextImage(self, delta=1):
        """ Navigate to next image in the folder """
        # Save annotations if needed
        if self.ui.autosave_chk.isChecked() and self.imagePanel.changeMade:
            self.saveAnnotations()

        # Change entry in combobox
        index = self.ui.imageComboBox.currentIndex() + delta
        if index < 0:
            index = 0
        self.ui.imageComboBox.setCurrentIndex(index)

    def changeImage(self, text):
        """ Call load image and set new image as title, combo box entry and image # """
        self.loadImage("%s/%s" % (self.folder_image, text))
        self.setWindowTitle("%s - Pychet Circle Annotator" % (self.ui.imageComboBox.currentText()))
        self.image_index = self.ui.imageComboBox.currentIndex()
        self.ui.image_index_label.setText('{:.0f}/{:.0f}'.format(self.image_index+1, self.ui.imageComboBox.count()))

    def openImageDirectory(self, folder_image=None):
        """ Open browser containing the set of images to be labelled """
        self.folder_image = folder_image or \
            str(QtGui.QFileDialog.getExistingDirectory(
                self, "Open directory", opendirectory))
        # Grab images and set up combobox
        self.images = sorted([x for x in os.listdir(self.folder_image) \
            if os.path.splitext(x)[-1].lower() \
            in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']])
        self.ui.imageComboBox.clear()
        self.ui.imageComboBox.addItems(self.images)
        # Reset window title to current image
        self.setWindowTitle("%s - Pychet Annotator" % (self.ui.imageComboBox.currentText()))

    def setLabelDirectory(self, dir_path=None):
        """ Pick folder to save annotations into """
        if dir_path:
            self.labelFolder = dir_path
        else:
            opendirectory = self.folder_image or '.'
            self.labelFolder = str(QtGui.QFileDialog.getExistingDirectory(self, "Open directory", opendirectory))
    def saveAnnotations(self):
        """Save annotations"""
        # Get the current image file name
        current_filename = os.path.splitext(str(self.ui.imageComboBox.currentText()))[0]
        if self.labelFolder is None:
            self.labelFolder = os.path.join(self.folder_image, '../labels-circles/')
        # Create label folder
        if not os.path.exists(self.labelFolder):
            self.ui.statusBar.showMessage('Created a Label Directory')
            os.makedirs(self.labelFolder)
        # Establish save file
        save_files = (os.path.join(self.labelFolder, current_filename + '.csv')
                    , os.path.join(self.labelFolder, current_filename + '.svg'))
        # If save file already exists, Ask user if they want to overwrite
        if any(map(os.path.exists, save_files)):
            overwrite_msg = 'Label file already exists for {}, overwrite?'.format(current_filename)
            reply = QtGui.QMessageBox.question(self, 'File already exists', overwrite_msg, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.Yes:
                self.ui.statusBar.showMessage('Overwriting previous label')
            else:
                return 0
        self.ui.statusBar.showMessage('Saved to {}'.format(current_filename))
        label_dataset.save(os.path.join(self.labelFolder, current_filename))

    def loadFromFile(self, filename=None):
        """load image and associated label data"""
        if filename is None: # If its an empty call, prompt open file
            filters = "Text files (*.csv);;All (*)"
            f = QtGui.QFileDialog.getOpenFileNameAndFilter(
                self, "Open Label File", '.', filters)
            filename = str(f[0])
        #TODO: SVG loading
        label_dataset.load(filename)
        self.populateTree()

    def aboutWindow(self):
        """ Display information about the software """
        message = """About the Circle Annotator:
Circle annotation tool.
Pick image directory (containing .jpg or .png files) and start labelling! Labels saved as .csv in the same parent folder as the images, under folder labels-circles
The Labels are stored in format item, c-x, c-y, radius, label #.
If Auto save is selected, the annotations will be saved upon clicking next/previous image (or by ctrl + s)
If Auto Load is selected, when an image loads, so will its annotations in the labels folder if they exist.
To delete an annotation, select it with a right click of from the annotation list and press delete.

Controls:
Zoom in/out: \t-/+ or Ctrl + Wheel Button
Move Image: \tShift + Wheel Button
Circle Radius: \tAlt + Wheel Button:
Label ID: \t\t[1-9]
Annotate: \t\tSpace or Left Click
Previous/Next Image: \t</>
Save Annotation: \tCtrl + s
Exit application: \tESC"""
        QtGui.QMessageBox.information(self, 'About Pychet Circle Annotator', message)

    def loadAnnotations(self):
        """Look for annotation file in label folder and load data"""
        # Get current file name
        filename = os.path.splitext(str(self.ui.imageComboBox.currentText()))[0]
        if self.labelFolder is None:
            self.labelFolder = os.path.join(self.folder_image, '../labels-circles/')
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

    n_args = len(sys.argv)
    if n_args >= 2:
        main.openImageDirectory(sys.argv[1])
    if n_args >= 3:
        main.setLabelDirectory(sys.argv[2])

    sys.exit(app.exec_())

