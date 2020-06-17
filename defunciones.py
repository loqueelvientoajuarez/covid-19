#! /usr/bin/env python3

import locale
locale.setlocale(locale.LC_ALL, '')

from astropy.table import Table
from numpy import datetime64
import os
import numpy as np
from matplotlib import pylab as plt
from scipy.stats import linregress

from datahandling import retrieve_chilean_vitals 

POPULATION = {
    2010: 17.063927,
    2011: 17.254159,
    2012: 17.443491,
    2013: 17.611902,
    2014: 17.787617,
    2015: 17.971423,
    2016: 18.167147,
    2017: 18.419192,
    2018: 18.751405,
    2019: 19.107216,
    2020: 19.458310,
}

HALFDAY = np.timedelta64(12, 'h')
DAY = np.timedelta64(24, 'h')
THISYEAR = int(str(np.datetime64('now'))[0:4])

def bin_data(dates, values, binsize='month'):
    year = dates[0].item().year
    firstday = '01-01'
    lastday = str(max(dates))[5:10]
    if year < THISYEAR:
        lastday = '12-31'
    lastmonth = int(lastday[3:])
    first = np.datetime64('{}-{}'.format(year, firstday)) - HALFDAY
    last = np.datetime64('{}-{}'.format(year, lastday)) + HALFDAY
    if isinstance(binsize, int):
        bins = np.hstack([np.arange(first, last, binsize * DAY), last])
    elif binsize == 'month':
        bins = [first]
        for m in range(2, 13):
            monthstart = np.datetime64('{}-{:02}-01'.format(year, m))
            if monthstart < last:
                bins.append(monthstart - HALFDAY)
        bins.append(last)
        bins = np.array(bins)
    width = np.array([s.item().days for s in np.diff(bins)])
    if width[-1] < width[-2] / 2:
        width[-2] += width[-1]
        width = width[:-1]
        bins = np.delete(bins, -2)
    if width[0] < width[1] / 2:
        width[1] += width[0]
        width = width[1:]
        bins = np.delete(bins, 1)
    centres = bins[:-1] + width * DAY / 2
    binned_values, unused = np.histogram(dates, bins=bins, weights=values) 
    binned_values = binned_values / width
    return centres, width, binned_values
     

def weeknumber(date=None, binsize=7):
    if date is None:
        date = [str(np.datetime64('now'))]
    year = date[0][0:4]
    start = datetime64('{}-01-01'.format(year))
    day = [(datetime64(d) - start).item().days for d in date]
    return 1 + np.array(day) // binsize

def get_vital(year, vital='death', region=None, binsize='month'):
    CODIGO_REGION = [str(i) for i in range(1, 17)]
    tab = retrieve_chilean_vitals(year, vital=vital, overwrite=year == 2020)
    if region is not None:
        colname = 'Region'
        if isinstance(region, int) or region in CODIGO_REGION:
            colname = 'Codigo region'
        tab = tab[tab[colname] == region]
    dates = np.array([np.datetime64(d) for d in tab['Fecha']])
    values = tab.columns[4].data
    centres, width, binned_values = bin_data(dates, values, 
        binsize=binsize)
    return centres, width, binned_values

def mortality_rate_correction(past_years, past_widths, past_values):
    past_mortalities = np.array([sum(w*v)/sum(w) / POPULATION[y] 
        for w, v, y in zip(past_widths, past_values, past_years)])
    a, b, *unused = linregress(past_years, past_mortalities)
    mortality_now = a * (past_years[-1] + 1) + b
    correction = mortality_now / (a * past_years + b) 
    return correction

def transpose_date(dates):
    dates = ['2020-' + (str(d)[5:10]) for d in dates]
    dates = np.array([np.datetime64(d) for d in dates])
    return dates

def plot_vital(past, present,
        vital='death', plotall=False, plotexcess=False, fignum=1):
    from matplotlib import pylab as plt
    from matplotlib.dates import DateFormatter, MonthLocator
    dates, binwidths, mortality = present
    past_dates, past_binwidths, past_mortality = past
    fig = plt.figure(fignum)
    fig.clf()
    ax = fig.add_subplot(111)
    rfact = 365 / 1000
    if plotall:
        for d, m in zip(past_dates, past_mortality):
            year = d[0].item().year
            plotdates = transpose_date(d)
            ax.plot(plotdates, m * 365/1000, 'k-', label=str(year), lw=1)
    m = np.sort(past_mortality, axis=0)[1:-1]
    mean = m.mean(axis=0)
    std = m.std(axis=0,ddof=1) 
    maxi = m.max(axis=0)
    mini = m.min(axis=0) 
    plotdates = transpose_date(past_dates[0])
    end = dates[-1] + binwidths[-1] * DAY / 2
    now = end.item().strftime('%d\\ %b')
    ax.plot(plotdates, mean * rfact, 'k-', 
            label='promedio 2010-2019')
    ax.fill_between(plotdates, mini * rfact, maxi * rfact, fc=(.4,.4,.4,.5),
        label='intervalo de confianza (80%)')
    ax.plot(plotdates, rfact * past_mortality.max(axis=0), 'k--', lw=.5)
    ax.plot(plotdates, rfact * past_mortality.min(axis=0), 'k--', lw=.5, 
        label='extremos 2010-2019')
    year = dates[0].item().year
    plotdates = transpose_date(dates)
    ax.plot(plotdates, mortality * 365/1000, 'r-', lw=3, label=str(year))
    ax.xaxis.set_major_formatter(DateFormatter('%d/%m'))
    ax.xaxis.set_major_locator(MonthLocator(bymonthday=15))
    ax.legend(loc='lower left')
    max_mortality = max(past_mortality.max(), mortality.max())
    ax.set_ylim(0, 1.1 * max_mortality * 365/1000)
    ymax = ax.get_ylim()[1]
    ax.set_xlim(np.datetime64('2020-01-01'), np.datetime64('2021-01-01'))
    ax.set_ylabel('tasa de mortalidad anualizada [‰]')
    ax2 = ax.twinx()
    ax2.set_ylim(0, ymax * 1000 / 365 * POPULATION[2020])
    ax2.set_ylabel('muertes diarias (2020)'.format(vital))
    ax3 = ax.twiny()
    ax3.set_xticks([])
    ax3.set_xlabel('Fallecimientos en Chile. Datos históricos corregidos de la tendencia secular.'.format(vital))
    if plotexcess:
        keep = np.argwhere(dates >= np.datetime64('2020-04-01'))[:,0]
        fact = binwidths[keep] * POPULATION[2020]
        begin = dates[keep][0] - binwidths[keep][0] * DAY / 2
        begin = begin.item().strftime('%d %b') 
        excess = np.sum((mortality[keep] - mean[keep]) * fact)
        errinf = np.sum((maxi[keep] - mean[keep]) * fact)
        errsup = np.sum((mean[keep] - mini[keep]) * fact)
        what = f'exceso\\ de\\ fallecimientos\\ ({begin}-{now})'
        FMT = '$\\mathrm{{{}}}: {:.0f}^{{{:+.0f}}}_{{{:+.0f}}}$'
        txt = FMT.format(what, excess, errsup, -errinf)
        ax.text(0.01, 0.99, txt, va='top',
            transform=ax.transAxes)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.show()
    fig.savefig('graphics/{}-statistics.png'.format(vital))

def load_vital(vital='death', region=None, correction=False, binsize='month'):
    past_years = np.arange(2010, 2020)
    past = [get_vital(year, vital=vital, binsize=binsize) 
        for year in range(2010, 2020)]
    past = list(zip(*past))
    past_dates, past_binwidths, past_values = past 
    past_mortality = np.array([v / POPULATION[y] 
                            for y, v in zip(past_years, past_values)])
    present = get_vital(2020, vital=vital, binsize=binsize)
    dates, binwidths, values = present
    mortality = values / POPULATION[2020]
    if correction:
        corr = mortality_rate_correction(past_years, past_binwidths, 
            past_values)
        past_mortality *= corr[:,None]
    past = (past_dates, past_binwidths, past_mortality)
    present = (dates, binwidths, mortality)
    return past, present
    

def compare_this_year(vital='death', plot='', correction=True, binsize=14):
    past, present = load_vital(vital=vital, correction=correction, 
            binsize=binsize)
    plot_vital(past, present, plotexcess=True, vital=vital, plotall=plot == 'all')
    return past, present

past, present = compare_this_year(binsize=14)

