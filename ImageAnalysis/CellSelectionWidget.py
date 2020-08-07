# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 21:00:06 2020

@author: xinmeng
"""

from __future__ import division
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import  QFont

from PyQt5.QtWidgets import (QWidget, QLabel, QSpinBox, QDoubleSpinBox, QGridLayout, QPushButton, 
                             QLineEdit, QTabWidget, QCheckBox)

import os, sys
sys.path.append('../')
from CoordinatesManager.ui_widgets.DrawingWidget import DrawingWidget
from HamamatsuCam.HamamatsuActuator import CamActuator
from ImageAnalysis.ImageProcessing import ProcessImage

import pyqtgraph as pg


import numpy as np
from skimage.io import imread
from skimage.color import gray2rgb
from skimage.transform import resize
from skimage.measure import find_contours
import threading
import colorsys
import random

import StylishQT


from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


        
from MaskRCNN.Configurations.ConfigFileInferenceOld import cellConfig
from CellDetectorGUI import CellGui

config = cellConfig()
config.IMAGE_RESIZE_MODE = "square"
config.IMAGE_MIN_DIM = 512
config.IMAGE_MAX_DIM = 1024
config.IMAGE_MIN_SCALE = 2.0
config.LogDir = ''
config.WeigthPath = r'M:\tnw\ist\do\projects\Neurophotonics\Brinkslab\Data\Martijn\FinalResults\ModelWeights.h5'
# =============================================================================
# Threading decorators
# =============================================================================
def run_in_thread(fn):
    """
    Use a Decorator to put self functions in thread.
    https://stackoverflow.com/questions/23944657/typeerror-method-takes-1-positional-argument-but-2-were-given
    """
    @staticmethod
    def run(*k):
        thread = threading.Thread(target=fn, args=(*k,), daemon = True)
        thread.start()
        return thread # <-- return the thread
    return run
    
class MainGUI(QWidget):
    
    # signal_DMDmask is cictionary with laser specification as key and binary mask as content.
    signal_DMDmask = pyqtSignal(dict)
    signal_DMDcontour = pyqtSignal(list)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        os.chdir('./')# Set directory to current folder.
        self.setFont(QFont("Arial"))
        
#        self.setMinimumSize(900, 1020)
        self.setWindowTitle("Cell Selection")
        self.layout = QGridLayout(self)
        
        self.roi_list_freehandl_added = []

        self.selected_cells_infor_dict = {}

        self.mask_color_multiplier = [1, 1, 0]
        # =============================================================================
        #         Container for image display
        # =============================================================================
        graphContainer = StylishQT.roundQGroupBox()
        graphContainerLayout = QGridLayout()
        
        self.Imgviewtabs = QTabWidget()
        
        MLmaskviewBox = QWidget()
        MLmaskviewBoxLayout = QGridLayout()        
        self.Matdisplay_Figure = Figure()
        self.Matdisplay_Canvas = FigureCanvas(self.Matdisplay_Figure)
        # self.Matdisplay_Canvas.setFixedWidth(500)
        # self.Matdisplay_Canvas.setFixedHeight(500)
        self.init_CellSelectGui(config)
        # self.Matdisplay_Canvas.mpl_connect('button_press_event', self._onclick)
        
        self.Matdisplay_toolbar = NavigationToolbar(self.Matdisplay_Canvas, self)
        
        MLmaskviewBoxLayout.addWidget(self.Matdisplay_toolbar, 0, 0)  
        MLmaskviewBoxLayout.addWidget(self.Matdisplay_Canvas, 1, 0) 
        
        MLmaskviewBox.setLayout(MLmaskviewBoxLayout)
        
        self.Imgviewtabs.addTab(MLmaskviewBox,"MaskRCNN")
        
        # =============================================================================
        #         Mask editing tab
        # =============================================================================
        MLmaskEditBox = QWidget()
        MLmaskEditBoxLayout = QGridLayout() 
        
        self.Mask_edit_view = DrawingWidget(self)
        self.Mask_edit_view.enable_drawing(False) # Disable drawing first
#        self.Mask_edit_view = pg.ImageView()
#        self.Mask_edit_view.getView().setLimits(xMin = 0, xMax = 2048, yMin = 0, yMax = 2048, minXRange = 2048, minYRange = 2048, maxXRange = 2048, maxYRange = 2048)
        self.Mask_edit_viewItem = self.Mask_edit_view.getImageItem()
        
#        self.ROIitem = pg.PolyLineROI([[0,0], [80,0], [80,80], [0,80]], closed=True)
        self.Mask_edit_view_getView = self.Mask_edit_view.getView()
#        self.Mask_edit_view_getView.addItem(self.ROIitem)

        self.Mask_edit_view.ui.roiBtn.hide()
        self.Mask_edit_view.ui.menuBtn.hide() 
        self.Mask_edit_view.ui.normGroup.hide()
        self.Mask_edit_view.ui.roiPlot.hide()
        
        MLmaskEditBoxLayout.addWidget(self.Mask_edit_view, 0, 0) 
        
        MLmaskEditBox.setLayout(MLmaskEditBoxLayout)   
        
        self.Imgviewtabs.addTab(MLmaskEditBox,"Mask edit")
        
        graphContainerLayout.addWidget(self.Imgviewtabs, 0, 0) 
        graphContainer.setLayout(graphContainerLayout)
        
        # =============================================================================
        #         Operation container
        # =============================================================================
        operationContainer = StylishQT.roundQGroupBox()
        operationContainerLayout = QGridLayout()
        
        # self.init_ML_button = QPushButton('Initialize ML', self)
        # operationContainerLayout.addWidget(self.init_ML_button, 0, 0)
        # self.init_ML_button.clicked.connect(self.init_ML)        
        
        #---------------------Load image from file-----------------------------
        self.textbox_loadimg = QLineEdit(self)   
        self.textbox_loadimg.returnPressed.connect(self.textbox_loadimg_Fcn)
        operationContainerLayout.addWidget(self.textbox_loadimg, 1, 0)    
        
        
        self.button_import_img_browse = QPushButton('Browse', self)
        operationContainerLayout.addWidget(self.button_import_img_browse, 1, 1)
        self.button_import_img_browse.clicked.connect(self.get_img_file_tif)
        
        self.run_ML_button = QPushButton('Analysis', self)
        operationContainerLayout.addWidget(self.run_ML_button, 2, 0)
        self.run_ML_button.clicked.connect(self.run_ML_onImg_and_display)
        
        self.generate_MLmask_button = QPushButton('Mask', self)
        operationContainerLayout.addWidget(self.generate_MLmask_button, 2, 1)
        self.generate_MLmask_button.clicked.connect(self.generate_MLmask)
        
        self.update_MLmask_button = QPushButton('Update mask', self)
        operationContainerLayout.addWidget(self.update_MLmask_button, 3, 0)
        self.update_MLmask_button.clicked.connect(self.update_mask)
        
        self.enable_modify_MLmask_button = QPushButton('Enable free-hand', self)
        self.enable_modify_MLmask_button.setCheckable(True)
        operationContainerLayout.addWidget(self.enable_modify_MLmask_button, 4, 0)
        self.enable_modify_MLmask_button.clicked.connect(self.enable_free_hand)
        
#        self.modify_MLmask_button = QPushButton('Add patch', self)
#        operationContainerLayout.addWidget(self.modify_MLmask_button, 4, 1)
#        self.modify_MLmask_button.clicked.connect(self.addedROIitem_to_Mask)
        
        self.clear_roi_button = QPushButton('Clear ROIs', self)
        operationContainerLayout.addWidget(self.clear_roi_button, 5, 0)
        self.clear_roi_button.clicked.connect(self.clear_edit_roi)
        
#        self.maskLaserComboBox = QComboBox()
#        self.maskLaserComboBox.addItems(['640', '532', '488'])
#        operationContainerLayout.addWidget(self.maskLaserComboBox, 6, 0)
#        
#        self.generate_transformed_mask_button = QPushButton('Transform mask', self)
#        operationContainerLayout.addWidget(self.generate_transformed_mask_button, 6, 1)
#        self.generate_transformed_mask_button.clicked.connect(self.generate_transformed_mask)
        
        self.emit_transformed_mask_button = QPushButton('Emit mask', self)
        operationContainerLayout.addWidget(self.emit_transformed_mask_button, 7, 1)
        self.emit_transformed_mask_button.clicked.connect(self.emit_mask_contour)
        
        operationContainer.setLayout(operationContainerLayout)
        
        # =============================================================================
        #         Mask para container
        # =============================================================================
        
        PltparaContainer = self.init_Plt_Gui()
        
        # =============================================================================
        #         Matplotlib figure settings
        # =============================================================================
        MaskparaContainer = StylishQT.roundQGroupBox()
        MaskparaContainerContainerLayout = QGridLayout()
        
        #----------------------------------------------------------------------        
        self.fillContourButton = QCheckBox()
        self.invertMaskButton = QCheckBox()
        self.thicknessSpinBox = QSpinBox()
        self.thicknessSpinBox.setRange(1, 25)
        MaskparaContainerContainerLayout.addWidget(QLabel('Fill contour:'), 0, 0)
        MaskparaContainerContainerLayout.addWidget(self.fillContourButton, 0, 1)
        MaskparaContainerContainerLayout.addWidget(QLabel('Invert mask:'), 1, 0)
        MaskparaContainerContainerLayout.addWidget(self.invertMaskButton, 1, 1)
        MaskparaContainerContainerLayout.addWidget(QLabel('Thickness:'), 2, 0)
        MaskparaContainerContainerLayout.addWidget(self.thicknessSpinBox, 2, 1)
        
        MaskparaContainer.setLayout(MaskparaContainerContainerLayout)
        
        
        
        # =============================================================================
        #         Device operation container
        # =============================================================================
        deviceOperationContainer = StylishQT.roundQGroupBox()
        deviceOperationContainerLayout = QGridLayout()
        
        #----------------------------------------------------------------------
        self.CamExposureBox = QDoubleSpinBox(self)
        self.CamExposureBox.setDecimals(6)
        self.CamExposureBox.setMinimum(0)
        self.CamExposureBox.setMaximum(100)
        self.CamExposureBox.setValue(0.001501)
        self.CamExposureBox.setSingleStep(0.001)  
        deviceOperationContainerLayout.addWidget(self.CamExposureBox, 0, 1)  
        deviceOperationContainerLayout.addWidget(QLabel("Exposure time:"), 0, 0)
        
        cam_snap_button = QPushButton('Cam snap', self)
        deviceOperationContainerLayout.addWidget(cam_snap_button, 0, 2)
        cam_snap_button.clicked.connect(self.cam_snap)
        
        cam_snap_button = QPushButton('Cam snap', self)
        deviceOperationContainerLayout.addWidget(cam_snap_button, 0, 2)
        cam_snap_button.clicked.connect(self.cam_snap) 
        
        deviceOperationContainer.setLayout(deviceOperationContainerLayout)
        
        self.layout.addWidget(graphContainer, 0, 0, 3, 1)
        self.layout.addWidget(operationContainer, 0, 1)
        self.layout.addWidget(MaskparaContainer, 1, 1)
        self.layout.addWidget(deviceOperationContainer, 2, 1)
        self.layout.addWidget(PltparaContainer, 3,1)
        self.setLayout(self.layout)

    #%%
    def init_Plt_Gui(self):
        PltparaContainer = StylishQT.roundQGroupBox()
        PltparaContainerContainerLayout = QGridLayout()
        
        StateAllInit    = [True, False, False, False, False]
        StateSelectInit = [True, True, True, False, True]
        self.SelectCellGui.on_click_All(StateAllInit)
        self.SelectCellGui.on_click_High(StateSelectInit)
        
        names           = ['Show Cells:', 'Show Mask:', 'Show BBox:', 'Show Label:', 'Show Centre:']
        
        self.plt_All_ShowCell   = QCheckBox()
        self.plt_All_ShowBBox   = QCheckBox()
        self.plt_All_ShowMask   = QCheckBox()
        self.plt_All_ShowLabel  = QCheckBox()
        self.plt_All_ShowCentre = QCheckBox()
        AllButtons = [self.plt_All_ShowCell, self.plt_All_ShowMask, self.plt_All_ShowBBox, self.plt_All_ShowLabel, self.plt_All_ShowCentre]
        
        self.plt_Select_ShowCell   = QCheckBox()
        self.plt_Select_ShowBBox   = QCheckBox()
        self.plt_Select_ShowMask   = QCheckBox()
        self.plt_Select_ShowLabel  = QCheckBox()
        self.plt_Select_ShowCentre = QCheckBox()
        SelectButtons = [self.plt_Select_ShowCell, self.plt_Select_ShowMask, self.plt_Select_ShowBBox, self.plt_Select_ShowLabel, self.plt_Select_ShowCentre]
        index = 0
        for stateAll, StateSelect, name,  AllButton, SelectButton in zip(StateAllInit, StateSelectInit, names, AllButtons, SelectButtons):
            index += 1
            AllButton.clicked.connect(self.plt_CheckButton)
            AllButton.setChecked(stateAll)
            SelectButton.clicked.connect(self.plt_CheckButton)
            SelectButton.setChecked(StateSelect)
            PltparaContainerContainerLayout.addWidget(QLabel(name), index, 0)
            PltparaContainerContainerLayout.addWidget(AllButton,    index, 1)
            PltparaContainerContainerLayout.addWidget(SelectButton, index, 2)
       
        PltparaContainerContainerLayout.addWidget(QLabel('Operation'), 0, 0)
        PltparaContainerContainerLayout.addWidget(QLabel('All cells'), 0, 1)
        PltparaContainerContainerLayout.addWidget(QLabel('Selected cell'), 0, 2)
        
        self.plt_Select_MultiSelect = QCheckBox()
        self.plt_Select_MultiSelect.setChecked(self.SelectCellGui.EnableMultiCellSelection)
        self.plt_Select_MultiSelect.clicked.connect(self.MultiSelect_Fcn)    
        PltparaContainerContainerLayout.addWidget(QLabel('Enable multi select'), 6, 0)
        PltparaContainerContainerLayout.addWidget(self.plt_Select_MultiSelect, 6, 2)
        PltparaContainer.setLayout(PltparaContainerContainerLayout)
        return PltparaContainer
    
    
    # =============================================================================
    #     MaskRCNN detection part
    # =============================================================================    
#    @run_in_thread
    def init_ML(self):
        # Initialize the detector instance and load the model.
        print('Removed. ML is made when gui is initialised')
    
    def get_img_file_tif(self):
        self.img_tif_filePath, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Single File', 'M:/tnw/ist/do/projects/Neurophotonics/Brinkslab/Data',"(*.tif)")
        self.textbox_loadimg.setText(self.img_tif_filePath)
        
        if self.img_tif_filePath != None:
            self.Rawimage = imread(self.img_tif_filePath)
            
            self.MLtargetedImg_raw = self.Rawimage.copy()
            
            self.MLtargetedImg = self.convert_for_MaskRCNN(self.MLtargetedImg_raw)
            
            self.show_raw_image(self.MLtargetedImg)
            
            self.addedROIitemMask = np.zeros((self.MLtargetedImg.shape[0], self.MLtargetedImg.shape[1]))
            self.MLmask = np.zeros((self.MLtargetedImg.shape[0], self.MLtargetedImg.shape[1]))
    
    def textbox_loadimg_Fcn(self):
        Path = self.textbox_loadimg.text()
        if os.path.isfile(Path):
            self.Rawimage = imread(Path)
            
            self.MLtargetedImg_raw = self.Rawimage.copy()
            
            self.MLtargetedImg = self.convert_for_MaskRCNN(self.MLtargetedImg_raw)
            
            self.show_raw_image(self.MLtargetedImg)
            
            self.addedROIitemMask = np.zeros((self.MLtargetedImg.shape[0], self.MLtargetedImg.shape[1]))
            self.MLmask = np.zeros((self.MLtargetedImg.shape[0], self.MLtargetedImg.shape[1]))
        
    def show_raw_image(self, image):
        # display a single image
        self.SelectCellGui.ShowImage(image)
        
    def convert_for_MaskRCNN(self, input_img):
        """Convert the image size and bit-depth to make it suitable for MaskRCNN detection."""

        
        minval = np.min(input_img)
        maxval = np.max(input_img)
        
        output_image = ((input_img-minval)/(maxval-minval)*255).astype(np.uint8)
        
        if len(np.shape(output_image)) == 2:
            output_image = gray2rgb(output_image)

        return output_image 
       
    def init_CellSelectGui(self,config)  :
        self.Matdisplay_Figure.clear()
        self.ax1CellSelectGui = self.Matdisplay_Figure.add_subplot(111)
        self.SelectCellGui = CellGui(config,self.Matdisplay_Figure,self.ax1CellSelectGui)
        
    def run_ML_onImg_and_display(self):
        """Run MaskRCNN on input image"""
        
        
        # Depends on show_mask or not, the returned figure will be input raw image with mask or not.
        
        # self.SelectCellGui.RunDetection(r'M:\tnw\ist\do\projects\Neurophotonics\Brinkslab\Data\ML images\NewAnnotationDaanPart2\PMT\Critine\2020-4-08 Archon citrine library 100FOVstrial_3_library_cellspicked\Training\Round1_Coords3_R0C3300_PMT_0Zmax.png')     

        self.SelectCellGui.RunDetection(self.MLtargetedImg.copy())
        self.MLresults = self.SelectCellGui.getResults()
        
        self.Mask              = self.MLresults['masks']
        self.Label             = self.MLresults['class_ids']
        self.Score             = self.MLresults['scores']
        self.Bbox              = self.MLresults['rois']


        
    #%%
    # =============================================================================
    #     Configure click event to add clicked cell mask
    # =============================================================================       
    

                
    def get_cell_polygon(self, mask):  
        # Mask Polygon
        # Pad to ensure proper polygons for masks that touch image edges.
        padded_mask = np.zeros(
            (mask.shape[0] + 2, mask.shape[1] + 2), dtype=np.uint8)
        padded_mask[1:-1, 1:-1] = mask
        contours = find_contours(padded_mask, 0.5)
        for verts in contours:
            # Subtract the padding and flip (y, x) to (x, y)
            verts = np.fliplr(verts) - 1
            contour_polygon = mpatches.Polygon(verts, facecolor=self.random_colors(1)[0])
        
        return contours, contour_polygon
        
        
    def random_colors(self, N, bright=True):
        """
        Generate random colors.
        To get visually distinct colors, generate them in HSV space then
        convert to RGB.
        """
        brightness = 1.0 if bright else 0.7
        hsv = [(i / N, 1, brightness) for i in range(N)]
        colors = list(map(lambda c: colorsys.hsv_to_rgb(*c), hsv))
        random.shuffle(colors)
        return colors
    #%%
    # =============================================================================
    #     For mask generation
    # =============================================================================
    
    def generate_MLmask(self):
        """ Generate binary mask with all selected cells"""
        self.MLmask = np.zeros((self.MLtargetedImg.shape[0], self.MLtargetedImg.shape[1]))
        
        if len(self.SelectCellGui.AllSelectedIndex) > 0:
            for selected_index in self.SelectCellGui.AllSelectedIndex:
                self.MLmask = np.add(self.MLmask, self.Mask[:,:,selected_index])
            
            self.intergrate_into_final_mask()
            
            self.add_rois_of_selected()
            
        else:
            self.intergrate_into_final_mask()
#            self.Mask_edit_viewItem.setImage(gray2rgb(self.MLtargetedImg))

    def add_rois_of_selected(self):
        """
        Using find_contours to get list of contour coordinates in the binary mask, and then generate polygon rois based on these coordinates.
        """
        Results = self.SelectCellGui.getResults()
        self.selected_cells_infor_dict = {}
        for selected_index in self.SelectCellGui.AllSelectedIndex:

            contours,_ = self.get_cell_polygon(Results['masks'][selected_index])
#            contours = find_contours(self.Mask[:,:,selected_index], 0.5) # Find iso-valued contours in a 2D array for a given level value.
                
            for n, contour in enumerate(contours):
                contour_coord_array = contours[n]
                #Swap columns
                contour_coord_array[:, 0], contour_coord_array[:, 1] = contour_coord_array[:, 1], contour_coord_array[:, 0].copy()
    
                #Down sample the coordinates otherwise it will be too dense.
                contour_coord_array_del = np.delete(contour_coord_array, np.arange(2, contour_coord_array.shape[0]-3, 2), 0)
                
                self.selected_cells_infor_dict['cell{}_ROIitem'.format(str(selected_index))] = \
                pg.PolyLineROI(positions=contour_coord_array_del, closed=True)
                
                self.Mask_edit_view.getView().addItem(self.selected_cells_infor_dict['cell{}_ROIitem'.format(str(selected_index))])
                
    def plt_CheckButton(self):
        """Update cell select figure if check box status changes"""
        allCheck = [self.plt_All_ShowCell,    self.plt_All_ShowMask,    self.plt_All_ShowBBox,    self.plt_All_ShowLabel,    self.plt_All_ShowCentre]
        allHigh  = [self.plt_Select_ShowCell, self.plt_Select_ShowMask, self.plt_Select_ShowBBox, self.plt_Select_ShowLabel, self.plt_Select_ShowCentre]
        stateAll  = []
        stateHigh = []
        for buttonAll, buttonhigh in zip(allCheck, allHigh):
            stateAll.append(buttonAll.checkState()>0)
            stateHigh.append(buttonhigh.checkState()>0)
        self.SelectCellGui.on_click_All(stateAll)
        self.SelectCellGui.on_click_High(stateHigh)
        self.SelectCellGui.DisplayImage()
            
        
    def MultiSelect_Fcn(self):        
        self.SelectCellGui.EnableMultiCellSelection = self.plt_Select_MultiSelect.checkState()>0
        
        
        

            
    def update_mask(self):
        """
        Regenerate the masks for MaskRCNN and free-hand added (in case they are changed), and show in imageview.
        
        !!!ISSUE: getLocalHandlePositions: moving handles changes the position read out, dragging roi as a whole doesn't.
        """
        
        # Binary mask from ML detection
        if len(self.SelectCellGui.AllSelectedIndex) > 0:
            # Delete items in dictionary that are not roi items
            roi_dict = self.selected_cells_infor_dict.copy()
            del_key_list=[]
            for key in roi_dict:
                print(key)
                if 'ROIitem' not in key:
                    del_key_list.append(key)
            for key in del_key_list:
                del roi_dict[key]
            
            self.MLmask = ProcessImage.ROIitem2Mask(roi_dict, mask_resolution = (self.MLtargetedImg.shape[0], self.MLtargetedImg.shape[1]))
        # Binary mask of added rois
        self.addedROIitemMask = ProcessImage.ROIitem2Mask(self.roi_list_freehandl_added, mask_resolution = (self.MLtargetedImg.shape[0], self.MLtargetedImg.shape[1]))
        
        self.intergrate_into_final_mask()
        
#        if type(self.roi_list_freehandl_added) is list:
#            for ROIitem in self.roi_list_freehandl_added:
#                
#                ROIitem.sigHoverEvent.connect(lambda: self.show_roi_detail(ROIitem))
#                
#        plt.figure()
#        plt.imshow(self.addedROIitemMask)
#        plt.show()
    # =============================================================================
    #     For free-hand rois
    # =============================================================================
    def enable_free_hand(self):
        if self.enable_modify_MLmask_button.isChecked():
            self.Mask_edit_view.enable_drawing(True)
        else:
            self.Mask_edit_view.enable_drawing(False)
        
        
    def add_freehand_roi(self, roi):
        # For drawwidget
        self.roi_list_freehandl_added.append(roi)           
    
    def clear_edit_roi(self):
        """
        Clean up all the free-hand rois.
        """
        
        for roi in self.roi_list_freehandl_added:
            self.Mask_edit_view.getView().removeItem(roi)
            
        self.roi_list_freehandl_added = []
        
        if len(self.selected_cells_infor_dict) > 0:
            # Remove all selected masks
            for roiItemkey in self.selected_cells_infor_dict:
                if 'ROIitem' in roiItemkey:
                    self.Mask_edit_view.getView().removeItem(self.selected_cells_infor_dict[roiItemkey])
            
        self.selected_cells_infor_dict = {}
        self.MLmask = np.zeros((self.MLtargetedImg.shape[0], self.MLtargetedImg.shape[1]))         
        self.intergrate_into_final_mask()

        
    def intergrate_into_final_mask(self):
        # Binary mask of added rois
        self.addedROIitemMask = ProcessImage.ROIitem2Mask(self.roi_list_freehandl_added, mask_resolution = (self.MLtargetedImg.shape[0], self.MLtargetedImg.shape[1]))
        #Display the RGB mask, ML mask plus free-hand added.
        self.Mask_edit_viewItem.setImage(gray2rgb(self.addedROIitemMask) * self.mask_color_multiplier + \
                                         gray2rgb(self.MLmask) * self.mask_color_multiplier + gray2rgb(self.MLtargetedImg))
        
        self.final_mask = self.MLmask + self.addedROIitemMask
        
        # In case the input image is 2048*2048, and it is resized to fit in MaskRCNN, need to convert back to original size for DMD tranformation.
        if self.final_mask.shape[0] != self.Rawimage.shape[0] or self.final_mask.shape[1] != self.Rawimage.shape[1]:
            self.final_mask = resize(self.final_mask,[self.Rawimage.shape[0],self.Rawimage.shape[1]],preserve_range=True).astype(self.final_mask.dtype) 
#        self.final_mask = np.where(self.final_mask <= 1, self.final_mask, int(1))
        
        plt.figure()
        plt.imshow(self.final_mask)
        plt.show()
            
    # =============================================================================
    # For DMD transformation and mask generation
    # =============================================================================
#    def generate_transformed_mask(self):
#        self.read_transformations_from_file()
##        self.transform_to_DMD_mask(laser = self.maskLaserComboBox.currentText(), dict_transformations = self.dict_transformations)
#        target_laser = self.maskLaserComboBox.currentText()
#        self.final_DMD_mask = self.finalmask_to_DMD_mask(laser = target_laser, dict_transformations = self.dict_transformations)
#        
#        plt.figure()
#        plt.imshow(self.final_DMD_mask)
#        plt.show()
    
    def emit_mask_contour(self):
        """Use find_contours to get a list of (n,2)-ndarrays consisting of n (row, column) coordinates along the contour,
           and then feed the list of signal:[list_of_rois, flag_fill_contour, contour_thickness, flag_invert_mode] to the 
           receive_mask_coordinates function in DMDWidget.
        """
        contours = find_contours(self.final_mask, 0.5)
        
        sig = [contours, self.fillContourButton.isChecked(), self.thicknessSpinBox.value(), self.invertMaskButton.isChecked()]
        
        self.signal_DMDcontour.emit(sig)
        
#    def emit_mask(self):
#        target_laser = self.maskLaserComboBox.currentText()
#        final_DMD_mask_dict = {}
#        final_DMD_mask_dict['camera-dmd-'+target_laser] = self.final_DMD_mask
#        
#        self.signal_DMDmask.emit(final_DMD_mask_dict)  

        
#    def read_transformations_from_file(self):    
#        try:
#            with open(r'M:\tnw\ist\do\projects\Neurophotonics\Brinkslab\People\Xin Meng\Code\Python_test\DMDManager\Registration\transformation.txt', 'r') as json_file:
#                self.dict_transformations = json.load(json_file)    
#        except:
#            print('No transformation could be loaded from previous registration run.')
#            return
    
    
#    def transform_to_DMD_mask(self, laser, dict_transformations, flag_fill_contour = True, contour_thickness = 1, flag_invert_mode = False, mask_resolution = (1024, 768)):
#        """
#        Get roi vertices from all roi items and perform the transformation, and then create the mask for DMD.
#        """
#        
#        #list of roi vertices each being (n,2) numpy array for added rois
#        if len(self.roi_list_freehandl_added) > 0:
#            self.addedROIitem_vertices = ProcessImage.ROIitem2Vertices(self.roi_list_freehandl_added)
#            #addedROIitem_vertices needs to be seperated to be inidividual (n,2) np.array
#                self.ROIitems_mask_transformed = ProcessImage.vertices_to_DMD_mask(self.addedROIitem_vertices, laser, dict_transformations, flag_fill_contour = True, contour_thickness = 1,\
#                                                                          flag_invert_mode = False, mask_resolution = (1024, 768))
#        
#        #Dictionary with (n,2) numpy array for clicked cells
#        if len(self.selected_cells_infor_dict) > 0:
#            #Convert dictionary to np.array
#            for roiItemkey in self.selected_cells_infor_dict:
#                #Each one is 'contours' from find_contour
#                if '_verts' in roiItemkey:
#                    self.selected_cells_infor_dict[roiItemkey]
#                    
#            self.MLitems_mask_transformed = ProcessImage.vertices_to_DMD_mask(self.selected_cells_infor_dict, laser, dict_transformations, flag_fill_contour = True, contour_thickness = 1,\
#                                                                      flag_invert_mode = False, mask_resolution = (1024, 768))
#        
#        if len(self.roi_list_freehandl_added) > 0:
#            self.final_DMD_mask = self.ROIitems_mask_transformed + self.MLitems_mask_transformed
#            self.final_DMD_mask[self.final_DMD_mask>1] = 1
#        else:
#            self.final_DMD_mask = self.MLitems_mask_transformed
#        
#        return self.final_DMD_mask
        
#    def finalmask_to_DMD_mask(self, laser, dict_transformations, flag_fill_contour = True, contour_thickness = 1, flag_invert_mode = False, mask_resolution = (1024, 768)):
#        """
#        Same goal as transform_to_DMD_mask, with input being the final binary mask and using find_contour to get all vertices and perform transformation,
#        and then coordinates to mask.
#        """
#
#        self.final_DMD_mask = ProcessImage.binarymask_to_DMD_mask(self.final_mask, laser, dict_transformations, flag_fill_contour = True, \
#                                                                  contour_thickness = 1, flag_invert_mode = False, mask_resolution = (1024, 768))
#         
#        return self.final_DMD_mask
    
    def closeEvent(self, event):
        QtWidgets.QApplication.quit()
        event.accept()
        
#    def apply_mask(self, image, mask, color, alpha=0.5):
#        """Apply the given mask to the image.
#        """
#        for c in range(3):
#            image[:, :, c] = np.where(mask == 1,
#                                      image[:, :, c] *
#                                      (1 - alpha) + alpha * color[c] * 255,
#                                      image[:, :, c])
#        return image
    #%%
#    @run_in_thread
    def cam_snap(self):
        """Get a image from camera"""
        self.cam = CamActuator()
        self.cam.initializeCamera()
        
        exposure_time = self.CamExposureBox.value()
        self.Rawimage = self.cam.SnapImage(exposure_time)
        self.cam.Exit()
        print('Snap finished')
        
        self.MLtargetedImg_raw = self.Rawimage.copy()
        
        self.MLtargetedImg = self.convert_for_MaskRCNN(self.MLtargetedImg_raw)
        
        self.show_raw_image(self.MLtargetedImg)

        self.addedROIitemMask = np.zeros((self.MLtargetedImg.shape[0], self.MLtargetedImg.shape[1]))
        self.MLmask = np.zeros((self.MLtargetedImg.shape[0], self.MLtargetedImg.shape[1]))
        
if __name__ == "__main__":
    def run_app():
        app = QtWidgets.QApplication(sys.argv)
        pg.setConfigOptions(imageAxisOrder='row-major')
        mainwin = MainGUI()
        mainwin.show()
        app.exec_()
    run_app()         
        
