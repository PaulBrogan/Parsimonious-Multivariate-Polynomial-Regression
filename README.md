Is this meant to run as a module? 
Not really more of a standalone, maybe it could be hacked together?

# 1 dependancies, you need R: on your computer ( https://www.r-project.org/ )
# and RPi2 installed also ( http://rpy.sourceforge.net/rpy2/doc-2.4/html/introduction.html )

## after that, fire the data you want to analyse in the */inputFolder*.

The first line of the CSV is interpreted as the headers and everything under 
that is treated as a column of data, if the data cannot be interpreted as a 
float, then it is rejected.

The code can be run from the main method ParsimoniousPlacement.py or from QuickRun.py

## I recommend starting from the QuickRun.py file and identifying the variables that are useful.


More comment is available in the code, but the basic run method goes like this (I use power
system data in this example as it is what I work with).

1. Specify the data you want to predict (in the test case CO2 intensity, 
beware that the name can change when pushed into R:, but an error in the console will flag this, especially be ware "/" things, 
as they can mess up the file name),
if no data is provided or the header is not found, then the first column is taken as the target value.

2. Run the code. A polynomial regression is carried out between the column of data of interest and all the other
columns. The best column is kept. The polynomial degree of the regress (e.g. a degree of 3 is a.x^3 + b.x^2 +c.x + d)
is specified in both scripts.

3. The data of interest is regressed against the best column found and every other column in the file,
the combination that returns the lowest residual squared (R2) value is kept. This the the 
multi-variate bit of the mouthful of a name I gave it.

4. When more than 3 multi-variate columns are chosen, then comes the parsimonious bit. Each
column of data is removed and if a better combination is found, it is kept; e.g. if a state with 
4 new variables gives a lower R2 value than the
previous best state with 4 variables, then it is kept and is used as the new base line, this is printed to 
console as "new diminished state", if you just end up back where you stated you get a message
"retrograde PMU removal, undone". This is described below with an example.

5. When finished processing - data and metadata gets dumped to files in the output folder, */Output* dat 
just tell you the best predictors, in the other folders you can see the actual functions and the coefficients
of these functions; these can be the important bits. 

6. This procedure can handle large files 200,000+ rows 200+ columns, but sometimes R: throws an
error if the vector (column) is too big.

## Ignore all the PMU stuff and Bus stuff, that is just what I first applied this to, electrical power engineering stuff.



# Understanding the output from the example data

## if you look in opFolder/Output

You can see the R2 value in the first column, in the example case this increases from 0.391 (poor correlation) to 
0.997 (very good correlation) with additional variables (be careful of variables derived from the 
regression term e.g. CO2 output in this case)

What follows are the headers of the columns used to regress the data.

When the columns step back in, then a better state has been found e.g.

*Res^2	B1	B2	B3	B4	B5	B6*

*0.682797694	Generation.SNSP	Source.Peat.MW	Source.Coal.MW	-*

*0.905049808	Generation.SNSP	Source.Peat.MW	Source.Coal.MW	Generation.Renewable.MW*

*0.893238172	Source.Peat.MW	Source.Coal.MW	Generation.Renewable.MW	-*

*0.922944377	Source.Peat.MW	Source.Coal.MW	Generation.Renewable.MW	Source.Gas.MW*

a significant improvement can be observed for the same number of variables

Interpretation - SNSP (system non-synchronous penetration) is a good predictor initially
but can be dropped in favour of Peat, coal and renewable generation as predictors of CO2 output


## if you look in opFolder/MetaData

This tells you the formula used in R: to carry out the regression, if you were/are using R:
directly, then this is what you would type in

*CO2.Intensity.kg.MW ~ poly( Source.Peat.MW, 2, raw = TRUE) + poly(Source.Coal.MW, 2, raw = TRUE) + poly(Generation.Renewable.MW, 2, raw = TRUE)*

The first column in here is the y intercept, in the case given it tends to 430 kg of CO2 per Megawatt hour
this can be interpreted as 430 kg_CO2/MWh would be released if all else were zero, this is a silly
idea, actually this value is the average value over the year and the other variables bias it away from this.

The following columns give the coefficients, if the coefficient are positive they place an upward trend on the
emissions (e.g. peat and coal) and if they are negative they place a downward trend (e.g. wind).  

*0.424266429.x1^2	-0.000490119.x1	0.144415952 x3^2	-2.98E-05.x2	-0.169283874.x3^2	3.68E-05.x3*



## if you are feeling brave, look in opFolder/VerboseOutput

This documents every regression carried out, along with formula and coefficients.

It is definitely worth a look.