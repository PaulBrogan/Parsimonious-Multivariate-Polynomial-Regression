# -*- coding: utf-8 -*-
"""
Created on Thu Apr 27 14:58:13 2017

@author: pbrogan
"""

import ParsimoniusPlacement as PP

PP = PP.FileItterator()

PP.TargetValue = 'CO2.Intensity.kg.MW'

#poly degree can be an integer or a list of integers
PolynomialDegree = [2]

MaxPlacements = 6

PP.TestParticularModels = False
#PP.ModelsToTest = ['regressMe']   #only applied when testing particular files

PP.MaxPMUs = MaxPlacements

PP.working_directory = 'inputFolder/'
PP.op_directory = "opFolder/" 

if type(PolynomialDegree) == int:
    PolynomialDegree = [PolynomialDegree] 
    
if type(PolynomialDegree) == list:
    for PD in PolynomialDegree:
        if type(PD) == float:
            PD = int(PD)
        if type(PD) == int:
            PP.PolynomialDegree = PD
            PP.ItterateAllFiles() 
        else:
            print('error in Polynomial Degree input - should be an interger')
        