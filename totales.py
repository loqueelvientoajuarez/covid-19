#! /usr/bin/env python3

import os
import re
import numpy as np
from astropy.io import ascii
from matplotlib import pylab as plt
from matplotlib.dates import MO, WeekdayLocator, DateFormatter
from datahandling import read_time_series

def plot_date(axis, x, y, label, *a, **ka):
    line = axis.plot(x, y, *a, **ka)[0]
    color = line.get_color()
    axis.set_ylabel(label, color=color)
    axis.tick_params(axis='y', colors=color)
    # ax.spines['right'].set_color(color)

def plot_tests(style=None):

    cols = [0, -2]
    test_d, test_t = read_time_series(17, header_lines=2, columns=cols)
    cols = ['Fecha', 'Casos totales', 'Fallecidos']
    case_d, case_t, death_t = read_time_series(5, columns=cols)
    # weekly average 
    test_n = (test_t[7:] - test_t[:-7]) / 7
    case_n = (case_t[7:] - case_t[:-7]) / 7
    death_n = (death_t[7:] - death_t[:-7]) / 7
    case_d = [np.datetime64(d) for d in case_d[7:]]
    test_d = [np.datetime64(d) for d in test_d[7:]]
    # positivity rate 
    pos_n = case_n[-len(test_n):] / test_n * 100

    fig = plt.figure(1)
    fig.clf()
    if style:
        plt.style.use(style)
    
    ax = fig.add_subplot(111)
    plot_date(ax, case_d, case_n, 'nuevos casos')
    ax.set_ylim(0, max(case_n) * 1.02)
    day = np.timedelta64('1', 'D')
    ax.set_xlim(min(case_d) - day, max(case_d) + day)
    
    ax3 = ax.twinx()
    ax3.plot([], [])
    ax3.plot([], [])
    plot_date(ax3, case_d, death_n, 'nuevos fallecimientos')
    ax3.set_ylim(0, max(death_n) * 1.4)
   
    ax2 = ax.twinx()
    ax2.spines['right'].set_position(('axes', 1.2))
    ax2.plot([], []) # advance the colour cycler
    plot_date(ax2, test_d, pos_n, 'positividad de PCR [%]')
    ax2.set_ylim(0, max(pos_n) * 1.1)
    

    
    ax4 = ax.twiny()
    ax4.set_xlabel('estadísticas diarias (promedio semanal).')
    ax4.set_xticklabels([])
 
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
        ax4.grid(False)
        ax.grid(axis='x', which='both')
    #ax.grid(axis='y')
    fig.tight_layout()
    fig.show()
    
    fig.savefig('graphics/casos-chile.png')    

plot_tests(style='fivethirtyeight')
