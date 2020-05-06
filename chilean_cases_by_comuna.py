#! /usr/bin/env python3

from astropy.table import Table
from matplotlib import pylab as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import argparse
import sys
import os
from scipy.stats import linregress
from datahandling import retrieve_chilean_region

GRAPHICSDIR = "graphics"

def plot_page(tabs, nrows=7, ncols=4, page=0, trend=False):
    (tab, tab2) = tabs
    dates = [np.datetime64(d) for d in tab.colnames[5:-1]]
    dates2 = [np.datetime64(d) for d in tab2.colnames[5:]]
    n = len(tab)
    now = np.datetime64('now')
    tomorrow = np.datetime64('today') + 1
    xlabels = np.arange(dates[0], dates[-1])[-1::-7]
    day = np.timedelta64(1, 'D')
    hour = np.timedelta64(1, 'h')
    days = (dates[-1] - dates[0]) / day
    maxcases = 0
    last_dates = dates[-4:]
    last_dates2 = dates2[-4:]
    naxes = nrows * ncols
    maxcases = max(tab.columns[-2])
    # plot data
    fig = plt.figure(1 + page, figsize=(8.5,11))    
    fig.clf()
    axes = fig.subplots(nrows, ncols, sharex=True, sharey=True)
    for i, (row, row2) in enumerate(zip(
            tab[page*naxes:(page+1)*naxes],
            tab2[page*naxes:(page+1)*naxes])):
        ax = axes[i // ncols][i % ncols]
        comuna = row['Comuna']
        cases = list(row)[5:-1]
        cases2 = list(row2)[5:]
        ax.plot(dates, cases, 'o', mfc=(.5,.5,.5), mec=(.3,.3,.3))
        ax.plot(dates2, cases2, 'o', mfc=(.5,.5,1.), mec=(.3,.3,1.))
        ax.set_ylim(1, ax.get_ylim()[1])
        ax.text(0.03, 0.97, comuna, va='top', transform=ax.transAxes, fontsize=8)
        pl = {False: '', True: 's'}
        total = '{} total case{}'.format(cases[-1], pl[cases[-1]>1])
        active = '{} active case{}'.format(cases2[-1], pl[cases2[-1]>1])
        last_cases = cases[-4:]
        if trend and max(last_cases) > 10 and min(last_cases) > 0:
            x = (last_dates - last_dates[0]) / day
            y = np.log2(last_cases)
            a, b, *unused = linregress(x, y)
            if a == 0:
                c, τ = 2**b, 1e6
            else:
                c, τ = 2**b, 1 / a
            x = np.arange(last_dates[0], now, hour)   
            y = c * 2**((x-x[0])/day / τ)
            if  τ > 0 and τ < 30:
                ax.plot(x, y, 'k--')
                total += ' ×2 in {:.2g} days'.format(τ)
            elif abs(τ) >= 30:
                ax.plot(x, y, 'b--')
                total += ' ≃ stable'
            last_cases2 = cases2[-4:]
            if max(last_cases2) > 10 and min(last_cases2) > 1:
                x = (last_dates2 - last_dates2[0]) / day
                y = np.log2(last_cases2)
                a, b, *unused = linregress(x, y)
                if a == 0:
                    c, τ = 2**b, 1e6
                else:
                    c, τ = 2**b, 1 / a
                x = np.arange(last_dates2[0], now, hour)   
                y = c * 2**((x-x[0])/day / τ)
                if τ > 0 and τ < 30:
                    ax.plot(x, y, 'b--')
                    active += ' ×2 in {:.2g} days'.format(τ)
                elif abs(τ) >= 30:
                    ax.plot(x, y, 'b--')
                    active += ' ≃ stable'
        ax.text(0.03, 0.06, active, transform=ax.transAxes, 
                            fontsize=8, color=(.3,.3,1.))
        ax.text(0.03, 0.15, total, transform=ax.transAxes, 
                    fontsize=8, color=(.3,.3,.3))
    # axes decoration
    for c in range(ncols):
        ax = axes[nrows - 1][c]
        ax.set_xticks(xlabels)
        ax.set_xticklabels(xlabels, rotation=60, ha='right')
        ax.set_xlim(dates[0], tomorrow)
    for r in range(nrows):
        ax = axes[r][0]
        ax.set_ylim(0, 1.2 * maxcases)
        ax.set_yscale('symlog', linthreshy=1)
        ax.set_yticks([1, 10, 100, 1000])
        ax.set_yticklabels(["1", "10", "100", "1000"])
    # plot trend
    fig.tight_layout(pad=2)
    fig.subplots_adjust(hspace=0, wspace=0)
    return fig

def plot_region(region, filename, trend=False):
    tab, tab2 = retrieve_chilean_region(region)
    # plot dimensions 4 x 7 or smaller if fits in one page
    ncols = int(round(np.sqrt(4 * len(tab) / 7)))
    nrows = int(np.ceil(len(tab) / ncols))
    if nrows > 7 or ncols > 4:
        ncols = 4
        nrows = 7
    naxes = nrows * ncols
    npages = 1 + (len(tab) - 1)//naxes 
    # do the plotting
    filename = os.path.join(GRAPHICSDIR, filename)
    os.makedirs(GRAPHICSDIR, exist_ok=True)
    figs = []
    with PdfPages(filename) as pdf:
        for page in range(npages):
            fig = plot_page((tab, tab2), nrows, ncols, page, trend=trend)
            pdf.savefig(fig)
            figs.append(fig)
        d = pdf.infodict()
        d['Title'] = 'Covid-19 cases in Chilean region {}'.format(region)
        d['Author'] = 'Régis Lachaume'
    return figs 
   
if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="COVID-19 cases by Chilean comuna from the bi/triweekly epidemiological reports")
        parser.add_argument('regions', type=int, nargs="*", help='Region numbers.  All if not given.')
        parser.add_argument('--trend', '-t', default=False,
            action="store_true",
            help='Determine growth trend from last four reports')
        args = parser.parse_args()
        if len(args.regions) == 0:
            args.regions = np.arange(1, 17)
        for r in args.regions:
            f = 'covid-by-chilean-comuna-region={}.pdf'.format(r)
            figs = plot_region(r, f, trend=args.trend)
        for fig in figs:
            fig.show()
    except Exception as e:
        print('{}: error: {}'.format(sys.argv[0], e))
        raise e
