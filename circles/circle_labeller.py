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

# class Command(object):
#     '''Superclass for editor commands'''
#     def __init__(self, **kwargs):
#         pass
#     def execute():
#         raise NotImplementedError("Command::execute")

class Tool(object):
    def __init__(self):
        self.position = QtCore.QPointF(0, 0)
    def click(self, parent, button):
        raise NotImplementedError("Tool::click")
    def wheel(self, parent, QWheelEvent):
        ## Zoom support
        delta = np.sign(QWheelEvent.delta()) * 0.1 
        if QtGui.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier:
            parent.zoom(delta)
    def paint(self, parent, QPainter, QStyleOptionGraphicsItem, QWidget):
        raise NotImplementedError("Tool::paint")
    def mouse_move(self, parent, pos):
        self.position = pos
    def key_down(self, parent, event):
        pass
    def enable(self, parent):
        pass
    def disable(self, parent):
        pass

class Tool_Circle(Tool):
    '''This tool creates a circle when clicked'''
    defaults = {
        'radius': 10,
        'radius_scroll_delta': 1,
        'label': 1
    }
    def __init__(self):
        super(Tool_Circle, self).__init__()
        self.radius = Tool_Circle.defaults['radius']
        self.label = Tool_Circle.defaults['label']
    def click(self, parent, button):
        if button == QtCore.Qt.LeftButton:
            parent.add_datum(LabelCircle(self.label, self.position.x()
                , self.position.y(), self.radius))
    def wheel(self, parent, QWheelEvent):
        delta = QWheelEvent.delta()
        self.radius += np.sign(delta) * self.defaults['radius_scroll_delta']
        parent.update()
        super(Tool_Circle, self).wheel(parent, QWheelEvent)
    def paint(self, parent, QPainter, QStyleOptionGraphicsItem, QWidget):
        QPainter.drawEllipse(
            self.position.x() - self.radius
            , self.position.y() - self.radius
            , 2 * self.radius, 2 * self.radius)
    def enable(self, parent):
        # parent.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        parent.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
    def key_down(self, parent, event):
        key = event.key()
        if key == QtCore.Qt.Key_Backspace and len(label_dataset.data):
            shape = label_dataset.data[-1]
            label_dataset.remove(shape)
            parent.update()
        else:
            keystr = str(QtCore.QString(QtCore.QChar(key)))
            if keystr and any([keystr == chr(i) for i in xrange(ord('0'), 1 + ord('9'))]):
                print keystr
                self.label = int(keystr)
                parent.ui.item_label_txt.setText(keystr)

class Tool_Select(Tool):
    defaults = {}
    def __init__(self):
        super(Tool_Select, self).__init__()
        self.modifiers = QtCore.Qt.NoModifier
        self.is_moving = False
        self.last_cursor = None
    def click(self, parent, button):
        point = (self.position.x(), self.position.y())
        if self.modifiers == QtCore.Qt.ShiftModifier:
            parent.setCursor(QtGui.QCursor(QtCore.Qt.ClosedHandCursor))
        elif self.modifiers == QtCore.Qt.NoModifier:
            datum = sorted(label_dataset.data_at(point))
            if datum:
                item = parent.parent.ui.treeWidget.findItems(
                str(datum[0].id), QtCore.Qt.MatchExactly, 0)[0]
                parent.parent.ui.treeWidget.setCurrentItem(item)
                parent.update()
                parent.parent.ui.treeWidget.setFocus()
    def wheel(self, parent, delta):
        pass
    def paint(self, parent, QPainter, QStyleOptionGraphicsItem, QWidget):
        pass
    def enable(self, parent):
        self.last_cursor = parent.cursor()
        parent.setFlag(QtGui.QGraphicsItem.ItemIsMovable, True)
        parent.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))
    def disable(self, parent):
        parent.setFlag(QtGui.QGraphicsItem.ItemIsMovable, False)
        parent.setCursor(self.last_cursor)
        self.last_cursor = None

class Tool_Polygon(Tool):
    defaults = {}
    def __init__(self):
        self.points = []
    def click(self, x, y, button):
        pass
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
        self.current_scale = 1.0
        self.defaultColorPixmap = None
        self.highlighted_id = None
        # Annotation parameters
        self.radius = 10.0
        self.opacity = 60 # Opacity of annotation
        self.highlight_opacity = 100
        self.label = 1 # Label of circle
        self.tool_last = Tool_Select()
        # Annotation results
        self.changeMade = None
        # Annotation drawing
        self.pen = QtGui.QPen(QtCore.Qt.SolidLine)
        self.pen.setColor(QtCore.Qt.black)
        self.pen.setWidth(1)
        self.tool = Tool_Circle()
        self.num_labels = 9
        self.setBrushes()
        self.highlight_centroid = None # Index of highlighted annotation
        # Set up options
        self.setAcceptHoverEvents(True)
        self.MovingMode = False # Check if image is being moved
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable, False) # todo
        self.tool.enable(self)
    def change_tool(self, tool=None):
        '''set the active tool'''
        if tool:
            self.tool_last = tool
            self.tool = tool
        else: # swap between previous tool
            (self.tool, self.tool_last) = (self.tool_last, self.tool)
        self.tool_last.disable(self)
        self.tool.enable(self)
    def zoom(self, delta):
        """Zoom in to image by a fraction delta"""
        self.current_scale += delta
        self.setScale(self.current_scale)
        # self.x = -1
    def setBrushes(self):
        """Set the brushes for normal view, annotated view, highlighted view"""
        self.testbursh =  QtGui.QBrush(QtGui.QColor(255, 255, 0, self.opacity))
        self.savebrush = QtGui.QBrush(QtGui.QColor(255, 0, 0, self.opacity))
        self.savebrushes = [
            QtGui.QBrush(QtGui.QColor(my_colormap[label_no][0],
            my_colormap[label_no][1],
            my_colormap[label_no][2],
            self.opacity)) for label_no in range(10)]
        self.highlightbrush = QtGui.QBrush(QtGui.QColor(0, 0, 255, self.opacity))
        self.highlightbrushes = [
            QtGui.QBrush(QtGui.QColor(my_colormap[label_no][0],
           my_colormap[label_no][1],
           my_colormap[label_no][2],
           self.highlight_opacity)) for label_no in range(10)]
    def paint(self, QPainter, QStyleOptionGraphicsItem, QWidget):
        """Painter to draw annotations"""
        # Set image and pen
        QPainter.drawPixmap(0, 0, self.pixmap())
        QPainter.setPen(self.pen)
        self.tool.paint(self, QPainter, QStyleOptionGraphicsItem, QWidget)
        for datum in label_dataset.data:
            if datum.id == self.highlighted_id:
                QPainter.setBrush(self.highlightbrushes[datum.label])
            else:
                QPainter.setBrush(self.savebrushes[datum.label])
            datum.populate_view(QPainter, scale=1.0)
    def hoverMoveEvent(self, event): #QGraphicsSceneHoverEvent
        '''While moving inside the picture, update x,y position for drawing annotation tool
        If instead in moving mode (grab and move image), do nothing.'''
        self.tool.mouse_move(self, event.pos())
        self.update()
    def mousePressEvent(self, event): # QGraphicsSceneMouseEvent
        """Record the annotation when mouse is clicked.
        If Image is in moving mode, prepare to move image"""
        self.setFocus()
        self.tool.click(self, event.button())
    def wheelEvent(self, QWheelEvent):
        self.tool.wheel(self, QWheelEvent)
    def mouseReleaseEvent(self, event): # QGraphicsSceneMouseEvent
        """If image was in moving more, change cursor grab icon"""
        QtGui.QGraphicsPixmapItem.mouseReleaseEvent(self, event)
    def add_datum(self, label_shape):
        label_dataset.add(label_shape)
        item = QtGui.QTreeWidgetItem(self.parent.ui.treeWidget)
        label_shape.populate_view(item)
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
    def connectSignals(self):
        """ Connect all the components on the GUI to respective functions """
        # Folder/image navigation
        ui = self.ui
        handlers = \
        [[ui.browse_btn, QtCore.SIGNAL("clicked()"), self.openImageDirectory],
        [ui.label_folder_btn, QtCore.SIGNAL("clicked()"), self.setLabelDirectory],
        [ui.prev_btn, QtCore.SIGNAL("clicked()"), self.previousImage],
        [ui.next_btn, QtCore.SIGNAL("clicked()"), self.nextImage],
        [ui.imageComboBox, QtCore.SIGNAL("currentIndexChanged(QString)"), self.changeImage],
        [ui.save_btn, QtCore.SIGNAL("clicked()"), self.saveAnnotations],
        # Menu bar
        [ui.actionOpen_Folder, QtCore.SIGNAL("triggered()"), self.openImageDirectory],
        [ui.actionSave_Label, QtCore.SIGNAL("triggered()"), self.saveAnnotations],
        [ui.actionExit_3, QtCore.SIGNAL("triggered()"), self.close],
        [ui.actionAbout, QtCore.SIGNAL("triggered()"), self.aboutWindow],
        [ui.actionLoad_Label, QtCore.SIGNAL("triggered()"), self.loadFromFile],
        # Annotation tool
        [ui.opacity_slider, QtCore.SIGNAL('valueChanged(int)'), self.change_opacity],
        # Imaging properties
        [ui.brightness_slider, QtCore.SIGNAL('valueChanged(int)'), self.change_brightness],
        [ui.contrast_slider, QtCore.SIGNAL('valueChanged(int)'), self.change_contrast]]
        for handler in handlers:
            self.connect(handler[0], handler[1], handler[2])
        self.ui.actionSave_Label.setShortcut(QtGui.QKeySequence("Ctrl+s"))
        self.ui.actionExit_3.setStatusTip('Exit Application')
        self.ui.actionExit_3.setShortcut(QtCore.Qt.Key_Escape)
        self.ui.actionAbout.setShortcut(QtCore.Qt.Key_F1)
        self.ui.actionLoad_Label.setShortcut(QtGui.QKeySequence("Ctrl+l"))
        # Drag and drop data
        self.setAcceptDrops(True)
    def dragEnterEvent(self, QDragEnterEvent):
        """Dragging in folders"""
        if QDragEnterEvent.mimeData().hasUrls:
            QDragEnterEvent.accept()
        else:
            QDragEnterEvent.ignore()
    def dropEvent(self, QDropEvent):
        """Drop a folder and ask user to select if image folder or label folder"""
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
        """Set scene properties - disable scrolling"""
        self.ui.graphicsView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.ui.graphicsView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        # self.ui.graphicsView.setFocusPolicy(QtCore.Qt.NoFocus)
    def eventFilter(self, QObject, QEvent):
        """Filter out wheel event from the window - we want to reserve the wheel for other commands"""
        if QObject == self.ui.graphicsView.viewport() and QEvent.type() == QtCore.QEvent.Wheel:
            return True
        return False
    # def wheelEvent(self, QWheelEvent): # TODO: Fix this handler to forward event
    #     self.ui.graphicsView.wheelEvent(QWheelEvent)
    def mainKeyPressEvent(self, event):
        self.imagePanel.tool.key_down(self, event)
        key = event.key()
        if key == QtCore.Qt.Key_Shift: # Alternate tool
            self.imagePanel.change_tool()
            self.update()
        # elif key == QtCore.Qt.Key_Equal or key == QtCore.Qt.Key_Plus:
        #     self.zoom(self.scroll_zoom_delta)
        # elif key == QtCore.Qt.Key_Minus:
        #     self.zoom(-self.scroll_zoom_delta)
        # elif key == QtCore.Qt.Key_Space:
        #     # Annotate current position (if for some reason clicking is too hard)
        #     if self.imagePanel.x >= 0:
        #         point = (self.imagePanel.x/self.imagePanel.current_scale, self.imagePanel.y/self.imagePanel.current_scale)
        #         radius = self.imagePanel.radius/self.imagePanel.current_scale
        #         self.add(point, radius, self.imagePanel.label)
        #         # self.populateTree()
        elif key == QtCore.Qt.Key_Period:
        # Browse images, prev <-> next
            self.ui.next_btn.animateClick()
        elif key == QtCore.Qt.Key_Comma:
            self.ui.prev_btn.animateClick()
    def mainKeyReleaseEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Shift:
            # Releasing the mouse button after dragging the image
            self.imagePanel.change_tool()
            self.update()
            # self.imagePanel.MovingMode = False
            # self.imagePanel.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
    def treeMousePress(self, event):
        """ Mouse events on the tree - select annotations """
        # Check if mouse selected gives a valid item
        item = self.ui.treeWidget.indexAt(event.pos())
        if item.isValid():
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
            self.ui.graphicsView.size().width() - 10,
            self.ui.graphicsView.size().height() - 10)
    def populateTree(self):
        """ Update the tree when a new annotation is added """
        self.ui.treeWidget.clear()
        for datum in label_dataset.data:
            datum.populate_view(QtGui.QTreeWidgetItem(self.ui.treeWidget))   
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
        self.populateTree()
    def previousImage(self):
        """ Navigate to previous image in the folder """
        self.nextImage(delta=-1)
    def nextImage(self, delta=1):
        """ Navigate to next image in the folder """
        # Save annotations if needed
        self.imagePanel.current_scale = 1.0
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
    """Resize function for window to properly fit an image."""
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

