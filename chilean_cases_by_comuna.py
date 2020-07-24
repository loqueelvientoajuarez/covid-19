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
YESTERDAY = np.datetime64('today') - 1

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
    def __exit__(self, *args):
        pass

def display_trend(ax, dates, values, threshold=10):
    if min(values) < 1 or max(values) < threshold:
        return ''
    x = (dates - dates[0]) / DAY 
    y = np.log2(values)
    a, b, *unused = linregress(x, y)
    x = np.arange(dates[0], NOW, HOUR)   
    y = 2**(b + a * (x-x[0]) / DAY)
    ax.plot(x, y, 'k--', zorder=2)
    if abs(a) >= 1/60:
        return f" {'×' if a>0 else '/'}2 en {1/abs(a):.2g} días"
    else:
        return ' ≃ estable'

def plot_page(tabs, nrows=7, ncols=4, page=0, trend=False):
    (tab_t, tab_a, tab_s) = tabs
    dates_t = [np.datetime64(d) for d in tab_t.colnames[5:-1]]
    dates_a = [np.datetime64(d) for d in tab_a.colnames[5:]]
    dates_s = [np.datetime64(d) for d in tab_s.colnames[5:]]
    xlabels = np.arange(dates_s[0], TOMORROW)[::14]
    naxes = nrows * ncols
    maxcases = max(r[-2] for r in tab_t
                        if r['Poblacion'] is not np.ma.masked)
    maxperm = max(1000 * r[-2] / r['Poblacion'] for r in tab_t
                        if r['Poblacion'] is not np.ma.masked)
    # plot data
    fig = plt.figure(1 + page, figsize=(8.5,11))    
    fig.clf()
    axes = fig.subplots(nrows, ncols, sharex=False, sharey=False)
    k = 0
    for (row_t, row_a, row_s) in zip(
            tab_t[page*naxes:(page+1)*naxes],
            tab_a[page*naxes:(page+1)*naxes],
            tab_s[page*naxes:(page+1)*naxes]):
        cases_t = list(row_t)[5:-1]
        cases_a = list(row_a)[5:]
        poblacion = row_t['Poblacion']
        comuna = row_t['Comuna']
        if poblacion is np.ma.masked:
            continue
        ax = axes[k // ncols][k % ncols]
        print(comuna, dates_t[-1], cases_t[-1])
        # no x
        ax.set_xlim(dates_s[0], TOMORROW)
        ax.set_xticks([])
        # set the absolute yscale
        y2max = 1.2 * maxperm
        ymax = maxperm * poblacion / 1000
        ymin = 0.2
        y2min = 1000 * ymin / poblacion
        ax.set_ylim(0, ymax)
        ax.set_yscale('symlog', linthreshy=ymin)
        yt = np.array([1, 10, 100, 1000, 10000])
        yt = yt[(ymin <= yt)*(yt <= ymax)]
        ax.set_yticks(yt)
        ax.set_yticklabels([str(y) for y in yt])
        # set the % yscale
        ax2 = ax.twinx()
        ax2.set_ylim(0, y2max)
        ax2.set_yscale('symlog', linthreshy=y2min)
        yt = np.array([.01, .1, 1, 10, 100])
        yt = yt[(y2min <= yt)*(yt <= y2max)]
        ax2.set_yticks(yt)
        ax2.set_yticklabels([f"{y:.4g}‰" for y in yt])
        # plot trends
        ct, ca = cases_t[-1], cases_a[-1]
        pt, pa = ct > 1, ca > 1
        text_t = f"{ct} caso{'s' if pt else ''} total{'es' if pt else ''}"
        text_t += display_trend(ax, dates_t[-4:], cases_t[-4:], threshold=10)
        text_a = f"{ca} caso{'s' if pa else ''} activo{'s' if pa else ''}" 
        text_a += display_trend(ax, dates_a[-4:], cases_a[-4:], threshold=10)
        # plot data
        ax.plot(dates_t, cases_t, 'o', mfc=(.5,.5,.5), mec=(.3,.3,.3), ms=3,
            label=text_t, zorder=1)
        ax.plot(dates_a, cases_a, 'o', mfc=(.5,.5,.9), mec=(.3,.3,.9), ms=3,
            label=text_a, zorder=1)
        ax.legend(fontsize=9, loc=3, fancybox=False, labelspacing=.3,
            handletextpad=0, handlelength=1.2, frameon=False)
        ax.text(0.03, 0.97, comuna, 
                va='top', transform=ax.transAxes, fontsize=10)
        k += 1
    for j in range(k, naxes):
        print('void graph', j)
        ax = axes[j // ncols][j % ncols]
        ax.axis('off')
    for j in range(k-2, k):
        # set the dates
        ax = axes[j // ncols][j % ncols]
        ax.set_xticks(xlabels)
        xl = [str(d)[-2:] + "/" + str(d)[-5:-3] for d in xlabels]
        ax.set_xticklabels(xl, rotation=75, ha='right')
        
    fig.tight_layout(pad=2)
    fig.subplots_adjust(hspace=0)
    return fig

def plot_region(region, filename=None, trend=False, overwrite=False, date=None):
    # total and active cases by comuna
    tabs = retrieve_chilean_region(region, overwrite=overwrite, date=date)
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
            parser.add_argument('--date', '-d', default=str(YESTERDAY),
                help='Date of report'
            )
            parser.add_argument('--overwrite', '-o', default=False,
                action="store_true",
                help='Overwrite files'
            )
            parser.add_argument('--style', '-s', default='fivethirtyeight',
                choices=plt.style.available + ['xkcd'],
                help='Plotting style'
            )
            args = parser.parse_args()
            with PlotStyle(args.style):
                for r in args.regions:
                    print('Region', r)
                    f = 'covid-by-chilean-comuna-region={}.pdf'.format(r)
                    figs = plot_region(r, f, trend=args.trend, 
                        overwrite=args.overwrite, date=args.date)
    except Exception as e:
        print('{}: error: {}'.format(sys.argv[0], e))
        raise e
