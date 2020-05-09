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
import __main__

GRAPHICSDIR = "graphics"
DAY = np.timedelta64(1, 'D')
HOUR = np.timedelta64(1, 'h')
NOW = np.datetime64('now')
TOMORROW = np.datetime64('today') + 1

class PlotStyle(object):
    def __init__(self, style):
        self._style = style
        self._object = None
    def __enter__(self):
        if self._style == 'xkcd':
            self._object = plt.xkcd()
        else:
            self._object = plt.style.context(self._style)
        return self._object

def display_trend(ax, dates, values, threshold=10):
    if min(values) < 1 or max(values) < threshold:
        return ''
    x = (dates - dates[0]) / DAY 
    y = np.log2(values)
    a, b, *unused = linregress(x, y)
    x = np.arange(dates[0], NOW, HOUR)   
    y = 2**(b + a * (x-x[0]) / DAY)
    ax.plot(x, y, 'k--')
    if  a >= 1/30:
        return ' ×2 in {:.2g} days'.format(1 / a)
    elif a <= -1/30:
        return ' /2 in {:.2g} days'.format(-1 / a)
    else:
        return ' ≃ stable'

def plot_page(tabs, nrows=7, ncols=4, page=0, trend=False):
    (tab_t, tab_a, tab_s) = tabs
    dates_t = [np.datetime64(d) for d in tab_t.colnames[5:-1]]
    dates_a = [np.datetime64(d) for d in tab_a.colnames[5:]]
    dates_s = [np.datetime64(d) for d in tab_s.colnames[5:]]
    xlabels = np.arange(dates_s[0], TOMORROW)[::14]
    naxes = nrows * ncols
    maxcases = max(tab_t.columns[-2])
    # plot data
    fig = plt.figure(1 + page, figsize=(8.5,11))    
    fig.clf()
    axes = fig.subplots(nrows, ncols, sharex=True, sharey=True)
    for i, (row_t, row_a, row_s) in enumerate(zip(
            tab_t[page*naxes:(page+1)*naxes],
            tab_a[page*naxes:(page+1)*naxes],
            tab_s[page*naxes:(page+1)*naxes])):
        ax = axes[i // ncols][i % ncols]
        comuna = row_t['Comuna']
        cases_t = list(row_t)[5:-1]
        cases_a = list(row_a)[5:]
        cases_s = np.cumsum(list(row_s)[5:])
        pl = {False: '', True: 's'}
        text_t = '{} total case{}'.format(cases_t[-1], pl[cases_t[-1]>1])
        text_t += display_trend(ax, dates_t[-4:], cases_t[-4:], threshold=10)
        text_a = '{} active case{}'.format(cases_a[-1], pl[cases_a[-1]>1])
        text_a += display_trend(ax, dates_a[-4:], cases_a[-4:], threshold=10)
        text_s = 'by date of symptoms'
        ax.plot(dates_t, cases_t, 'o', mfc=(.5,.5,.5), mec=(.3,.3,.3), ms=4,
            label=text_t)
        ax.plot(dates_s, cases_s, 's', mfc=(.2,.2,.2), mec=(.0,.0,.0), ms=3,
            label=text_s)
        ax.plot(dates_a, cases_a, 'o', mfc=(.5,.5,.9), mec=(.3,.3,.9), ms=4,
            label=text_a)
        ax.legend(fontsize=9, loc=3, fancybox=False, labelspacing=.3,
            handletextpad=0, handlelength=1.2, frameon=False)
        ax.text(0.03, 0.97, comuna, 
                va='top', transform=ax.transAxes, fontsize=10)
        #ax.text(0.03, 0.05, text_s, transform=ax.transAxes,
        #            fontsize=8, color=(.0,.0,.0))
        #ax.text(0.03, 0.13, text_t, transform=ax.transAxes, 
        #                    fontsize=8, color=(.3,.3,.3))
        #ax.text(0.03, 0.21, text_a, transform=ax.transAxes, 
        #            fontsize=8, color=(.3,.3,.7))
    # axes decoration
    for c in range(ncols):
        ax = axes[nrows - 1][c]
        ax.set_xticks(xlabels)
        xl = [str(d)[-2:] + "/" + str(d)[-5:-3] for d in xlabels]
        ax.set_xticklabels(xl, rotation=75, ha='right')
        ax.set_xlim(dates_s[0], TOMORROW)
    for r in range(nrows):
        ax = axes[r][0]
        ax.set_yscale('symlog', linthreshy=.2)
        ax.set_yticks([1, 10, 100, 1000, 10000])
        ax.set_yticklabels(["1", "10", "100", "1000", "10000"])
        ax.set_ylim(0, 1.2 * maxcases)
    # plot trend
    fig.tight_layout(pad=2)
    fig.subplots_adjust(hspace=0, wspace=0)
    return fig

def plot_region(region, filename=None, trend=False):
    # total and active cases by comuna
    tabs = retrieve_chilean_region(region)
    ncomunas = len(tabs[0])
    # plot dimensions 4 x 7 or smaller if fits in one page
    ncols = 2
    nrows = min(6, int(np.ceil(ncomunas/ncols)))
    naxes = nrows * ncols
    npages = 1 + (ncomunas - 1)//naxes 
    # do the plotting
    figs = [plot_page(tabs, nrows, ncols, page, trend=trend) 
                    for page in range(npages)]
    # save to PDF if given
    if filename:
        filename = os.path.join(GRAPHICSDIR, filename)
        os.makedirs(GRAPHICSDIR, exist_ok=True)
        with PdfPages(filename) as pdf:
            for fig in figs:
                pdf.savefig(fig)
            d = pdf.infodict()
            d['Title'] = 'Covid-19 cases in Chilean region {}'.format(region)
            d['Author'] = 'Régis Lachaume'
    return figs 
   
if __name__ == "__main__":
    try:
        DEBUG = False 
        if DEBUG:
            print("Plotting RM in interactive mode. No PDF is saved.")
            figs = plot_region(13, trend=True)
            for fig in figs:
                fig.show()
        else:
            parser = argparse.ArgumentParser(description="COVID-19 cases by Chilean comuna from the bi/triweekly epidemiological reports")
            parser.add_argument('--regions', '-r', type=int, nargs="+", 
                help='Region numbers', default=np.arange(1, 17))
            parser.add_argument('--trend', '-t', default=False,
                action="store_true",
                help='Determine growth trend from last four reports')
            parser.add_argument('--style', '-s', default='fivethirtyeight',
                choices=plt.style.available + ['xkcd'],
                help='Plotting style'
            )
            args = parser.parse_args()
            with PlotStyle(args.style):
                for r in args.regions:
                    print('Region', r)
                    f = 'covid-by-chilean-comuna-region={}.pdf'.format(r)
                    figs = plot_region(r, f, trend=args.trend)
    except Exception as e:
        print('{}: error: {}'.format(sys.argv[0], e))
        raise e
