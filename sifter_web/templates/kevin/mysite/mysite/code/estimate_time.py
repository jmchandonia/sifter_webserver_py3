import matplotlib.pyplot as plt
import numpy as np
import os
import pickle
import sqlite3
from math import log10
from numpy import array, linalg, ones
from scipy import misc, stats

from chartit import DataPool, Chart
from graphs.models import ErrorHistogramBarsTmp

# Paths to various files
runningTimeFile = '/lab/app/python/python_mohammad/SIFTER_jobs/CAFA/running_time.pickle'
myFile = os.path.dirname(__file__)
runningTimeNCFile = os.path.join(myFile, 'running_time_nc.pickle')
dataDictFile = os.path.join(myFile, 'data_dict.pickle')
paramsDictFile = os.path.join(myFile, 'params_dict.pickle')
dividersFile = os.path.join(myFile, 'dividers.pickle')
errDictFile = os.path.join(myFile, 'err_dict.pickle')
percentileDictFile = os.path.join(myFile, 'percentile_dict.pickle')

# DATADICT['reg'] is a dictionary that maps tags to their corresponding values from DICT_TIME_NC.
# DATADICT['iea'] is a dictionary that maps tags to their corresponding values from DICT_TIME_NC_IEA.
dataDict = {}

# PARAMSDICT[CRIT] is an array of parameters of the least squares regression line
# for estimating processing time for criteria CRIT
paramsDict = {}
              
# List of dividers based upon the number of elements NUMEL in transition matrix
numelDivs = []

# List of dividers based upon the family size FAMSIZE
famSizeDivs = []

# ERRDICT[CAT] is a list of error data corresponding to the category CAT,
# where error = actual time / estimated time.
errDict = {}

# PERCENTILEDICT[CAT][PER] is the PERth percentile of the distribution of errors
# corresponding to the category CAT.
percentileDict = {}

# Returns the maximum number of simultaneous functions and the resulting number of elements
# in the transition matrix Q, where each gene has NUMTERMS candidate GO term functions,
# such that the width of Q is less than or equal to threshold THR.
def max_fun_possible(numTerms, thr=1500):
    width = 0
    for i in range(1, numTerms + 1):
        sum = width + misc.comb(numTerms, i, exact=1)
        if sum > thr:
            return [i - 1, pow(width, 2)]
        else:
            width = sum
    return [numTerms, pow(width, 2)]
    
# Returns the number of elements NUMEL in the transition matrix where each
# gene has a maximum of MAXFUN of the NUMTERMS candidate GO term functions.
# The formula is given by NUMEL = (sum from I = 1 to MAXFUN of (NUMTERMS choose I))^2
def calc_numel(numTerms, maxFun):
    return pow(sum([float(misc.comb(numTerms, i, exact=True)) for i in range(1, maxFun + 1)]), 2)
    
# Returns the criteria to which the data point with NUMTERMS candidate GO term functions
# and MAXFUN truncation factor belongs.
def get_criteria(numTerms, maxFun):
    if numTerms > 8:
        if maxFun > 1:
            return 1
        else:
            return 2
    else:
        return 3

# Returns the category to which the data point with NUMEL
# number of elements in transition matrix and family size FAMSIZE belongs.
def get_category(numel, famSize):
    n = sum(map(lambda x: numel > x, numelDivs))
    s = sum(map(lambda x: famSize > x, famSizeDivs))
    return (n, s)        

# Estimates the processing time for a species tree of family size FAMSIZE,
# where each gene has at most MAXFUN of the NUMTERMS candidate GO term functions.
def est_processing_time(numTerms, famSize, maxFun):
    numel = calc_numel(numTerms, maxFun)
    crit = get_criteria(numTerms, maxFun)
    line = paramsDict[crit]
    return pow(10, line[0]) * pow(numel, line[1]) * pow(famSize, line[2])

    

# Returns a dictionary PFAMDICT.
# PFAMDICT['reg'] is a list of pfam ids from DICT_TIME_NC that do not constitute noise.
# PFAMDICT['iea'] is a list of pfam ids from DICT_TIME_NC_IEA that do not constitute noise.
def get_pfams_dict():
    types = ('reg', 'iea')
    sourceDicts = (dict_time_nc, dict_time_nc_iea)
    pfamsDict = {}
    for i in range(len(types)):
        type = types[i]
        sourceDict = sourceDicts[i]
        pfamsDict[type] = []
        for pfam, res in sourceDict.iteritems():
            if res['time'] >= 2 and (res['term'] >= 9 or res['time'] >= 100 or res['size'] >= 1000):
                pfamsDict[type].append(pfam)
    return pfamsDict

# Returns if the pfam id with NUMTERMS candidate GO term functions, family size FAMSIZE,
# and processing time TIME should be included in generation of the parameters for
# estimating processing time.
def include_pfam(numTerms, famSize, time):
    return numTerms >= 9 or famSize >= 4000 or time <= 10
    
# Given the pfam ids in PFAMSDICT, adds the parameters for estimating processing time
# to PARAMSDICT[CRIT] for each criteria CRIT.
def get_params(pfamsDict):
    types = ('reg', 'iea')
    sourceDicts = (dict_time_nc, dict_time_nc_iea)
    crits = [1, 2, 3]
    
    # DATA[CRIT] maps tags 'logNumel', logFamSize', and 'logTime' to lists containing
    # the number of elements in transition matrix, family size, and processing time
    # of each pfam id in SOURCEDICTS with criteria CRIT.
    data = {}

    for crit in crits:
        data[crit] = {}
        for tag in ['logNumel', 'logFamSize', 'logTime']:
            data[crit][tag] = []

    for i in range(len(types)):
        type = types[i]
        sourceDict = sourceDicts[i]
        for pfam in pfamsDict[type]:
            res = sourceDict[pfam]
            numTerms = int(res['term'])
            famSize = int(res['size'])
            maxFun = int(res['max_fun'])
            numel = int(res['numel'])
            time = max(res['time'], 1.0) # set minimum time to 1.0 minutes
            crit = get_criteria(res['term'], res['max_fun'])
            if crit in crits and include_pfam(numTerms, famSize, time):
                data[crit]['logNumel'].append(log10(numel))
                data[crit]['logFamSize'].append(log10(famSize))
                data[crit]['logTime'].append(log10(time))

    for crit in crits:
        logNumels = data[crit]['logNumel']
        logFamSizes = data[crit]['logFamSize']
        logTimes = data[crit]['logTime']
        A = array([ones(len(logNumels)), logNumels, logFamSizes])
        params = linalg.lstsq(A.T, logTimes)[0] # obtaining the parameters
        paramsDict[crit] = array(params)    

# Returns if data point (LOGTIME, LOGETIME) corresponding to criteria CRITERIA is an
# outlier by a factor of FACTOR on the log-log graph of estimated time vs actual time.
def is_outlier(criteria, logTime, logETime, factor=10):
    logFactor = log10(factor)
    return logETime - logTime > logFactor or logETime - logTime < - logFactor \
        or (criteria == 2 and (logTime < 1 or logETime < 1 or logETime > 3)) \
        or (criteria == 3 and (logTime > 2.9 or logETime > 2))

# Returns a dictionary OUTLIERSDICT.
# OUTLIERSDICT['reg'] is a list of pfam ids from DICT_TIME_NC that are outliers
# on the graph of estimated time vs actual time.
# OUTLIERSDICT['iea'] is a list of pfam ids from DICT_TIME_NC_IEA that are outliers
# on the graph of estimated time vs actual time.
def get_outliers():
    types = ('reg', 'iea')
    sourceDicts = (dict_time_nc, dict_time_nc_iea)
    outliersDict = {}
    
    get_params(pfamsDict)
    
    for i in range(len(types)):
        type = types[i]
        sourceDict = sourceDicts[i]
        outliersDict[type] = []
        for pfam, res in sourceDict.iteritems():
            numTerms = int(res['term'])
            famSize = int(res['size'])
            maxFun = int(res['max_fun'])
            time = res['time']
            eTime = est_processing_time(numTerms, famSize, maxFun)
            crit = get_criteria(numTerms, maxFun)
            if is_outlier(crit, log10(time), log10(eTime)):
                outliersDict[type].append(pfam)
    return outliersDict

# Removes the outliers from PFAMSDICT.
def remove_outliers():
    types = ('reg', 'iea')
    for type in types:
        pfamsDict[type] = [pfam for pfam in pfamsDict[type] if pfam not in outliersDict[type]]

# Returns a dictionary DATADICT.
# DATADICT['reg'] is a dictionary that maps tags to their corresponding values from DICT_TIME_NC.
# DATADICT['iea'] is a dictionary that maps tags to their corresponding values from DICT_TIME_NC_IEA.
# Includes tags 'numTerms', 'famSize', 'maxFun', 'numel', and 'time'.
def get_data_dict(pfamsDict):
    types = ('reg', 'iea')
    sourceDicts = (dict_time_nc, dict_time_nc_iea)
    dataDict = {}
    oldTags = ('term', 'size', 'max_fun', 'numel')
    newTags = ('numTerms', 'famSize', 'maxFun', 'numel')
    for i in range(len(types)):
        type = types[i]
        sourceDict = sourceDicts[i]
        dataDict[type] = {}
        for pfam in pfamsDict[type]:
            dataDict[type][pfam] = {}
            for j in range(len(oldTags)):
                dataDict[type][pfam][newTags[j]] = int(sourceDict[pfam][oldTags[j]])
            dataDict[type][pfam]['time'] = sourceDict[pfam]['time']
    return dataDict

# Returns two lists NUMELLIST and FAMSIZELIST of the number of elements in transition matrix
# and family size for pfam ids in DATADICT.
def get_numels_famSizes(dataDict):
    types = ('reg', 'iea')
    numelList = []
    famSizeList = []
    for type in types:
        numelList.extend([d['numel'] for d in dataDict[type].values()])
        famSizeList.extend([d['famSize'] for d in dataDict[type].values()])
    return (numelList, famSizeList)    
    
# Returns two lists of dividers NUMELDIVS and FAMSIZEDIVS to partition
# NUMELLIST and FAMSIZELIST into N categories each, forming a total of N^2 categories.
def get_dividers(numelList, sizeList, n):
    numelDivs = []
    famSizeDivs = []
    for i in range(1, n):
        per = 100 * float(i) / float(n)
        numelDivs.append(stats.scoreatpercentile(numelList, per))
        famSizeDivs.append(stats.scoreatpercentile(sizeList, per))
    return (numelDivs, famSizeDivs)    

# Adds the error (actual time / estimated time) of each pfam id in DATADICT
# to ERRDICT[CAT] weighted by the family size FAMSIZE, where CAT is the numel-famSize category.
def calc_errs(dataDict):
    for type in dataDict:
        for pfam in dataDict[type]:
            res = dataDict[type][pfam]
            numTerms = res['numTerms']
            famSize = res['famSize']
            maxFun = res['maxFun']
            numel = res['numel']
            time = res['time']
            eTime = est_processing_time(numTerms, famSize, maxFun)
            cat = get_category(numel, famSize)
            if cat not in errDict:
                errDict[cat] = []
            err = time / eTime
            errDict[cat].append((err, famSize))
            
# Stores the PERth percentile of the distribution of errors corresponding to the category CAT
# in PERCENTILEDICT[CAT][PER] for each percentile in the list PERS.
# corresponding to the category CAT.
def calc_upper_bounds(pers):
    for cat in errDict:
        percentileDict[cat] = {}
        errs = []
        for (err, famSize) in errDict[cat]:
            errs.extend([err,] * famSize)
        for per in pers:
            percentileDict[cat][per] = stats.scoreatpercentile(errs, per)
            
def store_hist_bars_old():
    if len(ErrorHistogramBarsTmp.objects.all()) == 0:
        low = 0
        numBins = 50
        for cat in errDict:
            errs = []
            for (err, famSize) in errDict[cat]:
                errs.extend([err,] * famSize)
            high = max(errs) + (max(errs) - min(errs)) * 0.02
            fig, ax = plt.subplots()
            n, bins, patches = plt.hist(errs, bins=np.linspace(low, high, numBins))
            for i in range(numBins - 1):
                h = ErrorHistogramBarsTmp.objects.create(numelCat=cat[0], famSizeCat=cat[1], bin=bins[i], barHeight=n[i])
                h.save()


### Adapt to ErrorHistogramBars
def create_my_db(db_file):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    # Create table
    c.execute('''CREATE TABLE mytable(ancestor_id integer, descendant_id integer, PRIMARY KEY(ancestor_id, descendant_id))''')
   
    # Save (commit) the changes
    conn.commit()
    
    # We can also close the connection if we are done with it.
    # Just be sure any changes have been committed or they will be lost.
    conn.close()

def store_my_db(db_file,data):
        
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
 
    c.executemany("INSERT INTO descendants VALUES (?,?)",data)
    conn.commit()
    
    # We can also close the connection if we are done with it.
    # Just be sure any changes have been committed or they will be lost.
    conn.close()

                
def store_hist_bars():
    data = []
    low = 0
    numBins = 50
    for cat in errDict:
        errs = []
        for (err, famSize) in errDict[cat]:
            errs.extend([err,] * famSize)
        high = max(errs) + (max(errs) - min(errs)) * 0.02
        fig, ax = plt.subplots()
        n, bins, patches = plt.hist(errs, bins=np.linspace(low, high, numBins))
        binWidth = bins[1] - bins[0]
        bins = array([x + binWidth / 2 for x in bins[:-1]])
        for i in range(numBins):
            data.append([cat[0], cat[1], bins[i], n[i]])
        # Connect to db
            
# Returns the PERth confidence upper bound of the estimated time ETIME, in minutes.
# The formula is ETIME * X, where X is the PERth percentile of the distribution of errors
# corresponding to the category CAT.
def get_upper_bound(eTime, cat, per):
    return eTime * percentileDict[cat][per]

# Setup DATADICT, PARAMSDICT, the dividers NUMELDIVS and FAMSIZEDIVS, ERRDICT, and PERCENTILEDICT.
if os.path.exists(dataDictFile):
    [dataDict] = pickle.load(open(dataDictFile, 'rb'))
    [paramsDict] = pickle.load(open(paramsDictFile, 'rb'))
    [numelDivs, famSizeDivs] = pickle.load(open(dividersFile, 'rb'))
    [errDict] = pickle.load(open(errDictFile, 'rb'))
    [percentileDict] = pickle.load(open(percentileDictFile, 'rb'))
else:
    if os.path.exists(runningTimeNCFile):
        [dict_time_nc, dict_time_nc_iea] = pickle.load(open(runningTimeNCFile, 'rb'))
    else:
        [dict_time, dict_time2, dict_time_iea, dict_time2_iea, dict_time_nc, dict_time_nc_iea] \
            = pickle.load(open(runningTimeFile,'rb'))
    pfamsDict = get_pfams_dict()
    outliersDict = get_outliers()
    remove_outliers()
    dataDict = get_data_dict(pfamsDict)
    get_params(pfamsDict)
    (numelList, sizeList) = get_numels_famSizes(dataDict)
    (numelDivs, famSizeDivs) = get_dividers(numelList, sizeList, 4)
    calc_errs(dataDict)
    calc_upper_bounds([95, 99.9])
    pickle.dump([dataDict], open(dataDictFile, 'wb'))
    pickle.dump([paramsDict], open(paramsDictFile, 'wb'))
    pickle.dump([numelDivs, famSizeDivs], open(dividersFile, 'wb'))
    pickle.dump([errDict], open(errDictFile, 'wb'))
    pickle.dump([percentileDict], open(percentileDictFile, 'wb'))
    
store_hist_bars_old() ###
    
# Returns the times in TIMES, given in minutes, in consistent units, rounded to EST decimal places.
def format_times(times):
    if not times:
        return times
    t = times[0]
    if t < 1:
        return ['%.1f seconds' % (60 * t) for t in times]
    elif t < 60:
        return ['%.1f minutes' % t for t in times]
    elif t < 60 * 24:
        return ['%.1f hours' % (t / 60) for t in times]
    elif t < 60 * 24 * 365:
        return ['%.1f days' % (t / 60 / 24) for t in times]
    else:
        return ['%.1f years' % (t / 60 / 24 / 365) for t in times]

def plot_histogram(eTime, cat):
    def xScale(err):
        return round(eTime * err, 1)

    # Step 1: Create a DataPool with the data we want to retrieve
    histData = DataPool(
        series = [{
            'options': {
                'source': ErrorHistogramBarsTmp.objects.filter(numelCat=cat[0]).filter(famSizeCat=cat[1]),
            },
            'terms': ['bin', 'barHeight'],
        }]
    )
    
    # Step 2: Create the Chart object
    histogram = Chart(
        datasource = histData,
        series_options = [{
            'options': {
                'type': 'column',
                'pointPadding': 0,
                'borderWidth': 0,
                'groupPadding': 0,
                'shadow': False,
                'stacking': False,
            },
            'terms':{
                'bin': ['barHeight',],
            },
        }],
        chart_options = {
            'title': {
                'style': {'color': '#000000', 'font-size': '40px'},
                'text': 'Distribution of estimated time',
            },
            'xAxis': {
                'labels': {
                    'style': {'color': '#000000', 'font-size': '20px'},
                },
                'plotLines': [{
                    'color': 'orange',
                    'value': 14,
                    'width': 2,
                    'zIndex': 5,
                }],
                'tickColor': '#000000',
                'tickInterval': 5,
                'tickmarkPlacement': 'between',
                'title': {
                    'style': {'color': '#000000', 'font-size': '30px'},
                    'text': 'Estimated time',
                },
            },
            'yAxis': {
                'gridLineColor': '#FFFFFF',
                'labels': {
                    'enabled': False,
                },
                'title': {
                    'style': {'color': '#000000', 'font-size': '30px'},
                    'text': 'Probability',
                },
            },
        },
        x_sortf_mapf_mts = (None, xScale, False)
    )
    return histogram
        
def estimate_time(numTerms, famSize):
    tableHeader = ['Truncation factor', 'Estimated time (hours)', 'Estimated time',
                   '95% Confidence upper bound', '99.9% Confidence upper bound']
    tableBody = []
    pers = [95, 99.9]
    for i in range(1, numTerms + 1):
        numel = calc_numel(numTerms, i)
        eTime = est_processing_time(numTerms, famSize, i)
        eTime = max(eTime, 1.0) # set minimum estimated time to 1 minute
        cat = get_category(numel, famSize)
        if round(eTime / 60.0, 1) == 0:
            row = [i, "%.2f" % (eTime / 60.0)]
        else:
            row = [i, "%.1f" % (eTime / 60.0)]
        times = [eTime]
        for j in range(len(pers)):
            upper = get_upper_bound(eTime, cat, pers[j])
            times.append(upper)
        row.extend(format_times(times))
        tableBody.append(row)

    histogram = plot_histogram(eTime, cat)
    return (tableHeader, tableBody, histogram)
    
def get_processing_time(pfam):
    if pfam in dataDict['reg']:
        numTerms = dataDict['reg'][pfam]['numTerms']
        famSize = dataDict['reg'][pfam]['famSize']
        return estimate_time(numTerms, famSize)
    else:
        return ([], [[]], None)
