from __main__ import vtk, qt, slicer
import math
import numpy

class QCUtil:
    def getVolume(self,volumeNode,minValue=1):
        if volumeNode:
            im=volumeNode.GetImageData()
            if im:
                return self.getVolumeIm(im,minValue)
        return None

    def getVolumeIm(self,im,minValue=1):
        thresh = vtk.vtkImageThreshold()
        thresh.SetInputData(im)

        max = im.GetScalarRange()[1]

        thresh.ThresholdBetween(minValue, max)
        thresh.SetInValue(1)
        thresh.SetOutValue(0)
        thresh.SetOutputScalarType(im.GetScalarType())
        thresh.Modified()
        thresh.Update()
                
        stencil = vtk.vtkImageToImageStencil()
        stencil.SetInputData(thresh.GetOutput())
        stencil.ThresholdBetween(1, 1)
        stencil.Update()
            
        stat1 = vtk.vtkImageAccumulate()
        stat1.SetInputData(im)
        stat1.SetStencilData(stencil.GetOutput())
        stat1.Update()

        return stat1.GetVoxelCount()        

    def getSliceArea(self,volumeNode,sliceNum,minValue=1):
        if volumeNode:
            im=volumeNode.GetImageData()
            if im:
                return self.getSliceAreaIm(im,sliceNum,minValue)

        return None

    def getSliceAreaIm(self,im,sliceNum,minValue=1):
        nslices=im.GetDimensions()[2]
        if sliceNum>(nslices-1) or sliceNum<0:
            return None
        else:
            eV=vtk.vtkExtractVOI()
            VOI=[0,im.GetDimensions()[0],0,im.GetDimensions()[1],sliceNum,sliceNum]
            eV.SetInputData(im)
            eV.SetVOI(VOI)
            eV.Update()
            slice=eV.GetOutput()

            maxValue = slice.GetScalarRange()[1]
            
            # thresh = vtk.vtkImageThreshold()
            # thresh.SetInputData(slice)

            # thresh.ThresholdBetween(minValue, max)
            # thresh.SetInValue(1)
            # thresh.SetOutValue(0)
            # thresh.SetOutputScalarType(slice.GetScalarType())
            # thresh.Update()

            stencil = vtk.vtkImageToImageStencil()
            stencil.SetInputConnection(eV.GetOutputPort())
            stencil.ThresholdBetween(minValue, maxValue)
            stencil.Update()
            
            stat1 = vtk.vtkImageAccumulate()
            stat1.SetInputConnection(eV.GetOutputPort())
            stat1.SetStencilData(stencil.GetOutput())
            stat1.Update()

            return stat1.GetVoxelCount()

    def getROIstats(self,volumeNode,ROInode):
        if volumeNode and ROInode:
            im=volumeNode.GetImageData()
            roiim=ROInode.GetImageData()
            return self.getROIstatsIM(im,roiim)
        
        return None

    def getROIstatsIM(self,volumeIm,ROIIm):
        im=volumeIm
        roiim=ROIIm
        ROIStats={}
        if im and roiim:
            dim3=im.GetDimensions()[2]
            
            stencil = vtk.vtkImageToImageStencil()
            stencil.SetInputData(roiim)
            stencilsl = vtk.vtkImageToImageStencil()
            numrois=int(roiim.GetScalarRange()[1])

            stat1 = vtk.vtkImageAccumulate()
            
            stat1.SetInputData(im)

            for roi in range(1,numrois+1):
                #print("roi " + str(roi))
                fg=roi
                
                stencil.ThresholdBetween(fg, fg)
                stencil.Update()
                stat1.SetStencilData(stencil.GetOutput())
                stat1.Update()
            
                Sstats={}
                stats={}
                stats['count']=stat1.GetVoxelCount()
                stats['min']=stat1.GetMin()[0]
                stats['max']=stat1.GetMax()[0]
                stats['mean']=stat1.GetMean()[0]
                stats['sd']=stat1.GetStandardDeviation()[0]

                Sstats['volume']=stats

                for d3 in range(dim3):
                    #print("slice " + str(d3))
                    eV=vtk.vtkExtractVOI()
                    VOI=[0,im.GetDimensions()[0],0,im.GetDimensions()[1],d3,d3]
                    eV.SetVOI(VOI)

                    eV.SetInputData(im)
                    eV.Update()
                    
                    slice=eV.GetOutput()

                    eVroi=vtk.vtkExtractVOI()
                    eVroi.SetVOI(VOI)
                    eVroi.SetInputData(roiim)
                    eVroi.Update()

                    roislice=eVroi.GetOutput()

                    stencilsl.SetInputData(roislice)
                    stencilsl.ThresholdBetween(fg, fg)
                    stencilsl.Update()

                    statsl = vtk.vtkImageAccumulate()
                    statsl.SetInputData(slice)
                    statsl.SetStencilData(stencilsl.GetOutput())
                    statsl.Update()
                    
                    stats={}
                    stats['count']=statsl.GetVoxelCount()
                    stats['min']=statsl.GetMin()[0]
                    stats['max']=statsl.GetMax()[0]
                    stats['mean']=statsl.GetMean()[0]
                    stats['sd']=statsl.GetStandardDeviation()[0]
                
                    Sstats[d3]=stats

                ROIStats[roi]=Sstats

            return ROIStats
        return None
    
    def getVolStatistics(self,volumeNode,minValue=1):
        if volumeNode:
            im=volumeNode.GetImageData()
            if im:
                return self.getVolImStatistics(im,minValue)
        return None

    def getVolImStatistics(self,im,minValue=1):
        dim3=im.GetDimensions()[2]
        stats={}
        stats['volume']=self.getVolumeIm(im,minValue)

        for d3 in range(dim3):
            stats[d3]=self.getSliceAreaIm(im,d3,minValue)

        return stats

    def getSliceNode(self):
        sns=slicer.mrmlScene.GetNodesByClass('vtkMRMLSliceNode')
        sn=None
        for n in range(sns.GetNumberOfItems()):
            if sns.GetItemAsObject(n).GetOrientationString() == "Axial":
                sn=sns.GetItemAsObject(n)
                break
        return sn

    def getSliceOffsetFromIndex(self,index,volumeNode):
        sn=self.getSliceNode()
        if sn:
            dim3=sn.GetUVWExtents()[2]
            sl=slicer.vtkMRMLSliceLogic()
            sl.SetSliceNode(sn)
            sl.StartSliceNodeInteraction(512)
            sl.StartSliceOffsetInteraction()
            off=sl.GetSliceOffset()
            slicein=sl.GetSliceIndexFromOffset(sl.GetSliceOffset(),volumeNode)-1
            sl.EndSliceNodeInteraction()
            sl.EndSliceOffsetInteraction()
            sl.SetSliceNode(None)
            orig=off-slicein*dim3
            newoff=orig+dim3*index

            return newoff
        else:
            return -1

    def getSliceIndexFromOffset(self,offset,volumeNode):
        sn=self.getSliceNode()
        if sn:
            sl=slicer.vtkMRMLSliceLogic()
            sl.SetSliceNode(sn)
            sl.StartSliceNodeInteraction(512)
            sl.StartSliceOffsetInteraction()
            off=sl.GetSliceOffset()
            slicein=sl.GetSliceIndexFromOffset(sl.GetSliceOffset(),volumeNode)-1
            sl.EndSliceNodeInteraction()
            sl.EndSliceOffsetInteraction()
            sl.SetSliceNode(None)

            return slicein
        else:
            return -1

    def getSliceOrigOffset(self,volumeNode):
        sn=self.getSliceNode()
        if sn:
            dim3=sn.GetUVWExtents()[2]
            sl=slicer.vtkMRMLSliceLogic()
            sl.SetSliceNode(sn)
            sl.StartSliceNodeInteraction(512)
            sl.StartSliceOffsetInteraction()
            off=sl.GetSliceOffset()
            slicein=sl.GetSliceIndexFromOffset(sl.GetSliceOffset(),volumeNode)-1
            sl.EndSliceNodeInteraction()
            sl.EndSliceOffsetInteraction()
            sl.SetSliceNode(None)
            orig=off-slicein*dim3

            return orig
        else:
            return -1

    def getVolumeMin(self,volume):
        if volume.GetClassName() == "vtkMRMLLabelMapVolumeNode":
            return 1
        else:
            return self.getImageMin(volume.GetImageData())

    def getImageMin(self,image):
        lo, hi = image.GetScalarRange()
        return (lo + 0.25 * (hi-lo))        

    def minRectangle(self,labelNode):
        a=slicer.util.array(labelNode.GetName())

        xmax={}
        xmin={}
        ymax={}
        ymin={}
        asw=a.swapaxes(1,2)
        for z in range(a.__len__()):
            b=a.__getitem__(z)
            c=asw.__getitem__(z)
            if b.any():
                for y in range(b.__len__()):
                    if b.__getitem__(y).any():
                        try:
                            tmp=ymin[z]
                            ymax[z]=y
                        except:
                            ymin[z]=y
            else:
                ymin[z]=-1
                ymax[z]=-1
            if c.any():
                for x in range(c.__len__()):
                    if c.__getitem__(x).any():
                        try:
                            tmp=xmin[z]
                            xmax[z]=x
                        except:
                            xmin[z]=x
            else:
                xmin[z]=-1
                xmax[z]=-1

        rect={}
        rect['xmin']=xmin
        rect['xmax']=xmax
        rect['ymin']=ymin
        rect['ymax']=ymax
        return rect

    #get a VOI list conjugate of a VOI in a image of dimensions dims
    def reverseVOI(self,VOI,dims):
        revVOIs=[]

        if VOI[0]!=0:
            revVOIs.append([0,VOI[0]-1,0,dims[1]-1,0,dims[2]-1]) #parte sn
        if VOI[1]!=dims[0]-1:
            revVOIs.append([VOI[1]+1,dims[0]-1,0,dims[1]-1,0,dims[2]-1]) #parte ds
        if VOI[2]!=0:
            revVOIs.append([VOI[0],VOI[1],0,VOI[2]-1,0,dims[2]-1]) #parte dietro
        if VOI[3]!=dims[1]-1:
            revVOIs.append([VOI[0],VOI[1],VOI[3]+1,dims[1]-1,0,dims[2]-1]) #parte davanti
        if VOI[4]!=0:
            revVOIs.append([VOI[0],VOI[1],VOI[2],VOI[3],0,VOI[4]-1]) #parte sotto
        if VOI[5]!=dims[2]-1:
            revVOIs.append([VOI[0],VOI[1],VOI[2],VOI[3],VOI[5]+1,dims[2]-1]) #parte sopra

        return revVOIs

    #get a VOI list conjugate of a VOI in a image
    def reverseVOIInImage(self,VOI,image):
        dims=image.GetDimensions()

        return self.reverseVOI(VOI,dims)


    def getVOIfromRectROI(self,ROInode):
        rect=self.minRectangle(ROInode)

        xmins=rect['xmin']
        xmaxs=rect['xmax']
        ymins=rect['ymin']
        ymaxs=rect['ymax']

        zmin=-1
        zmax=-1
        xmin=-1
        xmax=-1
        ymin=-1
        ymax=-1
        for n in range(xmins.__len__()):
            if xmins[n]>=0:
                xmin=xmins[n]
                xmax=xmaxs[n]
                ymin=ymins[n]
                ymax=ymaxs[n]
                if zmin<0:
                    zmin=n
                if zmax<n:
                    zmax=n
        VOI=[xmin,xmax,ymin,ymax,zmin,zmax]

        return VOI
        
    def Rebin(self,histVals,nbin,xmin,xmax,interp=False):
        xrang=xmax-xmin
        binSize = xrang / (nbin - 1)

        xvals=histVals[0]
        yvals=histVals[1]

        hst={}
        deg={}

        for idx in range(xvals.__len__()):
            xval=xvals[idx]
            if (xval>=xmin) and (xval<=xmax):
                binNum = math.floor(xval / binSize + 0.5)
                try:
                    v=hst[binNum]
                    hst[binNum]+=yvals[idx]
                    deg[binNum]+=1
                except:
                    hst[binNum]=yvals[idx]
                    deg[binNum]=1

        bins=[]
        hist=[]

        for n in range(hst.__len__()):
            hist.append(hst.values()[n]/deg.values()[n])
            bins.append(binSize * int(hst.keys()[n]))
        histogram=[bins,hist]
        sortHist=list(zip(*sorted(zip(*histogram),key=lambda x:x[0])))
        sortHist=[list(sortHist[0]),list(sortHist[1])]

        if not interp or hst.__len__()==nbin:
            return sortHist
        else:
            xs=list(numpy.linspace(xmin,xmax,nbin))
            try:
                xs.index(0)
            except:
                xs.append(0)
                xs.sort()
            hsty=numpy.interp(xs,sortHist[0],sortHist[1])

            return [xs,hsty]

    #discrete derivate of a array
    def DDerive(self,darray):
        xval=darray[0]
        yval=darray[1]

        # Dx=[]
        # Dy=[]
        # for n in range(len(darray[0])-1):
        #     Dx.append(xval[n])
        #     Dy.append((yval[n+1]-yval[n])/(xval[n+1]-xval[n]))

        Dy=list(numpy.diff(yval)/numpy.diff(xval))
        
        DD=[xval[0:len(xval)-1],Dy]

        return DD

    #discrete fourier transform of a array uniformly sampled
    def DFFT(self,darray):
        N=len(darray[0])
        if N>1:
            xval=darray[0]
            yval=darray[1]

            FFTx=[]
            FFTyRe=[]
            FFTyIm=[]

            T=xval[1]-xval[0]
            omegas=float(2*math.pi/(N*T))
            for n in range(N):
                FFTx.append(n*omegas)
                FFTyRe.append(0)
                FFTyIm.append(0)
                print("freq " + str(n) + ": " + str(FFTx[n]))
                for k in range(N):
                    theta=-float(k*n*omegas)
                    Re=math.cos(theta)
                    Im=math.sin(theta)
                    FFTyRe[n]+=yval[k]*Re
                    FFTyIm[n]+=yval[k]*Im
                    #print("fft " + str(k) + ": " + str(Re) + " " + str(Im) + " " + str(FFTyRe) + " " + str(FFTyIm))
                print("fft : " + str(FFTyRe) + " " + str(FFTyIm))
            return [FFTx,[FFTyRe,FFTyIm]]
        else:
            return None

    #modulus of a two dimensional array
    def modulus(self,darray):
        comp1=darray[0]
        comp2=darray[1]

        mod=[]
        for n in range(len(comp1)):
            mod.append(math.sqrt(comp1[n]**2+comp2[n]**2))

        return mod

    def normalize(self,darray):
        Mx=max(darray)

        Nar=[]
        for n in range(len(darray)):
            Nar.append(darray[n]/Mx)

        return Nar

    def maskVolume(self,input,mask,output):
        sr=input.GetImageData().GetScalarRange()
        
        parameters={}
        parameters["InputVolume"] = input.GetID()
        parameters["MaskVolume"] = mask.GetID()
        parameters["OutputVolume"] = output.GetID()
        parameters["Label"]=1 #TODO: label values
        parameters["Replace"]=sr[0]-1

        mskSL=slicer.modules.maskscalarvolume

        cliNode=slicer.cli.run(mskSL,None,parameters,wait_for_completion=True)
        im=output.GetImageData()

        return im
