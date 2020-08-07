# -*- coding: utf-8 -*-
"""
Created on Wed Jul 22 20:31:41 2020

@author: meppenga
"""

 
import numpy as np

import os
from skimage.measure import find_contours
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.patches import Polygon
import skimage.io
import random
import colorsys
from matplotlib.widgets import CheckButtons, Button
from MaskRCNN.Engine.MaskRCNN import MaskRCNN as modellib
from MaskRCNN.Miscellaneous.utils import ConvertImage2RGB

try:
    import Tkinter as tk
    from Tkinter.filedialog import askopenfilename
except:
    import tkinter as tk
    from tkinter.filedialog import askopenfilename

class CellGui(object):
    
    def __init__(self,config):
        self.config = config
        # Create MaskRCNN model
        self.Predictor = modellib(self.config, 'inference', model_dir=self.config.LogDir)
        self.Predictor.compileModel()
        
        self.Predictor.LoadWeigths(self.config.WeigthPath, by_name=True)
        
        # Create Figure
        self.fig_size = (20,10)
        self.CreateFigure()
        self.HighlightColor = (0.0, 1.0, 0.0)
        
        self.NumCells = 0
        self.Radius = 3
        
    def getSelectedCellAtributes(self):
        if self.NumCells == 0:
            raise Exception('No cell instances, thus no selected cell results')
        class_names = ['BG'] + self.config.ValidLabels
        Result = {'rois':          self.Results['rois'][self.SelectedCellIndex],
                  'mask':          self.Results['masks'][:,:,self.SelectedCellIndex],
                  'class_ids':     self.Results['class_ids'][self.SelectedCellIndex],
                  'Centre_coor':   self.Results['Centre_coor'][self.SelectedCellIndex],
                  'Centre_coor x': self.Results['Centre_coor'][self.SelectedCellIndex][1],
                  'Centre_coor y': self.Results['Centre_coor'][self.SelectedCellIndex][0],
                  'Label':         class_names[self.Results['class_ids'][self.SelectedCellIndex]],
                  'Image':         self.Image,
                  'Index':         self.SelectedCellIndex}
        return Result
    
    def getAllResults(self, event):
        return self.Results, self.getSelectedCellAtributes()
    
    def ChangeWeighs(self, file):
        self.config.WeigthPath =file
        self.Predictor.LoadWeigths(self.config.WeigthPath, by_name=True)
        
    def CreateFigure(self):
        plt.close('Select Cell GUI')
        self.fig, self.ax = plt.subplots(1, figsize=self.fig_size, num='Select Cell GUI')
        self.ax.axis('off')
        self.fig.text(0,0.01,'Brinks lab\nAuthor: Martijn Eppenga\nTensorFlow version: '+self.Predictor.TF_Version+'\n') #
        self.fig_msg = self.fig.text(0,0.01,'Status: ')
        
        # Create Buttons axis
        self.Button_All_Label  = ['Show Cells','Show Mask','Show BBox','Show Label','Show centre']
        self.Button_High_Label = ['Show Mask', 'Show BBox','Show Label','Show centre']
        self.fig.subplots_adjust(right = 0.8)
        self.Ax_Button_All  = self.fig.add_axes([0.81, 0.71, 0.1, 0.2])
        self.Ax_Button_High = self.fig.add_axes([0.81, 0.41, 0.1, 0.2])
        self.Ax_Button_Get  = self.fig.add_axes([0.81, 0.21, 0.1, 0.075])
        self.Ax_Button_File = self.fig.add_axes([0.81, 0.11, 0.1, 0.075])
        
        # Create buttons
        self.Button_All     = CheckButtons(self.Ax_Button_All,   self.Button_All_Label)
        self.Button_High    = CheckButtons(self.Ax_Button_High, self.Button_High_Label)
        self.Button_Get     = Button(self.Ax_Button_Get, 'Get results')
        self.Button_File    = Button(self.Ax_Button_File,'Change file')

        
        # Set button text
        self.Ax_Button_All.text(0.4, 1,'All cells')
        self.Ax_Button_High.text(0.3, 1,'Selected cell')
        
        # Init button state
        self.Button_All.set_active(0)
        for ii in range(4):
            # set all active
            self.Button_High.set_active(ii)
        # Deactivate label
        self.Button_High.set_active(2)
            
        
        # Create state dicts
        self.Display_All_State = {}
        for label, state in zip(self.Button_All_Label, self.Button_All.get_status()):
            self.Display_All_State[label] = state
        self.Display_High_State = {self.Button_All_Label[0]: True}
        for label, state in zip(self.Button_High_Label, self.Button_High.get_status()):
            self.Display_High_State[label] = state
            
        # Bind CallBacks
        self.Button_All.on_clicked(self.on_click_All)
        self.Button_High.on_clicked(self.on_click_High)
        self.Button_Get.on_clicked(self.getAllResults)
        self.Button_File.on_clicked(self.ChangeFile)


               
        # Add mouse click callback
        self.fig.canvas.mpl_connect('button_press_event', self.on_Mouse_Click)
        # Add close callback:
        self.fig.canvas.mpl_connect('close_event', self.close_fcn)
        self.fig.show()
        self.UpdateFigure()
    
    def close_fcn(self,event):
        pass
        
    def on_click_All(self, label):
        """Callback which updates the figure when a checkbox setting is changed"""
        for idx, state in enumerate(self.Button_All.get_status()):
            self.Display_All_State[self.Button_All_Label[idx]] = state
        self.DisplayImage()
    
    def on_click_High(self, label):
        """Callback which updates the figure when a checkbox setting is changed"""
        for idx, state in enumerate(self.Button_High.get_status()):
            self.Display_High_State[self.Button_High_Label[idx]] = state
        self.DisplayImage()
    
    def on_Mouse_Click(self,event):
        """Callback which searches for a cell at the location in the figure where
        the user have clicked with his mouse.
        If a new cell is selected it will update the figure"""
        try:
            self.Results['masks'][0,0,0]
        except:
            print('No detection results found')
            return
        if self.NumCells > 0:
            if event.xdata == None or event.ydata == None:
                # ensure click is inside figure
                return
            elif event.xdata < 1.01 or event.ydata < 1.01:
                # ensure click is inside figure (not inside checkbox)
                return
            self.indexPrev = self.SelectedCellIndex + 0 # +0 to make copy
            ShapeMask      = np.shape(self.Results['masks'])
            
            # get coorinates at selected location in image coordinates            
            xcoor = min(max(int(event.xdata),0),ShapeMask[1])
            ycoor = min(max(int(event.ydata),0),ShapeMask[0])
            for ii in range(self.NumCells):
                # find selected cell
                if self.Results['masks'][ycoor,xcoor,ii]:
                    self.SelectedCellIndex = ii
                    break
            if self.SelectedCellIndex  != self.indexPrev:
                # Update figure if a new cell is selected
                self.patches[self.SelectedCellIndex] = self._CreateImageAtributes(self.SelectedCellIndex, self.HighlightColor)
                self.patches[self.indexPrev]         = self._CreateImageAtributes(self.indexPrev, self.Colors[self.indexPrev])            
                self.DisplayImage()
    
    def ChangeFile(self,event):
        """Callback which opens a file selection GUI. A detection will run on
        the selected file and the results will be displayed in the figure"""
        obj = tk.Tk()
        filename = askopenfilename(filetypes = (("png files","*.png"),("jpeg files","*.jpg"),('tiff files','*.tif'),("all files","*.*"))) 
        obj.destroy()
        if filename:
            self.RunDetection(filename)

    def CreateTitle(self):
        """Sets the title of the main figure"""
        class_names = ['BG'] + self.config.ValidLabels
        title = "Selected Cell: {} {:.3f}\n Centre: y = {:3d}, x = {:3d}".format(
            class_names[self.Results['class_ids'][self.SelectedCellIndex]],
            self.Results['scores'][self.SelectedCellIndex],
            self.Results['Centre_coor'][self.SelectedCellIndex][0],
            self.Results['Centre_coor'][self.SelectedCellIndex][1])
        self.ax.set_title(title)
    
    def RunDetection(self,Image):
        """Runs a detection on an image
        Input:
            Image: str or array. If a string is given as input, then the function
                assumes that it is a file path. It will load the image and run 
                the detection on the image.
                If an array is given it is assuemd that the array is the image 
                and it will run the detection on the image"""
        # Check input
        if isinstance(Image, str):
            # Load image
            if not os.path.isfile(Image):
                return
            Image = skimage.io.imread(Image)
        self.Text_ChangeStatus('Run detection')
        # Perapre image for detection
        Image = ConvertImage2RGB(Image)
        self.Image = Image
        # Run detection
        self.Results = self.Predictor.detect([Image])[0]
        self.Text_ChangeStatus('Run detection done')
        self.NumCells = len(self.Results['class_ids'])
        self.SelectedCellIndex = 0
        self.indexPrev         = 0
        # Create and display figure
        self.CreateImage()
        self.patches[self.SelectedCellIndex] = self._CreateImageAtributes(self.SelectedCellIndex, self.HighlightColor)
        self.DisplayImage()
        
            
            
            
    def CreateImage(self):
        """Creates all atributes to display within the main figure"""
        if self.NumCells == 0:
            print("\n*** No instances to display *** \n")
            return
        self.Text_ChangeStatus('Create figure')
        self.Colors = self.random_colors(self.NumCells)
        self.patches = []
        for idx in range(self.NumCells):
            self.patches.append(self._CreateImageAtributes(idx,self.Colors[idx]))
        self.Text_ChangeStatus('Create figure done')
            
        
            
        
    def _CreateImageAtributes(self,Index,color): 
        """Create the atributes for a single cell
        Input:
            Index: int index coresponding to the cell for which the atributes are
                created (with respect to self.Results
             color: tuple (R,G,B) [0-1]: color to assign to each atribute"""
        if self.NumCells == 0:
            return [None,None,None,None,None,False]
        Mask        = self.Results['masks'][:,:,Index]
        Box         = self.Results['rois'][Index]
        score       = self.Results['scores'][Index]
        class_id    = self.Results['class_ids'][Index]
        class_names = ['BG'] + self.config.ValidLabels
        CCoor       = self.Results['Centre_coor'][Index]

        if not np.any(Box):
            return [None,None,None,None,None,False]
        
        y1, x1, y2, x2 = Box
        BoxPatches = patches.Rectangle((x1, y1), x2 - x1, y2 - y1, linewidth=2,
                            alpha=0.7, linestyle="dashed",
                            edgecolor=color, facecolor='none')
        CCoorPatches = patches.Circle(np.flipud(CCoor),radius=self.Radius, color='y')

        label   = class_names[class_id]
        caption = "{} {:.3f}".format(label, score) if score else label

            # padded image to create nice contour 
        padded_mask = np.zeros(
                (Mask.shape[0] + 2, Mask.shape[1] + 2), dtype=np.uint8)
        padded_mask[1:-1, 1:-1] = Mask
        contours = find_contours(padded_mask, 0.5)
        vertsPatch = []
        for verts in contours:
            # Subtract the padding and flip (y, x) to (x, y)
            verts = np.fliplr(verts) - 1
            p = Polygon(verts, facecolor="none", edgecolor=color)
            vertsPatch.append(p)
        return [BoxPatches,caption,vertsPatch,Box,CCoorPatches,True]
    
    def DisplayImage(self):
        """Displays the main image in the figure"""
        Masked_Image = self.Image.copy()
        if self.NumCells == 0:
            self.ax.imshow(Masked_Image.astype(self.Image.dtype))
            self.Text_ChangeStatus('Display image done')
            self.UpdateFigure()
            return
        self.Text_ChangeStatus('Display image')
        #Clear axis and set border limits +10 pixels for nice view
        self.ax.clear()
        height, width = self.Image.shape[:2]
        self.ax.set_ylim(height + 10, -10)
        self.ax.set_xlim(-10, width + 10)
        self.ax.axis('off')
        for index, atribute in enumerate(self.patches):
            if index == self.SelectedCellIndex:
                CheckBoxSatus = self.Display_High_State
                color = self.HighlightColor
            else:
                CheckBoxSatus = self.Display_All_State
                color = self.Colors[index]
            if CheckBoxSatus['Show Cells']:
                for patch_ in atribute[2]:
                    self.ax.add_patch(patch_) 
            else:
                continue
            if CheckBoxSatus['Show Mask']:
                # Masked_Image = self.apply_mask(Masked_Image, self.Results['masks'][:,:,index], color)
                Masked_Image = self.apply_mask_Fast(Masked_Image, self.Results['masks'][:,:,index], atribute[3], color)
            if CheckBoxSatus['Show BBox']:
                self.ax.add_patch(atribute[0])
            if CheckBoxSatus['Show Label']:
                y1, x1, y2, x2 = atribute[3]
                self.ax.text(x1, y1 + 8, atribute[1],
                        color='w', size=11, backgroundcolor="none")
            if CheckBoxSatus['Show centre']:
                self.ax.add_patch(atribute[4])
        self.ax.imshow(Masked_Image.astype(self.Image.dtype)) 
        self.CreateTitle()
        self.Text_ChangeStatus('Display image done')
        self.UpdateFigure()
        
    def Text_ChangeStatus(self,msg):
        """Updates the satus message
        Input: str, message to display"""
        self.fig_msg.set_text('Status: '+msg)
        self.UpdateFigure()
        

    def UpdateFigure(self):   
        """Update figure, can be used to force matplotlib to immediately update
        the figure"""
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()         

        
        
    
  
    def random_colors(self,N, bright=True):
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
    
    def apply_mask(self,image, mask, color, alpha=0.5):
        """Apply the given mask to the image.
        """
        for c in range(3):
            image[:, :, c] = np.where(mask,
                                      image[:, :, c] *
                                      (1 - alpha) + alpha * color[c] * 255,
                                      image[:, :, c])
        return image
        
    def apply_mask_Fast(self,image, mask, bbox, color, alpha=0.5):
        """Apply the given mask to the image.
        This method is a speed up of the apply_mask method
        By using the bounding boxes one can filter out many zero calculations
        Specially powerful for large images with small cells
        """
        # Get bbox indices and padded it one pixel to ensure proper mask generation
        shape = np.shape(image)
        y1, x1, y2, x2 = bbox
        y1 = int(max(0,y1-1))
        x1 = int(max(0,x1-1))
        y2 = int(min(shape[0],y2+1))
        x2 = int(min(shape[1],x2+1))
        # Get relevant part of the mask array
        mask = mask[y1:y2, x1:x2]
        # Apply mask
        for c in range(3):
            temp = image[y1:y2, x1:x2, c]
            temp[mask] = (temp[mask] * (1 - alpha) + alpha * color[c] * 255).astype(image.dtype)
            image[y1:y2, x1:x2, c] = temp
        return image
        

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    