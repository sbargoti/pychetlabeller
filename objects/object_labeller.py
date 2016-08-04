#! /usr/bin/python
"""
Image annotation tool.
Annotate using circular or rectangular shapes
"""
__author__ = 'suchet'
__date__ = '04/08/16' 


import sys, os, csv, argparse
import numpy as np
import svgwrite
from PyQt4 import QtGui, QtCore
from pychetlabeller.objects.object_labeller_ui import Ui_MainWindow
from shapely.geometry import Point, Polygon, box

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
                    self.add(LabelCircle(int(line[4]), float(line[1]), float(line[2]), float(line[3])))
            except ValueError:
                # Things that don't convert will be skipped
                if not line[0][0] == '#': # ignore comments
                    print "WARNING: Skipped a line (ValueError) '%s'" % line
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
    def click(self, parent, button, release=False):
        raise NotImplementedError("Tool::click")
    def wheel(self, parent, QWheelEvent):
        pass
    def paint(self, parent, QPainter, QStyleOptionGraphicsItem, QWidget):
        raise NotImplementedError("Tool::paint")
    def mouse_move(self, parent, pos):
        self.position = pos
    def key_down(self, parent, event):
        pass
    def key_up(self, parent, event):
        pass
    def enable(self, parent):
        pass
    def disable(self, parent):
        pass

class Tool_Circle(Tool):
    '''This tool creates a circle when clicked'''
    def __init__(self):
        super(Tool_Circle, self).__init__()
        self.radius = 20
        self.label = 1
        self.radius_scroll_delta = 2
    def click(self, parent, button, release=False):
        modifiers = QtGui.QApplication.keyboardModifiers()
        point = (self.position.x(), self.position.y())
        if release:
            return
        if modifiers == QtCore.Qt.ShiftModifier and button == QtCore.Qt.LeftButton:
            datum = sorted(label_dataset.data_at(point))
            if datum:
                parent.highlight(datum[0])
        elif modifiers == QtCore.Qt.NoModifier and button == QtCore.Qt.LeftButton:
            parent.add_datum(LabelCircle(self.label, point[0], point[1], self.radius))
    def wheel(self, parent, QWheelEvent):
        delta = QWheelEvent.delta()
        self.radius += np.sign(delta) * self.radius_scroll_delta
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
            parent.imagePanel.remove_datum(shape, from_tree=True)
            parent.update()
            parent.imagePanel.update()
            parent.ui.treeWidget.update()
        else:
            keystr = str(QtCore.QString(QtCore.QChar(key)))
            if keystr and any([keystr == chr(i) for i in xrange(ord('0'), 1 + ord('9'))]):
                self.label = int(keystr)
                parent.ui.item_label_txt.setText(keystr)

class Tool_Rectangle(Tool):
    '''This tool creates a rectangle when clicked'''
    def __init__(self):
        super(Tool_Rectangle, self).__init__()
        self.dx, self.dy = float(20), float(20)
        self.label = 1
        self.size_scroll_delta = 2
        self.resize_x = False
        self.resize_y = False
    def click(self, parent, button, release=False):
        modifiers = QtGui.QApplication.keyboardModifiers()
        point = (self.position.x(), self.position.y())
        if release:
            return
        if modifiers == QtCore.Qt.ShiftModifier and button == QtCore.Qt.LeftButton:
            datum = sorted(label_dataset.data_at(point))
            if datum:
                parent.highlight(datum[0])
        elif modifiers == QtCore.Qt.NoModifier and button == QtCore.Qt.LeftButton:
            parent.add_datum(LabelRectangle(self.label, point[0], point[1], self.dx, self.dy))
    def wheel(self, parent, QWheelEvent):
        delta = QWheelEvent.delta()
        dx_delta, dy_delta = 1, 1
        if self.resize_x:
            dy_delta = 0
        elif self.resize_y:
            dx_delta = 0

        self.dx += np.sign(delta) * self.size_scroll_delta * dx_delta
        self.dy += np.sign(delta) * self.size_scroll_delta * dy_delta
        parent.update()
        super(Tool_Rectangle, self).wheel(parent, QWheelEvent)
    def paint(self, parent, QPainter, QStyleOptionGraphicsItem, QWidget):
        QPainter.drawRect(self.position.x(), self.position.y(), self.dx, self.dy)
    def enable(self, parent):
        # parent.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        parent.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
    def key_down(self, parent, event):
        key = event.key()
        if key == QtCore.Qt.Key_Backspace and len(label_dataset.data):
            shape = label_dataset.data[-1]
            parent.imagePanel.remove_datum(shape, from_tree=True)
            parent.update()
            parent.imagePanel.update()
            parent.ui.treeWidget.update()
        elif key == QtCore.Qt.Key_Q:
            self.resize_x = True
        elif key == QtCore.Qt.Key_A:
            self.resize_y = True
        else:
            keystr = str(QtCore.QString(QtCore.QChar(key)))
            if keystr and any([keystr == chr(i) for i in xrange(ord('0'), 1 + ord('9'))]):
                self.label = int(keystr)
                parent.ui.item_label_txt.setText(keystr)
    def key_up(self,parent,event):
        key = event.key()
        if key == QtCore.Qt.Key_Q:
            self.resize_x = False
        elif key == QtCore.Qt.Key_A:
            self.resize_y = False


class Tool_TransformView(Tool):
    def __init__(self):
        super(Tool_TransformView, self).__init__()
        self.is_moving = False
        self.last_cursor = None
    def click(self, parent, button, release=False):
        if release:
            parent.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))
            # parent.setDragMode(QtGui.QGraphicsView.ScrollHandDrag)
            parent.setFlag(QtGui.QGraphicsItem.ItemIsMovable, False)
        else:
            parent.setCursor(QtGui.QCursor(QtCore.Qt.ClosedHandCursor))
            # parent.setDragMode(QtGui.QGraphicsView.NoDrag)
            parent.setFlag(QtGui.QGraphicsItem.ItemIsMovable, True)
    def wheel(self, parent, QWheelEvent):
        delta = np.sign(QWheelEvent.delta()) * 0.1 
        parent.zoom(delta)
    def paint(self, parent, QPainter, QStyleOptionGraphicsItem, QWidget):
        pass
    def enable(self, parent):
        self.last_cursor = parent.cursor()
        parent.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))
    def disable(self, parent):
        parent.setCursor(self.last_cursor)
        self.last_cursor = None

class Tool_Polygon(Tool):
    '''not yet implemented'''
    pass #

class LabelShape(object):
    '''base class of all data'''
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

class LabelRectangle(LabelShape):
    enum = 1
    def __init__(self, label, x, y, dx, dy):
        rectangle = box(x, y, x+dx, y+dy)
        super(LabelRectangle, self).__init__(label, rectangle)
    def get_rect_data(self):
        x1, y1, x2, y2 = self.shape.bounds
        x, y, dx, dy = x1, y1, x2-x1, y2-y1
        return x,y,dx,dy
    def populate_view(self, view, **kwargs):
        x, y, dx, dy = self.get_rect_data()
        if isinstance(view, QtGui.QTreeWidgetItem):
            # NOTE: It is important not to change the first field as it is used for lookup
            view.setText(0, str(self.id)) 
            view.setText(1, "(%d, %d)" % (x, y))
            view.setText(2, "(%d, %d)" % (dx, dy))
            view.setText(3, str(self.label))
        elif isinstance(view, QtGui.QPainter):
            view.drawRect(x, y, dx, dy)
    def serialize(self):
        return (LabelRectangle.enum,) + self.get_rect_data() + (self.label,)
    def svg_shape(self):
        '''return the SVG shape that this object represents'''
        r, g, b = my_colormap[self.label]
        x, y, dx, dy = self.get_rect_data()
        return svgwrite.shapes.Rect(insert=(x, y)
            , size=(dx,dy), stroke=svgwrite.rgb(r, g, b, 'RGB')
            , fill=svgwrite.rgb(r, g, b, 'RGB'))


class LabelCircle(LabelShape):
    enum = 1
    def __init__(self, label, x, y, radius):
        circle = Point(x, y).buffer(radius)
        (circle.x, circle.y, circle.radius) = (x, y, radius)
        super(LabelCircle, self).__init__(label, circle)
    def populate_view(self, view, **kwargs):
        if isinstance(view, QtGui.QTreeWidgetItem):
            # NOTE: It is important not to change the first field as it is used for lookup
            view.setText(0, str(self.id)) 
            view.setText(1, "(%d, %d)" % (self.shape.x, self.shape.y))
            view.setText(2, str(self.shape.radius))
            view.setText(3, str(self.label))
        elif isinstance(view, QtGui.QPainter):
            (x, y) = (self.shape.x - self.shape.radius, self.shape.y - self.shape.radius)
            side_width = 2*self.shape.radius
            view.drawEllipse(x , y, side_width, side_width)
    def serialize(self):
        return (self.id, self.shape.x, self.shape.y
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

class ObjectDrawPanel(QtGui.QGraphicsPixmapItem):
    """Establish a pixmap item on which labelling (painting) will be performed"""
    def __init__(self, pixmap=None, parent=None, scene=None, tool='circle'):
        self.is_initialised = False
        super(ObjectDrawPanel, self).__init__()
        # Class variables
        self.parent = parent # Parent class - ui mainwindow
        self.current_scale = 1.0
        self.defaultColorPixmap = None
        self.highlighted_datum = None
        # Annotation parameters
        self.opacity = 60 # Opacity of annotation
        self.highlight_opacity = 100
        # Annotation drawing
        self.changeMade = None
        # Use arg parse to select tool:
        self.tool_last = Tool_TransformView()
        if tool == 'circle':
            self.tool = Tool_Circle()
        elif tool == 'rectangle':
            self.tool = Tool_Rectangle()
        else:
            raise ValueError('Input tool {} not valid'.format(tool))
        
        self.num_labels = 9
        self.pen = None
        #TODO: Tidy brushes
        self.highlightbrushes = []
        self.savebrushes = []
        self.setBrushes()
        # Set up options
        self.setAcceptHoverEvents(True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable, False)
        self.tool.enable(self)
        self.is_initialised = True
    def change_tool(self, tool=None):
        '''set the active tool'''
        if tool:
            self.tool_last = self.tool
            self.tool = tool
        else: # swap between previous tool
            (self.tool, self.tool_last) = (self.tool_last, self.tool)
        self.tool_last.disable(self)
        self.tool.enable(self)
    def zoom(self, delta):
        """Zoom in to image by a fraction delta"""
        self.current_scale = max(self.current_scale + delta, 0.1)
        self.setScale(self.current_scale)
    def setBrushes(self):
        """Set the brushes for normal view, annotated view, highlighted view"""
        self.pen = QtGui.QPen(QtCore.Qt.SolidLine)
        self.pen.setColor(QtCore.Qt.black)
        self.pen.setWidth(1)
        self.savebrushes = [
            QtGui.QBrush(QtGui.QColor(my_colormap[label_no][0],
            my_colormap[label_no][1],
            my_colormap[label_no][2],
            self.opacity)) for label_no in range(10)]
        self.highlightbrushes = [
            QtGui.QBrush(QtGui.QColor(my_colormap[label_no][0],
           my_colormap[label_no][1],
           my_colormap[label_no][2],
           self.highlight_opacity)) for label_no in range(10)]
    def paint(self, QPainter, QStyleOptionGraphicsItem, QWidget):
        """Painter to draw annotations"""
        if not self.is_initialised:
            return
        # Set image and pen
        QPainter.drawPixmap(0, 0, self.pixmap())
        QPainter.setPen(self.pen)
        self.tool.paint(self, QPainter, QStyleOptionGraphicsItem, QWidget)
        for datum in label_dataset.data:
            if datum is self.highlighted_datum:
                QPainter.setBrush(self.highlightbrushes[datum.label])
            else:
                QPainter.setBrush(self.savebrushes[datum.label])
            datum.populate_view(QPainter)
    def hoverMoveEvent(self, event): #QGraphicsSceneHoverEvent
        '''While moving inside the picture, update x,y position for drawing annotation tool
        If instead in moving mode (grab and move image), do nothing.'''
        self.tool.mouse_move(self, event.pos())
        self.update()
    def mousePressEvent(self, event): # QGraphicsSceneMouseEvent
        self.setFocus()
        self.tool.click(self, event.button())
    def wheelEvent(self, QWheelEvent):
        self.tool.wheel(self, QWheelEvent)
    def mouseReleaseEvent(self, event): # QGraphicsSceneMouseEvent
        self.tool.click(self, event.button(), release=True)
        #NOTE: The following line has to be here to propagate the event
        QtGui.QGraphicsPixmapItem.mouseReleaseEvent(self, event)
    def add_datum(self, label_shape):
        label_dataset.add(label_shape)
        item = QtGui.QTreeWidgetItem(self.parent.ui.treeWidget)
        label_shape.populate_view(item)
        self.changeMade = True
    def remove_datum(self, label_shape, from_tree=False):
        if from_tree:
            tree = self.parent.ui.treeWidget
            item = tree.findItems(str(label_shape.id), QtCore.Qt.MatchExactly, 0)[0]
            tree.takeTopLevelItem(tree.indexOfTopLevelItem(item))
        if self.highlighted_datum is label_shape:
            self.highlighted_datum = None
        label_dataset.remove(label_shape)
    def highlight(self, datum):
        self.highlighted_datum = datum
        if datum:
            item = self.parent.ui.treeWidget.findItems(
                str(datum.id), QtCore.Qt.MatchExactly, 0)[0]
            self.parent.ui.treeWidget.setCurrentItem(item)
        self.update()
        self.parent.ui.treeWidget.setFocus()
class MainWindow(QtGui.QMainWindow):
    """The main window of the GUI - designed using Qt Designer"""
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
        self.scene = None
        self.imagePanel = None
        self.image_index = None
        self.images = None
        self.default_directory = os.path.expanduser("~")
        self.folder_image = None
        self.pixmap = None
        self.tool_str = 'circle'
        # Define key and mouse function names
        self.key_alternate_tool = QtCore.Qt.Key_Control
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
        ui = self.ui
        # handlers: [UI Element, Signal, Handler]
        handlers = [ \
        # Folder/image navigation
        [ui.browse_btn, QtCore.SIGNAL("clicked()"), self.openImageDirectory],
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
        ui.actionSave_Label.setShortcut(QtGui.QKeySequence("Ctrl+s"))
        ui.actionExit_3.setStatusTip('Exit Application')
        ui.actionExit_3.setShortcut(QtCore.Qt.Key_Escape)
        ui.actionAbout.setShortcut(QtCore.Qt.Key_F1)
        ui.actionLoad_Label.setShortcut(QtGui.QKeySequence("Ctrl+l"))
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
        self.ui.graphicsView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.ui.graphicsView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
    def eventFilter(self, QObject, QEvent):
        """Filter out wheel event from the window - we want to reserve the wheel for other commands"""
        if QObject is self.ui.graphicsView.viewport() and QEvent.type() == QtCore.QEvent.Wheel:
            return True
        return False
    def mainKeyPressEvent(self, event):
        key = event.key()
        if key == self.key_alternate_tool: # Alternate tool
            self.imagePanel.change_tool()
            # self.update()
        elif key == QtCore.Qt.Key_Period: # Browse images, prev <-> next
            self.ui.next_btn.animateClick()
        elif key == QtCore.Qt.Key_Comma:
            self.ui.prev_btn.animateClick()
        else:
            self.imagePanel.tool.key_down(self, event)
    def mainKeyReleaseEvent(self, event):
        self.imagePanel.tool.key_up(self, event)
        key = event.key()
        if key == self.key_alternate_tool:
            self.imagePanel.change_tool()
            # self.update()
    def treeMousePress(self, event):
        """ Mouse events on the tree - select annotations """
        # Check if mouse selected gives a valid item
        item = self.ui.treeWidget.indexAt(event.pos())
        if item.isValid():
            QtGui.QTreeWidget.mousePressEvent(self.ui.treeWidget, event)
            selected_item = self.ui.treeWidget.currentItem()
            datum = label_dataset.find(int(selected_item.text(0)))
            self.imagePanel.highlight(datum)
    def treeKeyPress(self, event):
        """ Keyboard events on the tree - move through annotations or delete them """
        selected_item = self.ui.treeWidget.currentItem()
        if selected_item is None:
            return
        key = event.key()
        datum = label_dataset.find(int(selected_item.text(0)))
        do_update = True
        if key == QtCore.Qt.Key_Delete and datum is not None:
            next_item = self.ui.treeWidget.itemAbove(selected_item)
            self.imagePanel.remove_datum(datum)
            if next_item:
                self.ui.treeWidget.setCurrentItem(next_item)
            self.ui.treeWidget.takeTopLevelItem(self.ui.treeWidget.indexOfTopLevelItem(selected_item))
        elif key in [QtCore.Qt.Key_Down, QtCore.Qt.Key_Up]:
            # Navigate through items - highlighting the current selection on the image
            if key == QtCore.Qt.Key_Up:
                next_item = self.ui.treeWidget.itemAbove(selected_item)
            else:
                next_item = self.ui.treeWidget.itemBelow(selected_item)
            if next_item:
                self.ui.treeWidget.setCurrentItem(next_item)
        else:
            do_update = False
        if do_update:
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
        self.firstImage = False
        # Set scene and add to graphics view
        self.scene = QtGui.QGraphicsScene()
        self.imagePanel = ObjectDrawPanel(scene=self.scene, parent=self, tool=self.tool_str)
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
            pixmap = pixmap.scaled(QtCore.QSize(self.original_size[0], self.original_size[1]),
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
        opendirectory = self.folder_image or self.default_directory
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
            self.labelFolder = os.path.join(self.folder_image, '../labels/')
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
Object annotation tool.
Pick image directory (containing .jpg or .png files) and start labelling! Labels saved as .csv in the same parent folder as the images, under folder labels
The Labels are stored in format: 
Circles: item, c-x, c-y, radius, label #.
Rectangles: item, x, c, dx, dy, label #.
If Auto save is selected, the annotations will be saved upon clicking next/previous image (or by ctrl + s)
If Auto Load is selected, when an image loads, so will its annotations in the labels folder if they exist.
To delete an annotation, select it with a right click of from the annotation list and press delete.

Controls:
Zoom in/out: \t-/+ or Ctrl + Wheel Button
Move Image: \tShift + Wheel Button
Object Size Radius: \t Wheel Button (press q or a to change dx, dy for rectangles)
Label ID: \t\t[1-9]
Annotate: \t\tSpace or Left Click
Select Annotation: \t Shift Click
Previous/Next Image: \t</>
Save Annotation: \tCtrl + s
Exit application: \tESC"""
        QtGui.QMessageBox.information(self, 'About Pychet Circle Annotator', message)
    def loadAnnotations(self):
        """Look for annotation file in label folder and load data"""
        # Get current file name
        filename = os.path.splitext(str(self.ui.imageComboBox.currentText()))[0]
        if self.labelFolder is None:
            self.labelFolder = os.path.join(self.folder_image, '../labels/')
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

def parse_args():
    parser = argparse.ArgumentParser(description='Object annotation toolbox')
    parser.add_argument('image_folder', metavar='IF', nargs='?', default=None, help='Image folder')
    parser.add_argument('annotation_folder', metavar='AF', nargs='?', default=None, help='Annotation folder')
    parser.add_argument('--tool', dest='tool', default='circle', help='circle or rectangle', type=str)
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = parse_args()

    app = QtGui.QApplication(sys.argv)
    main = MainWindow()
    main.tool_str = args.tool
    main.show()

    if args.image_folder is not None:
        main.openImageDirectory(args.image_folder)
    if args.annotation_folder is not None:
        main.openImageDirectory(args.annotation_folder)



    sys.exit(app.exec_())

