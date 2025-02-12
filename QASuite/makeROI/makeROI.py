import os
import unittest
from __main__ import vtk, qt, ctk, slicer
import QCLib
#import plugins
from ErodeImage import *

#
# makeROI
#

class makeROI:
  def __init__(self, parent):
    parent.title = "Make ROI for uniformity tests"
    parent.categories = ["QC.Process"]
    parent.dependencies = []
    parent.contributors = ["Gina Belmonte (AOUS)"]
    parent.helpText = """
    Make a ROI for uniformity e SNR QC controls.
    """
    parent.acknowledgementText = ""

    self.parent = parent

    # Add this test to the SelfTest module's list for discovery when the module
    # is created.  Since this module may be discovered before SelfTests itself,
    # create the list if it doesn't already exist.
    try:
      slicer.selfTests
    except AttributeError:
      slicer.selfTests = {}
    slicer.selfTests['makeROI'] = self.runTest

  def runTest(self):
    tester = makeROITest()
    tester.runTest()

#
# qmakeROIWidget
#

class makeROIWidget (QCLib.genericPanel):
  def __init__(self, parent = None):
    self.master=None
    #super(makeROIWidget,self).__init__(parent)
    QCLib.genericPanel.__init__(self,parent)
    self.qu=QCLib.QCUtil()
    self.master=None
    self.merge=None
    self.suffixMergeName="-label"

    if not parent:
      self.setup()
      self.parent.show()

  def setup(self):
    #super(makeROIWidget,self).setup()
    QCLib.genericPanel.setup(self)

    applicationLogic = slicer.app.applicationLogic()
    selectionNode = applicationLogic.GetSelectionNode()
    selectionNode.SetReferenceActiveVolumeID(None)
    selectionNode.SetReferenceActiveLabelVolumeID(None)
    selectionNode.SetReferenceSecondaryVolumeID(None)
    applicationLogic.PropagateVolumeSelection(0)

    self.masterWhenMergeWasSet = None

    self.label = ctk.ctkCollapsibleButton(self.frame)
    self.label.setText("ROI")
    self.framelayout.addWidget(self.label)

    parametersFormLayout=qt.QFormLayout(self.label)

    #
    # Volume of ROI in master percentage
    #
    self.volumeratioslider = ctk.ctkSliderWidget()
    self.volumeratioslider.singleStep = 1.0
    self.volumeratioslider.minimum = 0.0
    self.volumeratioslider.maximum = 100.0
    self.volumeratioslider.value = 80.0
    self.volumeratioslider.enabled = False
    self.volumeratioslider.setToolTip("Set ROI volume as percentage of master volume")
    parametersFormLayout.addRow("ROI Area Percentage", self.volumeratioslider)

    self.sliceslider = slicer.qMRMLSliceControllerWidget()
    self.sliceslider.enabled=False
    parametersFormLayout.addRow("Slice for Area Ratio", self.sliceslider)

    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.toolTip = "Create a ROI for QC"
    self.applyButton.enabled = False
    #parametersFormLayout.addRow(self.applyButton)
    self.framelayout.addWidget(self.applyButton)

    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.masterSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectMaster)
    self.masterSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    #self.labelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)

    # Add vertical spacer
    self.framelayout.addStretch(1)

  def cleanup(self):
    pass

  def onSelect(self):
    self.applyButton.enabled = self.masterSelector.currentNode()

  def onSelectMaster(self):
    self.master = self.masterSelector.currentNode()
    merge=None

    self.volumeratioslider.enabled = False
    self.sliceslider.enabled=False
    #-----mergeVolume()
    if self.master:
      self.volumeratioslider.enabled = True

      masterName = self.master.GetName()
      mergeName = masterName+self.suffixMergeName

      # if we already have a merge and the master hasn't changed, use it
      if self.merge and self.master == self.masterWhenMergeWasSet:
        mergeNode = slicer.mrmlScene.GetNodeByID(self.merge.GetID())
        if mergeNode and mergeNode !="":
          merge=self.merge

      if not merge:
        self.masterWhenMergeWasSet = None

        # otherwise pick the merge based on the master name
        # - either return the merge volume or empty string
        merge = self.getNodeByName(mergeName)
        self.merge=merge
        #-----

      if merge:
        if merge.GetClassName() != "vtkMRMLLabelMapVolumeNode":
          self.errorDialog("Error: selected merge label volume is not a label volume " + merge.GetClassName())
        else:
          warnings = self.checkForVolumeWarnings(self.master,self.merge)
          if warnings != "":
            self.errorDialog( "Warning: %s" % warnings )
          else:
            # make the source node the active background, and the label node the active label
            applicationLogic = slicer.app.applicationLogic()
            selectionNode = applicationLogic.GetSelectionNode()
            selectionNode.SetReferenceActiveVolumeID(self.master.GetID())
            selectionNode.SetReferenceActiveLabelVolumeID(merge.GetID())
            applicationLogic.PropagateVolumeSelection(0)
            self.merge = merge

            sn=self.qu.getSliceNode()
            if sn:
              self.sliceslider.setMRMLSliceNode(sn)
              self.sliceslider.enabled=True
            else:
              self.sliceslider.enabled=False
      else:
        # the master exists, but there is no merge volume yet
        volumesLogic = slicer.modules.volumes.logic()
        merge = volumesLogic.CreateAndAddLabelVolume(slicer.mrmlScene, self.master, mergeName)
        coln=slicer.vtkMRMLColorTableNode()
        coln.SetTypeToUser()
        coln.SetNumberOfColors(2)
        coln.SetColor(0,'bg',0,0,0)
        coln.SetColor(1,'fg',1,0,0)
        coln.SetOpacity(0,0)
        coln.SetOpacity(1,1)
        slicer.mrmlScene.AddNode(coln)
        merge.GetDisplayNode().SetAndObserveColorNodeID(coln.GetID())
        self.merge = merge
        self.masterWhenMergeWasSet = self.master
        #self.labelSelector.setCurrentNode(self.merge)
        self.onSelectMaster()

  def getNodeByName(self, name):
    """get the first MRML node that has the given name
    - use a regular expression to match names post-pended with numbers"""

    slicer.mrmlScene.InitTraversal()
    node = slicer.mrmlScene.GetNextNode()
    while node:
      try:
        nodeName = node.GetName()
        if nodeName.find(name) == 0:
          # prefix matches, is the rest all numbers?
          if nodeName == name or nodeName[len(name):].isdigit():
            return node
      except:
        pass
      node = slicer.mrmlScene.GetNextNode()
    return None
    
  def onApplyButton(self):
    applicationLogic = slicer.app.applicationLogic()
    selectionNode = applicationLogic.GetSelectionNode()
    selectionNode.SetReferenceActiveVolumeID(self.master.GetID())
    selectionNode.SetReferenceActiveLabelVolumeID(self.merge.GetID())
    applicationLogic.PropagateVolumeSelection(0)
    logic=ErodeImageLogic()
    connectivity=2
    newROI=True
    iterations=1
    self.frame.enabled=False
    logic.run(self.master, self.merge, 1, iterations, connectivity, newROI)
    
    sn=self.qu.getSliceNode()
    if sn:
      newROI=False
      ratio=self.volumeratioslider.value
      idx=self.qu.getSliceIndexFromOffset(sn.GetSliceOffset(),self.master)
      area0=self.qu.getSliceArea(self.master,idx,self.qu.getVolumeMin(self.master))
      area1=self.qu.getSliceArea(self.merge,idx,self.qu.getVolumeMin(self.merge))
      erod=1-(ratio/100)
      rne=erod*area0/(area0-area1)
      #r0=math.sqrt(area0/math.pi)
      #r1=math.sqrt(area1/math.pi)
      #rne=int(math.sqrt(ratio/100)/(1-(r1/r0)))
      print("rne "+ str(rne))
      #print("area 0 1 " + str(area0) + " " + str(area1))
      logic.run(self.master, self.merge, int(rne-1), iterations, connectivity, newROI)
      self.frame.enabled=True
