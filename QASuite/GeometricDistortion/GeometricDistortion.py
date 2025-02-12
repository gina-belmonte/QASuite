import os
import unittest
import time
import math
from __main__ import vtk, qt, ctk, slicer
from makeROI import *
import vtkITK

#
# GeometricDistortion
#

class GeometricDistortion:
  def __init__(self, parent):
    parent.title = "Geometric Distortion (Philips Phantom)"
    parent.categories = ["QC"]
    parent.dependencies = []
    parent.contributors = ["Gina Belmonte(AOUS)"]
    parent.helpText = """
    Estimate the geometric distortion percentage using rods slice in the Philips MR Phantom
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
    slicer.selfTests['GeometricDistortion'] = self.runTest

  def runTest(self):
    tester = GeometricDistortionTest()
    tester.runTest()

#
# qGeometricDistortionWidget
#

class GeometricDistortionWidget  (makeROIWidget):
  def __init__(self, parent = None):
    makeROIWidget.__init__(self,parent)
    self.suffixMergeName="-Rods"
    self.sides=None
    self.diagonals=None

    if not parent:
      self.setup()
      self.parent.show()

  def setup(self):
    QCLib.genericPanel.setup(self)

    self.label = ctk.ctkCollapsibleButton(self.frame)
    self.label.setText("ROI")
    self.framelayout.addWidget(self.label)

    parametersFormLayout=qt.QFormLayout(self.label)

    self.overrideROI = ctk.ctkCheckBox()
    self.overrideROI.setText('Override ROI if exists')
    self.overrideROI.enabled=False
    self.overrideROI.checked=True
    parametersFormLayout.addRow(self.overrideROI)

    self.sliceslider = slicer.qMRMLSliceControllerWidget()
    self.sliceslider.enabled=False
    parametersFormLayout.addRow("Rods Slice", self.sliceslider)

    self.autothr = ctk.ctkCheckBox()
    self.autothr.setText('Automatic Threashold Range')
    self.autothr.enabled=False
    self.autothr.checked=True
    parametersFormLayout.addRow(self.autothr)

    self.thr = ctk.ctkRangeWidget()
    self.thr.decimals = 0
    self.thr.minimum = 0
    self.thr.maximum = 0
    self.thr.enabled = False
    parametersFormLayout.addRow("Threashold Range",self.thr)

    self.dgp = ctk.ctkCollapsibleButton(self.frame)
    self.dgp.setText("GDP (Double Click a row to chart measured distances)")
    self.dgp.enabled=False
    self.framelayout.addWidget(self.dgp)
    self.dgp.setLayout(qt.QVBoxLayout())

    self.chartButton = qt.QPushButton("Chart")
    self.chartButton.toolTip = "Chart distances frequency"
    self.chartButton.enabled=False
    self.dgp.layout().addWidget(self.chartButton)

    self.resultTable=qt.QTableWidget(2,5)
    #self.resultTable=qt.QTableView()

    labels=['','Minimum(mm)','GDP(%) of Minumum','Maximum(mm)','GDP(%) of Maximum']
    self.resultTable.setHorizontalHeaderLabels(labels)
    self.resultTable.verticalHeader().setVisible(False)
    self.items=[]
    self.items.append(qt.QTableWidgetItem('Side'))
    self.items.append(qt.QTableWidgetItem('Diagonal'))
    
    self.resultTable.setItem(0,0,self.items[0])
    self.resultTable.setItem(1,0,self.items[1])

    for n in range(8):
      self.items.append(qt.QTableWidgetItem())
      self.resultTable.setItem(n/4,(n%4)+1,self.items[n+2])

    for n in range(len(self.items)):
      self.items[n].setFlags(33)

    self.resultTable.resizeColumnsToContents()
    
    self.dgp.layout().addWidget(self.resultTable)

    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.toolTip = "Estimate GDP."
    self.applyButton.enabled = False
    self.framelayout.addWidget(self.applyButton)

    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.chartButton.connect('clicked(bool)', self.onChart)
    self.masterSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.masterSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectMaster)
    self.autothr.connect("toggled(bool)",self.autothreshold)
    self.resultTable.connect('cellDoubleClicked(int,int)',self.ChartThem)

    # Add vertical spacer
    self.layout.addStretch(1)

  def cleanup(self):
    pass

  def onChart(self):
    dists=self.sides+self.diagonals

    self.Chart(dists)

  def ChartThem(self,row,col):
    print("click")
    if row==0:
      dists=self.sides
    else:
      dists=self.diagonals

    self.Chart(dists)

  def Chart(self,dists):
    """Make a MRML chart of the current stats
    """
    if dists:
      layoutNodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLLayoutNode')
      layoutNodes.SetReferenceCount(layoutNodes.GetReferenceCount()-1)
      layoutNodes.InitTraversal()
      layoutNode = layoutNodes.GetNextItemAsObject()
      layoutNode.SetViewArrangement(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpQuantitativeView)
      
      chartViewNodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLChartViewNode')
      chartViewNodes.SetReferenceCount(chartViewNodes.GetReferenceCount()-1)
      chartViewNodes.InitTraversal()
      chartViewNode = chartViewNodes.GetNextItemAsObject()
      
      arrayNode = slicer.mrmlScene.AddNode(slicer.vtkMRMLDoubleArrayNode())
      array = arrayNode.GetArray()
      #dists=self.sides + self.diagonals
      # samples=len(dists)

      minimum=min(dists)
      maximum=max(dists)
      nbins=10.0
      binsize=(maximum-minimum)/nbins

      hist=self.createHst(binsize,dists)
      samples=len(hist['bin'])

      print("samples: " + str(samples))

      array.SetNumberOfTuples(samples)
      # for n in range(samples):
      #   array.SetComponent(n, 0, n)
      #   array.SetComponent(n, 1, dists[n])
      for n in range(samples):
        array.SetComponent(n, 0, hist['bin'][n])
        array.SetComponent(n, 1, hist['freq'][n])
      
      chartNode = slicer.mrmlScene.AddNode(slicer.vtkMRMLChartNode())
      chartNode.SetName("Freq")
      chartNode.AddArray("Distances", arrayNode.GetID())

      chartViewNode.SetChartNodeID(chartNode.GetID())

      print("set properties")

      chartNode.SetProperty('default', 'title', 'Measured Distances')
      chartNode.SetProperty('default', 'xAxisLabel', 'Distance')
      chartNode.SetProperty('default', 'yAxisLabel', 'N')
      #chartNode.SetProperty('default', 'type', 'Bar');
      chartNode.SetProperty('default', 'type', 'Scatter');
      #chartNode.SetProperty('default', 'xAxisType', 'categorical')
      chartNode.SetProperty('default', 'showLegend', 'off')

  def createHst(self,binsize,values):
    xs=[]
    ys=[]

    minimum=min(values)

    bin=minimum+binsize
    ys.append(0)
    xs.append(minimum+binsize/2)
    for n in range(len(values)):
      v=values[n]
      if v<=bin:
        ys[len(ys)-1]+=1
      else:
        binnum=int((v-minimum)/binsize)
        bin=minimum+(binnum+1)*binsize
        xs.append(bin-binsize/2)
        ys.append(1)

    # for n in range(len(ys)):
    #   ys[n]-=1

    hist={}
    hist['bin']=xs
    hist['freq']=ys

    return hist

  def autothreshold(self):
    self.thr.enabled=self.autothr.enabled and not self.autothr.checked
    if self.autothr.checked:
      self.thr.setValues(0,0)
      if self.master:
        lo,hi=self.master.GetImageData().GetScalarRange()
        self.thr.maximum=hi
        self.thr.minimum=0
        self.thr.setValues(self.thr.maximum/2,self.thr.maximum)
      else:
        self.thr.minimum=0
        self.thr.maximum=0

  def onSelect(self):
    self.applyButton.enabled = self.masterSelector.currentNode()

  def onSelectMaster(self):
    self.master = self.masterSelector.currentNode()
    merge=None

    self.overrideROI.enabled=False
    self.sliceslider.enabled=False
    self.autothr.enabled=False
    self.autothreshold()

    self.dgp.enabled=False
    self.chartButton.enabled=False
    self.sides=None
    self.diagonals=None
    for n in range(8):
      self.items[n+2].setText("")

    #-----mergeVolume()
    if self.master:
      self.overrideROI.enabled=True
      self.autothr.enabled=True
      self.autothreshold()

      masterName = self.master.GetName()
      mergeName = masterName+self.suffixMergeName

      # if we already have a merge and the master hasn't changed, use it
      if self.merge and self.master == self.masterWhenMergeWasSet:
        mergeNode = slicer.mrmlScene.GetNodeByID(self.merge.GetID())
        if mergeNode and mergeNode !="":
          merge=self.merge

      if not merge:
        self.masterWhenMergeWasSemasterWhenMergeWasSet = None

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
        coln.SetTypeToRandom()
        slicer.mrmlScene.AddNode(coln)
        merge.GetDisplayNode().SetAndObserveColorNodeID(coln.GetID())
        #cl=slicer.vtkMRMLColorLogic()
        #cl.SetMRMLScene(slicer.mrmlScene)
        #merge.GetDisplayNode().SetAndObserveColorNodeID(cl.GetFileColorNodeID("GenericColors.txt"))
        self.merge = merge
        self.masterWhenMergeWasSet = self.master
        #self.labelSelector.setCurrentNode(self.merge)
        self.onSelectMaster()

  def onApplyButton(self):
    applicationLogic = slicer.app.applicationLogic()
    selectionNode = applicationLogic.GetSelectionNode()
    selectionNode.SetReferenceActiveVolumeID(self.master.GetID())
    selectionNode.SetReferenceActiveLabelVolumeID(self.merge.GetID())
    applicationLogic.PropagateVolumeSelection(0)

    self.frame.enabled=False

    logic = GeometricDistortionLogic()
    print("Estimate GDP")
    sn=self.qu.getSliceNode()
    if sn:
      idx=self.qu.getSliceIndexFromOffset(sn.GetSliceOffset(),self.master)
      print("offest: " + str(sn.GetSliceOffset()))
      print("slice: " + str(idx))
      logic.run(self.master,self.merge,self.thr.maximumValue,self.thr.minimumValue,idx,self.overrideROI.checked)
      if logic.DGP:
        self.items[2].setText(logic.sides[0])
        self.items[3].setText(logic.DGP[0])
        self.items[4].setText(logic.sides[logic.sides.__len__()-1])
        self.items[5].setText(logic.DGP[1])

        self.items[6].setText(logic.diagonals[0])
        self.items[7].setText(logic.DGP[2])
        self.items[8].setText(logic.diagonals[logic.diagonals.__len__()-1])
        self.items[9].setText(logic.DGP[3])

        self.sides=logic.sides
        self.diagonals=logic.diagonals

        self.dgp.enabled=True
        self.chartButton.enabled=True
          
        # print(logic.DGP)
        # print("sides")
        # print(logic.sides)
        # print("diagonals")
        # print(logic.diagonals)

    self.frame.enabled=True

#
# GeometricDistortionLogic
#

class GeometricDistortionLogic:
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget
  """
  def __init__(self):
    pass

  def run(self,inputVolume,outputVolume,maxThr,minThr,slice,override=True):
    """
    Estimate DGP
    """
    self.volume=inputVolume
    self.label=outputVolume
    self.thrRange=[minThr,maxThr]
    self.sliceidx=slice

    self.DGP=None
    self.sides=None
    self.diagonals=None
    self.nears=None

    if override:
      slicer.util.delayDisplay('Identify islands')
      self.identIslands()

    t1=time.time()
    slicer.util.delayDisplay('Estimate DGP')
    self.getDGP()
    t2=time.time()
    print(t2-t1)

    return True

  def identIslands(self):
    inputImage=self.volume.GetImageData()
    labelImage=self.label.GetImageData()
    #labelImage.SetSpacing(self.label.GetSpacing())

    IJKToRAS = vtk.vtkMatrix4x4()
    self.volume.GetIJKToRASMatrix(IJKToRAS)
    self.label.SetIJKToRASMatrix(IJKToRAS)

    eV=slicer.vtkFillVOIImageFilter()
    eV.SetfillValue(0)
    eV.SetInputData(inputImage)

    if self.sliceidx>0:
      VOIpre=[0,inputImage.GetDimensions()[0],0,inputImage.GetDimensions()[1],0,self.sliceidx-1]
      eV.AddVOI(VOIpre)
    if self.sliceidx<inputImage.GetDimensions()[2]:
      VOIpost=[0,inputImage.GetDimensions()[0],0,inputImage.GetDimensions()[1],self.sliceidx+1,inputImage.GetDimensions()[2]]
      eV.AddVOI(VOIpost)

    eV.Update()
                    
    slice=eV.GetOutput()

    thresh = vtk.vtkImageThreshold()
    thresh.SetInputData(slice)

    thresh.ThresholdBetween(self.thrRange[0],self.thrRange[1])
    thresh.SetInValue(1)
    thresh.SetOutValue(0)
    thresh.SetOutputScalarType(vtk.VTK_SHORT)
    thresh.Modified()
    thresh.Update()

    islandM=vtkITK.vtkITKIslandMath()
    islandM.SetInputData(thresh.GetOutput())
    islandM.Update()

    labelImage.DeepCopy(islandM.GetOutput())

  def getCOG(self,volumeNode,labelVal):
    COG = []
    count = 0
    sumX = sumY = sumZ = 0
    volumeIM = volumeNode.GetImageData()
    pixdims=volumeNode.GetSpacing()

    # for z in xrange(volumeIM.GetExtent()[4], volumeIM.GetExtent()[5]+1):
    #   for y in xrange(volumeIM.GetExtent()[2], volumeIM.GetExtent()[3]+1):
    #     for x in xrange(volumeIM.GetExtent()[0], volumeIM.GetExtent()[1]+1):
    #       voxelValue = volumeIM.GetScalarComponentAsDouble(x,y,z,0)
    #       if voxelValue==labelVal:
    #         count=count+1
    #         sumX = sumX + (x*pixdims[0])
    #         sumY = sumY + (y*pixdims[1])
    #         sumZ = sumZ + (z*pixdims[2])

    for y in range(volumeIM.GetDimensions()[1]):
      for x in range(volumeIM.GetDimensions()[0]):
        voxelValue = volumeIM.GetScalarComponentAsDouble(x,y,self.sliceidx,0)
        if voxelValue==labelVal:
          count=count+1
          sumX = sumX + (x*pixdims[0])
          sumY = sumY + (y*pixdims[1])

    if count > 0:
      COG.append(sumX / count)
      COG.append(sumY / count)
      #COG.append(sumZ / count)

    return COG

  def getDGPPyth(self):
    labelImage=self.label.GetImageData()

    if labelImage.GetScalarRange()[1]!=49:
      print("Error: Wrong number of rods: slice or threshold range?: " + str(labelImage.GetScalarRange()[1]))
    else:
      COGs=[]
      maxnear=40
      side=25
      diag=side*math.sqrt(2)

      slicer.util.delayDisplay('Calculating COGs...')
      for l in range(5,50):
        COGs.append(self.getCOG(self.label,l))

      slicer.util.delayDisplay('Measuring distances...')
      self.nears={}
      dsts=[]
      for r1 in range(45):
        c1=COGs[r1]
        self.nears[r1]=[]
        for r2 in range(r1+1,45):
          c2=COGs[r2]
          ds=[]
          ds.append(c1[0]-c2[0])
          ds.append(c1[1]-c2[1])
          if (abs(ds[0])<maxnear and abs(ds[1])<maxnear):
            self.nears[r1].append(r2)
            dsts.append(math.sqrt(ds[0]**2+ds[1]**2))

      if dsts.__len__() != 144:
        print("Wrong nears numbers: " + str(dsts.__len__()))
      else:
        dsts.sort()

        self.sides=dsts[0:76]
        self.diagonals=dsts[76:144]

        slicer.util.delayDisplay('Estimating DGPs...')
        DGPsides=[]
        DGPdiags=[]
        for n in range(self.sides.__len__()):
          DGPsides.append(100*(self.sides[n]-side)/side)

        DGPsides.sort()

        for n in range(self.diagonals.__len__()):
          DGPdiags.append(100*(self.diagonals[n]-diag)/diag)

        DGPdiags.sort()

        self.DGP=[]
        self.DGP.append(DGPsides[0])
        self.DGP.append(DGPsides[DGPsides.__len__()-1])
        self.DGP.append(DGPdiags[0])
        self.DGP.append(DGPdiags[DGPdiags.__len__()-1])


  def getDGPvtk(self):
    labelImage=self.label.GetImageData()

    if labelImage.GetScalarRange()[1]!=49:
      print("Error: Wrong number of rods: slice or threshold range?: " + str(labelImage.GetScalarRange()[1]))
    else:
      COGs=[]
      maxnear=40
      side=25
      diag=side*math.sqrt(2)

      slicer.util.delayDisplay('Calculating COGs...')
      for l in range(5,50):
        COG=self.getCOGvtk(self.label,l)
        sp=self.label.GetSpacing()
        for s in range(3):
          COG[s]=COG[s]*sp[s]
        COGs.append(COG)

      slicer.util.delayDisplay('Measuring distances...')
      self.nears={}
      dsts=[]
      for r1 in range(45):
        c1=COGs[r1]
        self.nears[r1]=[]
        for r2 in range(r1+1,45):
          c2=COGs[r2]
          ds=[]
          ds.append(c1[0]-c2[0])
          ds.append(c1[1]-c2[1])
          if (abs(ds[0])<maxnear and abs(ds[1])<maxnear):
            self.nears[r1].append(r2)
            dsts.append(math.sqrt(ds[0]**2+ds[1]**2))

      if dsts.__len__() != 144:
        print("Wrong nears numbers: " + str(dsts.__len__()))
      else:
        dsts.sort()

        self.sides=dsts[0:76]
        self.diagonals=dsts[76:144]

        slicer.util.delayDisplay('Estimating DGPs...')
        DGPsides=[]
        DGPdiags=[]
        for n in range(self.sides.__len__()):
          DGPsides.append(100*(self.sides[n]-side)/side)

        DGPsides.sort()

        for n in range(self.diagonals.__len__()):
          DGPdiags.append(100*(self.diagonals[n]-diag)/diag)

        DGPdiags.sort()

        self.DGP=[]
        self.DGP.append(DGPsides[0])
        self.DGP.append(DGPsides[DGPsides.__len__()-1])
        self.DGP.append(DGPdiags[0])
        self.DGP.append(DGPdiags[DGPdiags.__len__()-1])


  def getDGP(self):
    labelImage=self.label.GetImageData()

    if labelImage.GetScalarRange()[1]!=49:
      print("Error: Wrong number of rods: slice or threshold range?: " + str(labelImage.GetScalarRange()[1]))
    else:
      COGs=[]
      maxnear=40
      side=25
      diag=side*math.sqrt(2)

      slicer.util.delayDisplay('Calculating COGs...')
      cogcal=slicer.vtkITKCoG()
      cogcal.SetInputData(labelImage)
      cogcal.Setspacing(self.volume.GetSpacing())
      
      #COG=[0,0,0]
      for l in range(5,50):
        cogcal.SetlabelValue(l)
        cogcal.Update()
        #cogcal.GetCOG(COG)
        COG=cogcal.GetCOG()
        #COGs.append(self.getCOG(self.label,l))
        COGs.append(COG)

      slicer.util.delayDisplay('Measuring distances...')
      self.nears={}
      dsts=[]
      for r1 in range(45):
        c1=COGs[r1]
        self.nears[r1]=[]
        for r2 in range(r1+1,45):
          c2=COGs[r2]
          ds=[]
          ds.append(c1[0]-c2[0])
          ds.append(c1[1]-c2[1])
          if (abs(ds[0])<maxnear and abs(ds[1])<maxnear):
            self.nears[r1].append(r2)
            dsts.append(math.sqrt(ds[0]**2+ds[1]**2))

      if dsts.__len__() != 144:
        print("Wrong nears numbers: " + str(dsts.__len__()))
      else:
        dsts.sort()

        self.sides=dsts[0:76]
        self.diagonals=dsts[76:144]

        slicer.util.delayDisplay('Estimating DGPs...')
        DGPsides=[]
        DGPdiags=[]
        for n in range(self.sides.__len__()):
          DGPsides.append(100*(self.sides[n]-side)/side)

        DGPsides.sort()

        for n in range(self.diagonals.__len__()):
          DGPdiags.append(100*(self.diagonals[n]-diag)/diag)

        DGPdiags.sort()

        self.DGP=[]
        self.DGP.append(DGPsides[0])
        self.DGP.append(DGPsides[DGPsides.__len__()-1])
        self.DGP.append(DGPdiags[0])
        self.DGP.append(DGPdiags[DGPdiags.__len__()-1])
