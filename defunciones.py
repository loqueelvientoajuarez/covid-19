#! /usr/bin/env python3

from astropy.table import Table
from numpy import datetime64
import os
import numpy as np
from matplotlib import pylab as plt

from datahandling import retrieve_chilean_vitals 

POPULATION = {
    2010: 17.09,
    2011: 17.25,
    2012: 17.40,
    2013: 17.631,
    2014: 17.819,
    2015: 18.006,
    2016: 18.192,
    2017: 18.374,
    2018: 18.751,
    2019: 19.107,
    2020: 19.458310,
}

def weeknumber(date=None, binsize=7):
    if date is None:
        date = [str(np.datetime64('now'))]
    year = date[0][0:4]
    start = datetime64('{}-01-01'.format(year))
    day = [(datetime64(d) - start).item().days for d in date]
    return 1 + np.array(day) // binsize

def get_vital(year, vital='death', region=None, date=None):
    CODIGO_REGION = [str(i) for i in range(1, 17)]
    tab = retrieve_chilean_vitals(year, vital=vital)
    if region is not None:
        colname = 'Region'
        if isinstance(region, int) or region in CODIGO_REGION:
            colname = 'Codigo region'
        tab = tab[tab[colname] == region]
    date = tab['Fecha']
    values = tab.columns[4].data
    start = '{}-01-01'.format(year)
    week = weeknumber(date)
    value = np.array([np.sum(values[week == w]) for w in range(1, 53)])
    value = value / POPULATION[year]
    return np.array(value)

def compare_vital(vital='death', region=None, plot='all'):
    historical = [get_vital(year, vital=vital) for year in range(2010, 2020)]
    historical = np.array(historical)
    now = get_vital(2020)
    hmean = np.mean(historical, axis=0)
    hstd = np.std(historical, axis=0, ddof=1)
    excess = now - historical
    hplot = np.transpose(historical)
    thisweek = weeknumber()[0]
    nplot = now[:thisweek-1]
    nweek = np.arange(1, thisweek)
    startcovid = 10
    excess = excess[:,startcovid:thisweek-1] * POPULATION[2020]
    fig = plt.figure(1)
    fig.clf()
    ax = fig.add_subplot(111)
    week = np.arange(52) + 1
    if plot == 'all':
        ax.plot(week, hplot, lw=1, color=(.8,.8,.8), label='años pasados')
    ax.fill_between(week, hmean-hstd, hmean+hstd, color=(.7,.7,.7),
        label='dispersión 2010-2019') 
    ax.plot(week, hmean, color='k', label='promedio 2010-2019')
    ax.plot(nweek[startcovid:], nplot[startcovid:], 'r-', lw=2, label='2020')
    ax.plot(nweek[:startcovid+1], nplot[:startcovid+1], 'r:', lw=2)
    ax.set_xlabel('semana')
    ax.set_ylabel('fallecidos semanales por millón')
    ax.set_xlim(1, 52)
    ax.set_ylim(0, 1.1*max(nplot))
    ax.legend()
    ax2 = ax.twiny()
    ax2.set_xticks([])
    ax2.set_xlabel('mortalidad semanal en Chile 2010-2020')
    fig.tight_layout()
    fig.show()
    excess = excess.sum(axis=1)
    txt = 'exceso = {:.0f} ± {:.0f} fallecidos'.format(excess.mean(), excess.std())
    ax.text(0.02, 0.98, txt, ha='left', va='top', color='r', 
        transform=ax.transAxes)
    fig.savefig('graphics/mortalidad.png')
    return historical, now, excess

excess = compare_vital(plot='mean')
