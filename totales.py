#! /usr/bin/env python3

import os
import re
import numpy as np
from astropy.io import ascii
from matplotlib import pylab as plt
from matplotlib.dates import MO, WeekdayLocator, DateFormatter
from datahandling import read_time_series


def week_average(x, y):
    ndays = 7
    l = len(y)
    ymean = np.mean([y[ndays-1-i:l-i] for i in range(ndays)], axis=0)
    x = x[ndays-1:]
    return x, ymean

def plot_date(axis, x, y, label, *a, **ka):
    line = axis.plot(x, y, *a, **ka)[0]
    color = line.get_color()
    axis.set_ylabel(label, color=color)
    axis.tick_params(axis='y', colors=color)
    # ax.spines['right'].set_color(color)


def plot_tests(style=None):

    cols = [0, -2, -1]
    test_d, test_t, test_n = read_time_series(17, header_lines=2, columns=cols)
    cols = ['Fecha', 'Casos totales', 'Casos nuevos totales']
    case_d, case_t, case_n = read_time_series(5, columns=cols)
    case_d, case_n = week_average(case_d, case_n)
    test_d, test_n = week_average(test_d, test_n)
    pos_n = case_n[-len(test_n):] / test_n * 100
    case_d = [np.datetime64(d) for d in case_d]
    test_d = [np.datetime64(d) for d in test_d]

    fig = plt.figure(1)
    fig.clf()
    if style:
        plt.style.use(style)
    
    ax = fig.add_subplot(111)
    plot_date(ax, case_d, case_n, 'casos nuevos diarios')
    ax.set_ylim(0, max(case_n) * 1.02)
    ax.set_xlim(min(case_d), max(case_d))
   
    ax2 = ax.twinx()
    ax2.plot([], []) # advance the colour cycler
    plot_date(ax2, test_d, pos_n, 'positividad de PCR [%]')
    ax2.set_ylim(0, max(pos_n) * 1.1)
    
    ax3 = ax.twiny()
    ax3.set_xlabel('Casos y testeo en Chile.  Promedio última semana.')
    ax3.set_xticklabels([])
 
    ax.tick_params(axis='x', rotation=30)
    ax.xaxis.set_major_locator(WeekdayLocator(byweekday=MO, interval=2))
    ax.xaxis.set_minor_locator(WeekdayLocator(byweekday=MO, interval=1))
    ax.xaxis.set_major_formatter(DateFormatter('Lun. %d/%m'))
    for label in ax.get_xticklabels():
        label.set_ha('right')

    if style == 'fivethirtyeight':
        ax.grid(False)
        ax2.grid(False)
        ax3.grid(False)
        ax.grid(axis='x', which='both')
    #ax.grid(axis='y')
    fig.tight_layout()
    fig.show()
    
    fig.savefig('graphics/casos-chile.png')    

plot_tests(style='fivethirtyeight')
