#from scipy import misc
import numpy as np
from estimatedb.models import Allsifterdata, Errorhistogrambars, Percentiles

try:
    from chartit import DataPool, Chart
except ImportError:
    DataPool = None
    Chart = None

# PARAMSDICT[CRIT] is an array of parameters of the least squares regression line
# for estimating processing time for criteria CRIT
paramsDict = {1: [-6.6940979152046394, 1.2175437752942884,   0.61437156459022535],
              2: [-3.6107074614976109, 0.91343454244972999,  0.45521131812635984],
              3: [-2.7026843343076519, 0.052132418536663394, 0.93755721899494526]}

# List of dividers based upon the number of elements NUMEL in transition matrix
numelDivs = [65025.0, 330625.0, 1046529.0]

# List of dividers based upon the family size FAMSIZE
famSizeDivs = [567.0, 1637.0, 4989.0]


def comb(N, k, exact=False, repetition=False):
    """
    The number of combinations of N things taken k at a time.
    This is often expressed as "N choose k".
    Parameters
    ----------
    N : int, ndarray
        Number of things.
    k : int, ndarray
        Number of elements taken.
    exact : bool, optional
        If `exact` is False, then floating point precision is used, otherwise
        exact long integer is computed.
    repetition : bool, optional
        If `repetition` is True, then the number of combinations with
        repetition is computed.
    Returns
    -------
    val : int, ndarray
        The total number of combinations.
    Notes
    -----
    - Array arguments accepted only for exact=False case.
    - If k > N, N < 0, or k < 0, then a 0 is returned.
    Examples
    --------
    >>> k = np.array([3, 4])
    >>> n = np.array([10, 10])
    >>> sc.comb(n, k, exact=False)
    array([ 120.,  210.])
    >>> sc.comb(10, 3, exact=True)
    120L
    >>> sc.comb(10, 3, exact=True, repetition=True)
    220L
    """
    if repetition:
        return comb(N + k - 1, k, exact)
    if exact:
        N = int(N)
        k = int(k)
        if (k > N) or (N < 0) or (k < 0):
            return 0
        val = 1
        for j in range(min(k, N-k)):
            val = (val*(N-j))//(j+1)
        return val
    else:
        k,N = asarray(k), asarray(N)
        cond = (k <= N) & (N >= 0) & (k >= 0)
        vals = binom(N, k)
        if isinstance(vals, np.ndarray):
            vals[~cond] = 0
        elif not cond:
            vals = np.float64(0)
        return vals

# Returns the maximum number of simultaneous functions and the resulting number of elements
# in the transition matrix Q, where each gene has NUMTERMS candidate GO term functions,
# such that the width of Q is less than or equal to threshold THR.
def max_fun_possible(numTerms, thr=1500):
    width = 0
    for i in range(1, numTerms + 1):
        sum = width + comb(numTerms, i, exact=1)
        if sum > thr:
            return [i - 1, pow(width, 2)]
        else:
            width = sum
    return [numTerms, pow(width, 2)]
    
# Returns the number of elements NUMEL in the transition matrix where each
# gene has a maximum of MAXFUN of the NUMTERMS candidate GO term functions.
# The formula is given by NUMEL = (sum from I = 1 to MAXFUN of (NUMTERMS choose I))^2
def calc_numel(numTerms, maxFun):
    return pow(sum([float(comb(numTerms, i, exact=True)) for i in range(1, maxFun + 1)]), 2)
    
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

# Returns the PERth confidence upper bound of the estimated time ETIME, in minutes.
# The formula is ETIME * X, where X is the PERth percentile of the distribution of errors
# corresponding to the category CAT.
def get_upper_bound(eTime, cat, per):
    percentiles = Percentiles.objects.filter(numelcat=cat[0]).filter(famsizecat=cat[1])
    if per == 95:
        return eTime * percentiles[0].per95
    else:
        return eTime * percentiles[0].per999
    
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

# Plots the estimated time distribution by scaling the error distribution of category CAT
# by estimated time ETIME.
def plot_histogram(eTime, cat):
    if DataPool is None or Chart is None:
        return None

    def xScale(err):
        return round(eTime * err * factor, 1)
        
    data = Errorhistogrambars.objects.filter(numelcat=cat[0]).filter(famsizecat=cat[1])
    percentiles = Percentiles.objects.filter(numelcat=cat[0]).filter(famsizecat=cat[1])
    bins = sorted([d.bin for d in data])
    binStart = bins[0]
    binWidth = bins[1] - bins[0]
    times = format_times([eTime, percentiles[0].per95 * eTime, percentiles[0].per999 * eTime])
    units = times[0].split(' ')[-1]
    factor = {'seconds': 60, 'minutes': 1, 'hours': 1.0 / 60, 'days': 1.0 / 60 / 24, 'years': 1.0 / 60 / 24 / 365}[units]
    lines = [(1, 'estimated time: %s' % times[0]),
             (percentiles[0].per95, '95%% confidence: %s' % times[1]),
             (percentiles[0].per999, '99.9%% confidence: %s' % times[2])]
    
    # Step 1: Create a DataPool with the data we want to retrieve
    histData = DataPool(
        series = [{
            'options': {
                'source': data,
            },
            'terms': ['bin', 'barheight'],
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
                'bin': ['barheight',],
            },
        }],
        chart_options = {
            'title': {
                'style': {'color': '#000000', 'font-size': '20px'},
                'text': 'Distribution of estimated time',
            },
            'xAxis': {
                'labels': {
                    'style': {'color': '#000000', 'font-size': '15px'},
                },
                'plotLines': [{
                    'color': 'orange',
                    'label': {'rotation': -90, 'style': {'font-size': '12px',}, 'text': line[1], 'align':'right' , 'x':-10, 'y':10},
                    'value': (line[0] - binStart) / binWidth,
                    'width': 2,
                    'zIndex': 5,
                } for line in lines],
                'tickColor': '#000000',
                'tickInterval': 5,
                'tickmarkPlacement': 'between',
                'title': {
                    'style': {'color': '#000000', 'font-size': '15px'},
                    'text': 'Time (%s)' % units,
                },
            },
            'yAxis': {
                'gridLineColor': '#FFFFFF',
                'labels': {
                    'enabled': False,
                },
                'title': {    
                    'style': {'color': '#000000', 'font-size': '15px'},
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
    histograms = []
    pers = [95, 99.9]
    cutoff = 1  # displayed table cuts off after eTime > 2 years
    stop_next=0
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
        # if estimated time <= 2 years
        if eTime <= 2 * 365 * 24 * 60:
            cutoff += 1
        else:
            stop_next+=1
        tableBody.append(row)
        histogram = plot_histogram(eTime, cat)
        if histogram is not None:
            histograms.append(histogram)
        if stop_next==1:
            break
    
    chartContainers = ','.join(['hist_container%i' % i for i in range(1, cutoff)])        
    return (tableHeader, tableBody[:cutoff], histograms, chartContainers, numTerms,famSize)
    
def get_processing_time(pfam):
    data = Allsifterdata.objects.filter(type='reg').filter(pfam=pfam)
    if pfam.startswith('PF') and len(data) > 0:
        return estimate_time(data[0].numterms, data[0].famsize)
    else:
        return ([], [[]], [], '', 0,0)
