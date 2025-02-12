import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import numpy

#
# CrossCorrCalculator
#

class CrossCorrCalculator(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Cross Correlation Calculator"
    self.parent.categories = ["Signals"]
    self.parent.dependencies = []
    self.parent.contributors = ["Gina Belmonte(AOUS)"]
    self.parent.helpText = """
    Calculate cross correlation for two arrays
    """
    self.parent.acknowledgementText = ""

#
# CrossCorrCalculatorWidget
#

class CrossCorrCalculatorWidget(ScriptedLoadableModuleWidget):

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    #
    # Array selector 1
    #
    self.ArraySelector1 = slicer.qMRMLNodeComboBox()
    self.ArraySelector1.nodeTypes = ( ("vtkMRMLDoubleArrayNode"), "" )
    self.ArraySelector1.selectNodeUponCreation = False
    self.ArraySelector1.addEnabled = False
    self.ArraySelector1.removeEnabled = True
    self.ArraySelector1.noneEnabled = True
    self.ArraySelector1.showHidden = False
    self.ArraySelector1.showChildNodeTypes = False
    self.ArraySelector1.setMRMLScene( slicer.mrmlScene )
    self.ArraySelector1.setToolTip( "Array for analysis" )
    parametersFormLayout.addRow("First function: ", self.ArraySelector1)

    #
    # Array selector 2
    #
    self.ArraySelector2 = slicer.qMRMLNodeComboBox()
    self.ArraySelector2.nodeTypes = ( ("vtkMRMLDoubleArrayNode"), "" )
    self.ArraySelector2.selectNodeUponCreation = False
    self.ArraySelector2.addEnabled = False
    self.ArraySelector2.removeEnabled = True
    self.ArraySelector2.noneEnabled = True
    self.ArraySelector2.showHidden = False
    self.ArraySelector2.showChildNodeTypes = False
    self.ArraySelector2.setMRMLScene( slicer.mrmlScene )
    self.ArraySelector2.setToolTip( "Array for analysis" )
    parametersFormLayout.addRow("Second function: ", self.ArraySelector2)

    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.toolTip = "Run the algorithm."
    self.applyButton.enabled = False
    parametersFormLayout.addRow(self.applyButton)

    #
    # Results Area
    #
    resultsCollapsibleButton = ctk.ctkCollapsibleButton()
    resultsCollapsibleButton.text = "Results"
    self.layout.addWidget(resultsCollapsibleButton)

    # Layout within the dummy collapsible button
    resultsFormLayout = qt.QFormLayout(resultsCollapsibleButton)
    
    #
    # delay value
    #
    self.delaySW = ctk.ctkSliderWidget()
    self.delaySW.singleStep = 1
    self.delaySW.minimum = 0
    self.delaySW.maximum = 0
    self.delaySW.value = 0
    self.delaySW.setToolTip("The delay for cross corralation")
    self.delaySW.enabled=False
    resultsFormLayout.addRow("Delay", self.delaySW)

    #
    # result value
    #
    self.resultLE=qt.QLineEdit()
    self.resultLE.readOnly=True
    self.resultLE.text=""
    resultsFormLayout.addRow("CC Value: ",self.resultLE)

    #
    # GOTO MAX Button
    #
    self.gomaxButton = qt.QPushButton("Go to Max")
    self.gomaxButton.toolTip = "Goto the maximum"
    #self.gomaxButton.enabled = False
    resultsFormLayout.addRow(self.gomaxButton)

    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.gomaxButton.connect('clicked(bool)', self.onGomaxButton)
    self.ArraySelector1.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.ArraySelector2.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.delaySW.connect("valueChanged(double)",self.getCC)

    # Add vertical spacer
    self.layout.addStretch(1)

    # Refresh Apply button state
    self.onSelect()

  def cleanup(self):
    pass

  def onGomaxButton(self):
    ar1=self.ArraySelector1.currentNode()
    ar2=self.ArraySelector2.currentNode()

    name="cc-"+ar1.GetName()+"-"+ar2.GetName()

    arrayNode = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLDoubleArrayNode",name).GetItemAsObject(0)

    if arrayNode:
      ar = numpy.asarray(arrayNode.GetArray())
      delayM=ar[numpy.argmax(ar[:,1]),0]
      self.delaySW.value=delayM
      

  def getCC(self,delay):
    ar1=self.ArraySelector1.currentNode()
    ar2=self.ArraySelector2.currentNode()

    name="cc-"+ar1.GetName()+"-"+ar2.GetName()

    arrayNode = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLDoubleArrayNode",name).GetItemAsObject(0)

    if arrayNode:
      arrayD = arrayNode.GetArray()
      self.resultLE.text=str(arrayD.GetComponent(int(delay)-int((1-arrayD.GetNumberOfTuples())/2),1))
    else:
      self.resultLE.text=""

  def onSelect(self):
    ar1=self.ArraySelector1.currentNode()
    ar2=self.ArraySelector2.currentNode()
    self.resultLE.text=""
    validT = ar1 and ar2
    self.applyButton.enabled = validT

    self.delaySW.enabled = False
    self.delaySW.minimum = 0
    self.delaySW.maximum = 0
    self.delaySW.value=0

  def onApplyButton(self):
    ar1=self.ArraySelector1.currentNode()
    ar2=self.ArraySelector2.currentNode()
    logic = CrossCorrCalculatorLogic(ar1,ar2)
    cc=logic.run()

    name="cc-"+ar1.GetName()+"-"+ar2.GetName()
    ntuple=len(cc)
    arrayNode = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLDoubleArrayNode",name).GetItemAsObject(0)

    if not arrayNode:
      arrayNode = slicer.mrmlScene.AddNode(slicer.vtkMRMLDoubleArrayNode())
      arrayNode.SetName(name)

    arrayD = arrayNode.GetArray()

    arrayD.SetNumberOfComponents(2)
    arrayD.SetNumberOfTuples(ntuple)
    
    for n in range(ntuple):
      #arrayD.SetComponent(n, 0, n+1-ar2.GetSize())
      arrayD.SetComponent(n, 0, n+int((1-ntuple)/2))
      arrayD.SetComponent(n, 1, cc[n])


    self.delaySW.enabled = True
    self.delaySW.minimum = -ntuple+1
    self.delaySW.maximum = ntuple-1
    self.delaySW.value=0

    self.getCC(self.delaySW.value)

#
# CrossCorrCalculatorLogic
#

class CrossCorrCalculatorLogic(ScriptedLoadableModuleLogic):

  #cc=sum_i[(x(i+d)-xbar)(y(i)-ybar)]/sqrt(sum_i[(x(i+d)-xbar)^2]sum_i[(y(i)-ybar)^2])

  #TODO: den does not consider delay yet

  def __init__(self, ar1, ar2):
    array1=numpy.asarray(ar1.GetArray())[:,1]
    array2=numpy.asarray(ar2.GetArray())[:,1]
    x1=numpy.asarray(ar1.GetArray())[:,0]
    x2=numpy.asarray(ar2.GetArray())[:,0]

    Xnt=numpy.concatenate((x1,x2))
    Xnt.sort()
    Xn=numpy.unique(Xnt)
    self.array1=numpy.interp(Xn,x1,array1,left=0,right=0)
    self.array2=numpy.interp(Xn,x2,array2,left=0,right=0)
    
    #test da cancellare
    lnmx=Xn.size
    arrayNode = slicer.mrmlScene.AddNode(slicer.vtkMRMLDoubleArrayNode())
    arrayNode.SetName(ar1.GetName() + "-nr")
    arrayD = arrayNode.GetArray()
    arrayD.SetNumberOfComponents(2)
    arrayD.SetNumberOfTuples(lnmx)
    for n in range(lnmx):
      arrayD.SetComponent(n, 0, Xn[0]+n)
      arrayD.SetComponent(n, 1, self.array1[n])

    arrayNode = slicer.mrmlScene.AddNode(slicer.vtkMRMLDoubleArrayNode())
    arrayNode.SetName(ar2.GetName() + "-nr")
    arrayD = arrayNode.GetArray()
    arrayD.SetNumberOfComponents(2)
    arrayD.SetNumberOfTuples(lnmx)
    for n in range(lnmx):
      arrayD.SetComponent(n, 0, Xn[0]+n)
      arrayD.SetComponent(n, 1, self.array2[n])

  def run(self):
    adm1=self.array1-numpy.mean(self.array1)
    adm2=self.array2-numpy.mean(self.array2)
    den=numpy.sqrt(numpy.sum(numpy.square(adm1))*numpy.sum(numpy.square(adm2)))
    cc=numpy.correlate(adm1,adm2,"full")
    return cc/den
