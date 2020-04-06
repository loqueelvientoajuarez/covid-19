#! /usr/bin/env python3

import argparse
import numpy as np
from matplotlib import pylab as plt

from datahandling import retrieve_data_set, get_country_data

def plot_country(country, cum=False, logy=False):
    tab = retrieve_data_set(source='JohnHopkins')
    date, cases = get_country_data(tab, country, 'cases', cum=cum)
    date, deaths = get_country_data(tab, country, 'deaths', cum=cum)
    date, recov = get_country_data(tab, country, 'recoveries', cum=cum)
    active = cases - deaths - recov
    fig = plt.figure(1)
    fig.clf()
    ax = fig.add_subplot(111)
    if logy:
        ax.set_yscale('symlog', linthreshy=1)
    ax.set_xlabel('days')
    date = np.array(date) - date[0]
    if cum:
        ax.fill_between(date, 0, active, label='active cases')
        ax.fill_between(date, active, active + recov, label='recoveries')
        ax.fill_between(date, active + recov, cases, label='deaths')
    else:
        ax.plot(date, cases, label='new cases')
        ax.plot(date, deaths, label='deaths')
        ax.plot(date, recov, label='recoveries')
    ax.legend(loc='upper left', title='daily stats in {}'.format(country),
        fancybox=True)
    return fig

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=
        'Plot the evolution of daily or total covid-19 statistics for selected'
        ' country'
    )
    parser.add_argument('country',
        help='country names or codes'
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--binsize', type=int, dest='nbin',
        default=1,
        help='number of days binned together'
    )
    group.add_argument('--cum', '--total', action='store_true',
        default=False,
        help='Plot cumulated data instead of daily data'
    )
    parser.add_argument('--style',
        default='fivethirtyeight',
        help='plot style (classic, fivethirtyeight, xkcd, etc.)'
    )
    parser.add_argument('--debug',
        action='store_true', default=False,
        help='debug mode (internal error message displayed)'
    )
    parser.add_argument('--log', action='store_true',
        default=False,
        help='log plot'
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-o', dest='output', default=None,
        help='Output file'
    )
    group.add_argument('-f', '--format', dest='fmt',
        default='pdf',  choices=['png', 'pdf'],
        help='plot format (pdf or png)',
    )
    arg = parser.parse_args()
    # output file
    if arg.output is None:
        pdfname = 'covid-19-{}.{}'.format(arg.country, arg.fmt)
    else:
        pdfname = arg.output
    # bin
    try:
        if arg.style == 'xkcd':
            plt.xkcd()
        else:
            plt.style.use(arg.style)
        fig = plot_country(arg.country, logy=arg.log, cum=arg.cum)
        fig.tight_layout()
        fig.savefig(pdfname)
    except Exception as e:
        print('error:', e)
        if arg.debug:
            raise e
