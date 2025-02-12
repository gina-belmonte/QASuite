import os
import unittest
import QCLib
import math
from __main__ import vtk, qt, ctk, slicer
from makeROI import *
#import makeROI

#
# SNR
#

class SNR:
  def __init__(self, parent):
    parent.title = "SNR"
    parent.categories = ["QC"]
    parent.dependencies = []
    parent.contributors = ["Gina Belmonte(AOUS)"]
    parent.helpText = """
    Calculate SNR from 2 identic acquisition
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
    slicer.selfTests['SNR'] = self.runTest

  def runTest(self):
    tester = SNRTest()
    tester.runTest()

#
# qSNRWidget
#

class SNRWidget(makeROIWidget):
  def __init__(self, parent = None):
    makeROIWidget.__init__(self,parent)
    #QCLib.genericPanel.__init__(self,parent)

    self.SNRstats=None

    if not parent:
      self.setup()
      self.parent.show()

  def setup(self):
    makeROIWidget.setup(self)
    #QCLib.genericPanel.setup(self)

    applicationLogic = slicer.app.applicationLogic()
    selectionNode = applicationLogic.GetSelectionNode()
    selectionNode.SetReferenceActiveVolumeID(None)
    selectionNode.SetReferenceActiveLabelVolumeID(None)
    selectionNode.SetReferenceSecondaryVolumeID(None)
    applicationLogic.PropagateVolumeSelection(0)

    self.volumes.text = "Volumes"
    # #
    # # Second Volume collapsible button
    # #
    # parameterCollapsibleButton = ctk.ctkCollapsibleButton()
    # parameterCollapsibleButton.text = "Second Volume"
    # self.framelayout.addWidget(parameterCollapsibleButton)

    # # Layout within the dummy collapsible button
    # parametersFormLayout = qt.QFormLayout(parameterCollapsibleButton)

    #
    # second volume selector
    #
    self.secondSelector = slicer.qMRMLNodeComboBox()
    self.secondSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    #self.secondSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
    self.secondSelector.selectNodeUponCreation = False
    self.secondSelector.addEnabled = False
    self.secondSelector.removeEnabled = False
    self.secondSelector.noneEnabled = True
    self.secondSelector.editEnabled = False
    self.secondSelector.showHidden = False
    self.secondSelector.showChildNodeTypes = False
    self.secondSelector.setMRMLScene( slicer.mrmlScene )
    self.secondSelector.setToolTip( "Second Volume" )
    self.secondSelector.enabled=False
    self.volumes.layout().addRow("Second Volume: ", self.secondSelector)

    #
    # Statistics Table collapsible button
    #
    statsCollapsibleButton = ctk.ctkCollapsibleButton()
    statsCollapsibleButton.text = "SNR Table"
    self.framelayout.addWidget(statsCollapsibleButton)
    self.table=qt.QTableWidget(0,6)
    labels=['Slice','Count','Mean','SD','N','SNR']
    self.table.setHorizontalHeaderLabels(labels)
    self.table.verticalHeader().setVisible(False)
    self.ROIStats=None
    self.UpdateTable()

    statsCollapsibleButton.setLayout(qt.QVBoxLayout())
    statsCollapsibleButton.layout().addWidget(self.table)

    self.framelayout.removeWidget(self.applyButton)
    self.framelayout.addWidget(self.applyButton)

    # #
    # # Apply Button
    # #
    # self.applyButton = qt.QPushButton("Apply")
    # self.applyButton.toolTip = "Calculate SNR"
    # self.applyButton.enabled = False
    # self.framelayout.addWidget(self.applyButton)

    # connections
    #self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.masterSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectMaster)
    self.masterSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.secondSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectSecond)
    self.secondSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.table.connect('currentCellChanged(int,int,int,int)', self.cellChanged)

    # Add vertical spacer
    self.framelayout.addStretch(1)
    
    count = slicer.mrmlScene.GetNumberOfNodesByClass('vtkMRMLSliceCompositeNode')
    for n in xrange(count):
      compNode = slicer.mrmlScene.GetNthNodeByClass(n, 'vtkMRMLSliceCompositeNode')
      compNode.SetForegroundOpacity(0.5)

  def UpdateTable(self):
    if self.SNRstats:
      len=self.SNRstats.__len__()

      self.table.setRowCount(len)

      self.tblits=[]
      for m in range(len):
        n=6*m
        self.tblits.append(qt.QTableWidgetItem(str(self.SNRstats.keys()[m])))
        self.table.setItem(m,0,self.tblits[n])
        self.table.item(m,0).setFlags(33)

        statroi=self.SNRstats.values()[m]

        self.tblits.append(qt.QTableWidgetItem(str(statroi['count'])))
        self.table.setItem(m,1,self.tblits[n+1])
        self.table.item(m,1).setFlags(33)

        self.tblits.append(qt.QTableWidgetItem(str(statroi['mean'])))
        self.table.setItem(m,2,self.tblits[n+2])
        self.table.item(m,2).setFlags(33)

        self.tblits.append(qt.QTableWidgetItem(str(statroi['sd'])))
        self.table.setItem(m,3,self.tblits[n+3])
        self.table.item(m,3).setFlags(33)

        self.tblits.append(qt.QTableWidgetItem(str(statroi['N'])))
        self.table.setItem(m,4,self.tblits[n+4])
        self.table.item(m,4).setFlags(33)

        N=float(statroi['N'])
        if N>0:
          SNR=math.sqrt(2)*(float(statroi['mean'])/N)
        else:
          SNR=0
        self.tblits.append(qt.QTableWidgetItem(str(SNR)))
        self.table.setItem(m,5,self.tblits[n+5])
        self.table.item(m,5).setFlags(33)

    self.table.resizeColumnsToContents()

  def cleanup(self):
    pass

  def onSelect(self):
    self.applyButton.enabled = self.masterSelector.currentNode() and self.secondSelector.currentNode()

  def cellChanged(self,currentRow,currentColumn,previousRow,previousColumn):
    if currentRow>0:
      slnumt=self.table.item(currentRow,0).text()
      qu=QCLib.QCUtil()
      sn=qu.getSliceNode()

      if sn:
        try:
          slnum=int(slnumt)
          vol=self.masterSelector.currentNode()
          newoff=qu.getSliceOffsetFromIndex(slnum,vol)
          sn.SetSliceOffset(newoff)
        except:
          #sn.SetSliceOffset(orig)
          pass

  def onSelectSecond(self):
    applicationLogic = slicer.app.applicationLogic()
    selectionNode = applicationLogic.GetSelectionNode()
    master=self.masterSelector.currentNode()
    second=self.secondSelector.currentNode()
    self.volumeratioslider.enabled = False
    self.sliceslider.enabled=False
    if second:
      warnings = self.checkForVolumeWarnings(master,second)
      if warnings != "":
        self.errorDialog("Warning: %s" % warnings)
        self.secondSelector.setCurrentNode(None)
        selectionNode.SetReferenceSecondaryVolumeID(None)
      else:
        self.volumeratioslider.enabled = True
        self.sliceslider.enabled=True
        selectionNode.SetReferenceSecondaryVolumeID(self.secondSelector.currentNode().GetID())
    else:
      selectionNode.SetReferenceSecondaryVolumeID(None)
    applicationLogic.PropagateVolumeSelection(0)

  def onSelectMaster(self):
    makeROIWidget.onSelectMaster(self)

    applicationLogic = slicer.app.applicationLogic()
    selectionNode = applicationLogic.GetSelectionNode()
    master=self.masterSelector.currentNode()
    self.volumeratioslider.enabled = False
    self.sliceslider.enabled=False
    if master:
      self.secondSelector.enabled = True
      selectionNode.SetReferenceActiveVolumeID(self.masterSelector.currentNode().GetID())

      second=self.secondSelector.currentNode()
      if second:
        warnings = self.checkForVolumeWarnings(master,second)
        if warnings != "":
          self.errorDialog( "Warning: %s" % warnings )
          self.secondSelector.setCurrentNode(None)
          selectionNode.SetReferenceSecondaryVolumeID(None)
        else:
          self.volumeratioslider.enabled = True
          self.sliceslider.enabled=True
          selectionNode.SetReferenceSecondaryVolumeID(self.secondSelector.currentNode().GetID())
    else:
      selectionNode.SetReferenceActiveVolumeID(None)
      self.secondSelector.enabled = False

  def onApplyButton(self):
    makeROIWidget.onApplyButton(self)

    applicationLogic = slicer.app.applicationLogic()
    selectionNode = applicationLogic.GetSelectionNode()
    second=self.secondSelector.currentNode()
    warnings = self.checkForVolumeWarnings(self.master,second)

    if warnings != "":
      self.errorDialog( "Warning: %s" % warnings )
      self.secondSelector.setCurrentNode(None)
      selectionNode.SetReferenceSecondaryVolumeID(None)
      applicationLogic.PropagateVolumeSelection(0)
    else:
      selectionNode.SetReferenceActiveVolumeID(self.master.GetID())
      selectionNode.SetReferenceSecondaryVolumeID(second.GetID())
      applicationLogic.PropagateVolumeSelection(0)
      logic = SNRLogic()
      self.frame.enabled=False
      logic.run(self.master,second,self.merge)
      self.SNRstats=logic.SNRvalues
      self.UpdateTable()
      self.frame.enabled=True

#
# SNRLogic
#

class SNRLogic:
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget
  """
  def __init__(self):
    pass

  def hasImageData(self,volumeNode):
    """This is a dummy logic method that
    returns true if the passed in volume
    node has valid image data
    """
    if not volumeNode:
      print('no volume node')
      return False
    if volumeNode.GetImageData() == None:
      print('no image data')
      return False
    return True

  def run(self,firstVolume,secondVolume,labelVolume):
    """
    Calculate SNR
    """

    slicer.util.delayDisplay('Calculate SNR')

    self.first=firstVolume
    self.second=secondVolume
    self.label=labelVolume

    self.SNRvalues=self.getSNR()

    return True

  def getSNR(self):
    qu=QCLib.QCUtil()
    imfirst=self.first.GetImageData()
    imsecond=self.second.GetImageData()

    if imfirst.GetScalarTypeMin()>=0: #unsigned
      imfirst.SetScalarType(imfirst.GetScalarType()-1)

    if imsecond.GetScalarTypeMin()>=0: #unsigned
      imsecond.SetScalarType(imsecond.GetScalarType()-1)

    stat=qu.getROIstats(self.first,self.label)
    statfirst=stat.values()[0]

    mathv=vtk.vtkImageMathematics()
    mathv.SetInput1Data(imfirst)
    mathv.SetInput2Data(imsecond)
    mathv.SetOperationToSubtract()
    mathv.Update()

    imsub=mathv.GetOutput()

    if imsub.GetScalarTypeMin()>=0: #unsigned
      imsub.SetScalarType(imsub.GetScalarType()-1)

    stat=qu.getROIstatsIM(imsub,self.label.GetImageData())
    statsub=stat.values()[0]

    len=statfirst.__len__()

    SNRvalues={}
    for n in range(len):
      stat={}
      statfirstn=statfirst.values()[n]
      statsubn=statsub.values()[n]
      stat['count']=statfirstn['count']
      stat['mean']=statfirstn['mean']
      stat['sd']=statfirstn['sd']
      stat['N']=statsubn['sd']
      SNRvalues[statfirst.keys()[n]]=stat

    return SNRvalues
