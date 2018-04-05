# -*- coding: utf-8 -*-
"""
Created on Thu Mar 12 12:43:40 2015

This code uses R: as a back end and the rpy2 module as an api.

This code takes as an input a CSV file with the dependent variable (the one you
want to predict) in the first column and the independent variables (the ones 
you want to use to predict from) in all subsequent columns. Headers are 
expected in the CSV file and are used in the output.

The code applies a 5th order linear model regression function in R: language
(mod = lm(Y ~ poly(X1, 5, raw = TRUE)) ). The regression is applied to each
column of independent variables (X1-Xn) and used to make a line of best fit.
The independent variable that returns the lowest residual squared (R^2) value
is saved.

Multivariate polynomial regression is then applied by mixing the best
independent variable with a second independent variable, in R: language;
(mod = lm(Y ~ poly(X1, 5, raw = TRUE)) + poly(X2, 5, raw = TRUE)) ...)) - the
combination returning the lowest R^2 is saved.

The process continues, but now the least necessary independent variable is
removed and the next best variable is added twice. This is the parsimonius 
process.

The output is a CSV file, the first column is the R^2, thereby ranking the 
solution, the following columns are then the independent variables employed
in the regression.  

Bare in mind that the R: environment is also running, therefore variables and
methods can persist in it. I had to attach() objects to the workspace as it is
difficult to pass a command such as RegressData$X1, to say X1 from data frame =
RegressData, instead I had to (in R language) attach(RegressData) go to X1. If
you see a Masking Error it is because data has been attached over other data
and they have the same column names. It is generally a good idea to start this
in a fresh consol.  

@author: pbrogan
"""

import rpy2.robjects as robjects
import glob
import csv
from numbers import Number

class Files():
    """This method utilises the rpy2 module for polynomial regression,
    the idea is to parsimoniously place PMUs at busses to give an 
    evermore accurate interpretation of system state"""
    
    def __init__(self):
        """This initiates variables that are specific to the working case,
        and can be changed; e.g. working directory, number of PMUs to place.
        The order in which to carry out the regression can be controlled as the
        variable self.ModelsToTest is itterated through in order.
        """
        #These values can be changed
        self.working_directory = 'inputFolder/'
        self.op_directory = "opFolder/" #self.working_directory + '/PMUplacementTables/'
        self.TestParticularModels = False
        self.ModelsToTest = ['regressMe']
        self.TargetValue = 'angDiff'
        #enter a defining feature of the files you wish tested 
        self.SetMaxPMUs = True
        self.MaxPMUs = 20
        self.ExcludedBusses = []
        self.VeryParsimonious = True                                                                                                 
        self.PolynomialDegree = 3
        self.GenMetaData = True
        self.AttachData = True
        self.VerboseOP = True
        #These are simply declared Lists etc. no change suggested
        self.MetaDataOP = []
        self.VerboseDataOP = []
        self.PlacedPMUs = [0]
        self.PMUstates = []
        self.DataOP = []
        self.ip_filenames_list = []
        self.dataframe = 0
        #robjects.r['detach']()
        robjects.r['rm']()
        self.formula = None
        self.fomulaBreakDown = []
        if self.SetMaxPMUs == False:
            self.MaxPMUs = 9999
        
    def Reset(self):
        """This is applied  reinitialises empty lists for the variables that 
        are first appended, other variables are set to 'None' type, clearing 
        memory and preventing the possibility of carry over of data in those
        varables"""
        self.PlacedPMUs = [0]
        self.PMUstates = []
        self.DataOP = []
        self.VerboseDataOP = []
        self.Xheaders = None
        self.Yheader = None
        self.Header = None
        self.formula = None
        self.fomulaBreakDown = []
        self.lmResults = None
        self.ResSquare = None
        self.TrialPMUs = None
        self.ip_filename = None
        self.MetaDataOP = []
        #robjects.r['detach']()
        robjects.r['rm']()
        robjects.r['gc']()
        
        
    def filenames(self):
        """This plucks out the filenames from the working_directory that fit
        the condition of being a CSV file; if self.TestParticularModels = TRUE
        then only file names containing strings contained in the 
        self.ModelsToTest list are included"""
        ip_files_list = self.working_directory + '*.csv'
        ip_files_list = glob.glob(ip_files_list)
        if self.TestParticularModels == True:
            for ModName in self.ModelsToTest:
                for FileName in ip_files_list:
                    if ModName in FileName:
                        self.ip_filenames_list.append(FileName)
        else:
            self.ip_filenames_list = ip_files_list
        
        
        
class ReadCSVdata(Files):
    """Call the read function to enter the dataframe in the R environment
    the dataframe is declared as an object variable, along with SysOPM -
    the dependent variable - and the bus numbers X1 through Xmax - as the
    indepent variables"""
    def __init__(self):
        Files.__init__(self)
        
    def Rread(self):
        self.dataframe = robjects.r['read.csv'](self.ip_filename)
        Headers = list(robjects.r['colnames'](self.dataframe))
        if self.AttachData == True:
            #if self.dataframe <> 0:
                #robjects.r['detach'](self.dataframe)
            robjects.r['attach'](self.dataframe)
        #I have to attach files, otherwise rpy2 uploads all the data
        #everytime I call the lm function. The data is detached in the
        #reset function
        try:
            Headers.remove(self.TargetValue)
            self.Yheader = self.TargetValue
            self.Xheaders = Headers
        except:
            print('Header Error', self.TargetValue, 'not in', Headers)
            self.Yheader = Headers[0]
            self.Xheaders = Headers[1:]

class SuportFunctions(ReadCSVdata):
    """This creates the strings that are fed to the rpy2 interface,
    the syntax should be familiar to those who understand some R e.g.
    fit = lm(Y~poly(X,3,raw=TRUE)) this function creates the 
    'Y~poly(X,3,raw=TRUE)' bit"""
    def __init__(self):
        ReadCSVdata.__init__(self)
        
    def SetFormula(self,BusList):
        """this takes the list of busses to be used in the regression model
        and sets the object variable 'self.formula' in the appropriate R format
        e.g. '(self.TargetValue ~ poly(X1, 5, Raw = True)+ poly(X2, 5, raw = TRUE)+..."""
        #print BusList
        begining = ' + poly('
        ending = ', ' + str(self.PolynomialDegree) + ', raw = TRUE)'
        opFormula = str(self.Yheader) + ' ~ poly( ' + BusList[0] + ending
        if len(BusList) > 1:
            for Bus in BusList[1:]:
                opFormula += begining + Bus + ending
        self.formula = str(opFormula)
        self.fomulaBreakDown = BusList
        #print self.formula
        
class StatAnalysis(SuportFunctions):
    """Only the linear model is run, the formula to be applied (anticipated as
    a polynomial) is taken as an argument. The function sets the object 
    variable of the linear model results and the residual squared"""
    def __init__(self):
        SuportFunctions.__init__(self)
        
    def RunLinearMod(self):
        robjects.r['gc']()
        if self.AttachData == True:
            lmResults = robjects.r['lm'](self.formula)
        else:
            lmResults = robjects.r['lm'](self.formula, data = self.dataframe)
        self.ResSquare = robjects.r['summary'](lmResults)[7][0]
        
        self.VerboseDataOP.append([self.ResSquare] +  [str(self.formula)] + 
            self.fomulaBreakDown + list(robjects.r['summary'](lmResults)[3])[
                    :( 1 + len(self.PlacedPMUs) * self.PolynomialDegree)])
        
    def GenerateMetaData(self):
        """this is auxilliary info, at present only on the coefficients of the 
        best fit line, this data in only generated if requested GenMetaData ==
        True. The coefficients returned by R: contain std. error and T values
        which are not stored, the line is parsed to only return the estimates 
        of the coefficients."""
        if self.GenMetaData == True:        
            PMUpositions = self.PlacedPMUs[1:]
            self.SetFormula(PMUpositions)
            self.MetaData = [str(self.formula)]
            lmResults = robjects.r['lm'](self.formula, data = self.dataframe)
            FitData = robjects.r['summary'](lmResults)[3]
            #print 'length',len(self.PlacedPMUs)
            
            for n in range(0, ( len(self.PlacedPMUs) * self.PolynomialDegree)-1):
                self.MetaData.append(FitData[n])
            self.MetaDataOP.append(self.MetaData)
       
  
class PlacePMUs(StatAnalysis):
    """These functions eith add a single PMU to self.PlacedPMUs, or removes one
    in either case the PMU that makes the most, or least (respectively),
    improvement to state certainty (deduced from the R^2 result) is either
    kept/dropped (respectively)"""
    
    def __init__(self):
        StatAnalysis.__init__(self)
    
    def AddBestPMU(self):
       # if (len(self.PlacedPMUs)-1) < self.MaxPMUs and \
       # (len(self.PlacedPMUs) - 1) < (len(self.Xheaders) 
       # - len(self.ExcludedBusses)):
        self.TrialPMUs = []
        lmResults = []
        for Bus in self.Xheaders:
            """Populate list with potential bus placements"""
            if Bus not in self.PlacedPMUs and Bus not in self.ExcludedBusses:
                self.TrialPMUs.append(Bus)
                
        for Bus in self.TrialPMUs:
            lmPMUs = list(self.PlacedPMUs[1:]) + [Bus]
            self.SetFormula(lmPMUs)
            self.RunLinearMod()
            lmResults.append([self.ResSquare] + lmPMUs)
        lmResults = sorted(lmResults, reverse = True)
        self.PlacedPMUs = lmResults[0]
   # else:
        #print "All PMUs Placed"
            
    def RemoveWorstPMU(self):
        lmResults = []
        for Bus in self.PlacedPMUs[1:]:
            lmPMUs = list(self.PlacedPMUs[1:])
            lmPMUs.remove(Bus)
            self.SetFormula(lmPMUs)
            self.RunLinearMod()
            lmResults.append([self.ResSquare] + lmPMUs)
            
        lmResults = sorted(lmResults, reverse = True)
        self.PlacedPMUs = lmResults[0]
        
        
        
class PMUitterator(PlacePMUs):
    """selectively add and remove PMUs untill either a) the desired number of 
    PMUs are placed b) PMUs are placed at all busses c) PMUs are placed at all
    busses apparet from forbidden ones. While this process is going on the 
    chain of PMU placements and removals are saved in self.DataOP"""
    def __init__(self):
        PlacePMUs.__init__(self)
        
    def PlaceAllPMUs(self):
        """selectively add and remove PMUs untill the requisite number of PMUs
        are on the system. Methods of opperation Start -> add 4 PMUs to the
        system. Main Body -> Remove least vital PMU, is this a new arrangement?
        [if no] -> undo remove PMU and add an extra PMU (if new state save)
        [if yes] -> save state then add next best PMU (if new state then save)
        add second PMU (if new state save). End Game -> have the requisite
        number of PMUs been added? [if no] -> run over main body [if yes] ->
        return results"""
        while len(self.PlacedPMUs) <= 4 and \
        (len(self.PlacedPMUs) - 1) <= (len(self.Xheaders) - 
        len(self.ExcludedBusses)) and \
        (len(self.PlacedPMUs) - 1) <= self.MaxPMUs:
            self.AddBestPMU()
            self.DataOP.append(list(self.PlacedPMUs))
            self.GenerateMetaData()
            print('Opening Placements - placed', (len(self.PlacedPMUs) - 1), 'regression value')
            self.PMUstates.append(sorted(self.PlacedPMUs[1:]))
        
        while (len(self.PlacedPMUs)-1) < self.MaxPMUs and \
        (len(self.PlacedPMUs) - 1) < (len(self.Xheaders)
        - len(self.ExcludedBusses)):
            PMUstateHold = list(self.PlacedPMUs)
            self.RemoveWorstPMU()
            if sorted(self.PlacedPMUs[1:]) in self.PMUstates:
                print('retrograde PMU removal, undone')
                self.PlacedPMUs = PMUstateHold
                self.AddBestPMU()

            else:
                self.DataOP.append(self.PlacedPMUs)
                self.PMUstates.append(sorted(self.PlacedPMUs[1:]))
                self.GenerateMetaData()
                print('new diminished state')
                if self.VeryParsimonious == False:
                    self.AddBestPMU()
                if sorted(self.PlacedPMUs[1:]) not in self.PMUstates:
                    self.DataOP.append(self.PlacedPMUs)
                    self.GenerateMetaData()
                    self.PMUstates.append(sorted(self.PlacedPMUs[1:]))
                self.AddBestPMU()

            if sorted(self.PlacedPMUs[1:]) not in self.PMUstates:
                self.DataOP.append(self.PlacedPMUs)
                self.GenerateMetaData()
                self.PMUstates.append(sorted(self.PlacedPMUs[1:]))
            print('1 back 2 forward - placed',(len(self.PlacedPMUs)-1), 'PMUs')

    def PlaceSinglePMU(self):
        """selectively add and remove a single PMU, this process will throw an
        exception if the number of PMUs exceeds the Max number of PMUs.
        While there are less than 4 PMUs on the system, PMUs are simply added;
        then one PMU, the least vital, is removed, if this is a new state the 
        state is saved. Next two PMUs are added incrementally, if either is a
        new state it is saved.
        [if no] -> undo remove PMU and add an extra PMU (if new state save)
        [if yes] -> save state then add next best PMU (if new state then save)
        add second PMU (if new state save). End Game -> have the requisite
        number of PMUs been added? [if no] -> run over main body [if yes] ->
        return results"""
        self.DataOP = []
        self.MetaDataOP = []
        if len(self.PlacedPMUs) <= 4 and \
        (len(self.PlacedPMUs) - 1) <= (len(self.Xheaders) - 
        len(self.ExcludedBusses)) and \
        (len(self.PlacedPMUs) - 1) <= self.MaxPMUs:
            self.AddBestPMU()
            self.DataOP.append(list(self.PlacedPMUs))
            self.GenerateMetaData()
            print('Opening - placed', (len(self.PlacedPMUs) - 1), 'PMUs')
            self.PMUstates.append(sorted(self.PlacedPMUs[1:]))
        
        elif (len(self.PlacedPMUs)-1) < self.MaxPMUs and \
        (len(self.PlacedPMUs) - 1) < (len(self.Xheaders)
        - len(self.ExcludedBusses)):
            PMUstateHold = list(self.PlacedPMUs)
            self.RemoveWorstPMU()
            if sorted(self.PlacedPMUs[1:]) in self.PMUstates:
                #print 'retrograde PMU removal, undone'
                self.PlacedPMUs = PMUstateHold
                self.AddBestPMU()

            else:
                self.DataOP.append(self.PlacedPMUs)
                self.PMUstates.append(sorted(self.PlacedPMUs[1:]))
                #print 'new diminished state'
                if self.VeryParsimonious == False:
                    self.AddBestPMU()
                if sorted(self.PlacedPMUs[1:]) not in self.PMUstates:
                    self.DataOP.append(self.PlacedPMUs)
                    self.GenerateMetaData()
                    self.PMUstates.append(sorted(self.PlacedPMUs[1:]))
                self.AddBestPMU()

            if sorted(self.PlacedPMUs[1:]) not in self.PMUstates:
                self.DataOP.append(self.PlacedPMUs)
                self.GenerateMetaData()
                self.PMUstates.append(sorted(self.PlacedPMUs[1:]))
            print('1 back 2 forward - placed',(len(self.PlacedPMUs)-1), 'PMUs')
        else:
            print("%%%%%%%%%% PROBLEM - CONDITION NOT MET %%%%%%%%%%%%%")

class OPsupportFunctions(PMUitterator):
    """At present this class only contains the csv writer function"""
    def __init__(self):
        PMUitterator.__init__(self)
        
    def MakeHeader(self):
        """This produces a header of length, desired number or PMUs, or, total
        number of busses minus number of excluded busses - whichever is the 
        shortest. The first column is called Res^2, this is the residual 
        squared (R-squared = Explained variation / Total variation). The 
        following headers are Var 1 through Max, these are the variables that 
        should be picked"""
        headerLength = min(self.MaxPMUs, 
                               (len(self.Xheaders) - len(self.ExcludedBusses)))
        self.Header = ["Res^2"]
        for n in range(1, (headerLength + 1)):
            self.Header.append(("B" + str(n)))
        #self.Header.append()
            
            
    def PrepData(self):
        """This function prepares the data for output, here the OP data can be 
        tailored, each row is extended with the null marker 'X' until it is the
        same length as the header. This function differenciates between a
        single row of data and a number of rows of data and handles them
        appropriately"""
        if type(self.DataOP[0]) == list:
            
            DataHold = []
            for Row in self.DataOP:
                RowHold = []
                for Cell in Row:
                    if type(Cell) == float:
                        RowHold.append(Cell)
                    elif type(Cell) == str:
                        RowHold.append((str(Cell)))
                    else:
                        print("potential error", Row)
                while len(RowHold) < len(self.Header):
                    RowHold.append('-')
                DataHold.append(RowHold)
            self.DataOP = DataHold
            DataHold, Row, Cell = None, None, None
        elif type(self.DataOP[0]) == str or isinstance(self.DataOP, Number):
            RowHold = []
            for Cell in self.DataOP:
                if type(Cell) == float:
                    RowHold.append(Cell)
                elif type(Cell) == str:
                    RowHold.append((str(Cell[1:])))
                else:
                    print("potential error", self.DataOP)
            while len(RowHold) < len(self.Header):
                RowHold.append('-')
            self.DataOP = RowHold
            
        else:
            print('Error? self.DataOP =', self.DataOP)
            
    def MakeFileName(self): 
        if len(self.ExcludedBusses) > 0:
            ExFiles = 'Busses '
            for Num in self.ExcludedBusses:
                ExFiles += ' ' + str(Num)
            ExFiles += ' Excluded '
        else:
            ExFiles = ' '
            
        start = self.ip_filename.index('\\') + 1
        filename = self.ip_filename[start:-4]
        
        if self.VeryParsimonious == True:
            self.OPcsvFileName = self.op_directory + "Output/" + filename + "_" +str(self.TargetValue) + " Very Parsimonius Table - degree " + str(self.PolynomialDegree) + ' ' + ExFiles + ".csv"
            if self.GenMetaData == True:
                self.MetaOPcsvFileName = self.op_directory + "MetaData/" + filename + "_" +str(self.TargetValue) + " Coeff for Very Parsimonius Table - degree " + ' ' + str(self.PolynomialDegree) + ExFiles + ".csv"
            if self.VerboseOP == True:
                self.VerboseOPcsvFileName = self.op_directory + "VerboseOutput/" + filename + "_" +str(self.TargetValue) + " Verbose Parsimonius Table - degree " + ' ' + str(self.PolynomialDegree) + ExFiles + ".csv"
                
        else:
            self.OPcsvFileName = self.op_directory + "Output/" + filename + "_" +str(self.TargetValue) + " Parsimonius Table - degree " + str(self.PolynomialDegree) + ' ' + ExFiles + ".csv"
            if self.GenMetaData == True:
                self.MetaOPcsvFileName = self.op_directory + "MetaData/" + filename + "_" +str(self.TargetValue) + " Coeff for Parsimonius Table - degree " + ' ' + str(self.PolynomialDegree) + ExFiles + ".csv"
            if self.VerboseOP == True:
                self.VerboseOPcsvFileName = self.op_directory + "VerboseOutput/" + filename + "_" +str(self.TargetValue) + " Verbose Parsimonius Table - degree " + ' ' + str(self.PolynomialDegree) + ExFiles + ".csv"
                
        
    def WriteAllToCSV(self):
        """This function writes all the data, including headers, at the same
        time, this is good for stable code, but if a crash is likly then line
        by line can be more desirable"""
        self.MakeHeader()
        self.PrepData()
        self.DataOP = [self.Header] + self.DataOP
        self.MakeFileName()
        print("writing to")
        print(self.OPcsvFileName)
                
        with open(self.OPcsvFileName, 'w', newline = '') as opFile:
            writer = csv.writer(opFile, delimiter = ',')
            for row in self.DataOP:
                writer.writerow(row)
            
        if self.GenMetaData == True:
            HeaderAux = ['Formula', 'Intercept']
            for n in range(1, (self.PolynomialDegree + 1)):
                HeaderAux.append(('x^'+ str(n)))
            self.MetaDataOP = [HeaderAux] + self.MetaDataOP
            with open(self.MetaOPcsvFileName, 'w', newline = '') as opFile:
                writer = csv.writer(opFile, delimiter = ',')
                for row in self.MetaDataOP:
                    writer.writerow(row)
                    
        if self.VerboseOP == True:
            with open(self.VerboseOPcsvFileName, 'w', newline = '') as opFile:
                writer = csv.writer(opFile, delimiter = ',')
                for row in self.VerboseDataOP:
                    writer.writerow(row)
                
    def WriteHeaderToCSV(self):
        """This function writes a header to a new file, if there is an existing
        file with that name it will be over written. This function is used when
        appending a single line to a file, more tollerant of crashes."""
        self.MakeHeader()
        self.MakeFileName()
        
        with open(self.OPcsvFileName, 'w', newline = '') as opFile:
            writer = csv.writer(opFile, delimiter = ',')
            writer.writerow(self.Header)
            
        if self.GenMetaData == True:
            HeaderAux = ['Formula', 'Intercept']
            for n in range(1, (self.PolynomialDegree + 1)):
                HeaderAux.append(('x^'+ str(n)))
            with open(self.MetaOPcsvFileName, 'w', newline = '') as opFile:
                writer = csv.writer(opFile, delimiter = ',')
                writer.writerow(HeaderAux)
            
    def WriteLineCSV(self):
        """This function writes a single line of data to the specified file, if
        code is prone to crash then cashed data is not lost. Actually it is the
        data from a single sweep, if 1 PMU is removed, revealing a new state, 
        then two PMUs are added, with each being a new state, then as many as
        three lines might be added."""
        self.PrepData()        
        
        with open(self.OPcsvFileName, 'a', newline = '') as opFile:
            writer = csv.writer(opFile, delimiter = ',')
            for row in self.DataOP:
                writer.writerow(row)
            
        if self.GenMetaData == True:
            with open(self.MetaOPcsvFileName, 'w', newline = '') as opFile:
                writer = csv.writer(opFile, delimiter = ',')
                for row in self.MetaDataOP:
                    writer.writerow(row)
            
class FileItterator(OPsupportFunctions):
    """This looks in the root folder self.working_directory, pulls out all the
    csv files, and carries out PMU placement on them. The details of specific
    files to be tested can be specified in self.ModelsToTest = ['IEEE 9', 
    'Whole', 'other string that appears in file name']"""
    def __init__(self):
        OPsupportFunctions.__init__(self)
        
    def ItterateAllFiles(self):
        self.filenames()
        for self.ip_filename in self.ip_filenames_list:
            print("###### Starting on", self.ip_filename, "######")
            self.Rread()
            print("       Data Loaded")
            self.PlaceAllPMUs()
            self.WriteAllToCSV()
            self.Reset()
            
    def FailoverAllFiles(self):
        self.filenames()
        for self.ip_filename in self.ip_filenames_list:
            n = 0
            while n < 3:
                try:                    
                    print("###### Starting on", self.ip_filename[17:], "######")
                    self.Rread()
                    print("       Data Loaded")
                    self.PlaceAllPMUs()
                    self.WriteAllToCSV()
                    self.Reset()
                    n = 4
                except:
                    n += 1
                    print('~~~~~~~~~~~~############~~~~~~~~~~~~~~~')
                    print('          failed', n, 'time')
                    print('~~~~~~~~~~~~############~~~~~~~~~~~~~~~')
                    self.Reset()
                    
            
    def IttAllLineByLine(self):
        self.filenames()
        #self.Reset()
        print('test list', self.ip_filenames_list)
        for self.ip_filename in self.ip_filenames_list:
            print("###### Starting on", self.ip_filename[17:], "#######")
            self.Rread()
            print("       Data Loaded")
            self.WriteHeaderToCSV()
            print('writing to')
            print(self.OPcsvFileName)
            #try:
            while (len(self.PlacedPMUs)-1) < self.MaxPMUs and \
            (len(self.PlacedPMUs) - 1) < (len(self.Xheaders)
            - len(self.ExcludedBusses)):
                   self.PlaceSinglePMU()
                   self.WriteLineCSV()
                       
                       
#            except:
#                print "!!!!!!!!!!!!   Failure   !!!!!!!!!!!!!!!"
#                print "Probably failed on"
#                print self.formula
#            self.Reset()

if __name__ == '__main__':
    run = FileItterator()
#    run.ModelsToTest = [' 30 O']
#    run.ExcludedBusses = ['X1']
    run.ItterateAllFiles() 
    #run.IttAllLineByLine()
    #run.FailoverAllFiles()
    
    print('Endeetoe')