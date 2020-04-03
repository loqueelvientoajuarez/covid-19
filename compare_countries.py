#! /usr/bin/env python3

from datahandling import retrieve_data_set, get_country_data

import re
import numpy as np
from matplotlib import pylab as plt
import argparse 
from cycler import cycler

def plural(variable):
    if variable == 'recovery':
        return 'recoveries'
    return variable + 's'

def country_comparison_plot(tab, countries, variable, 
        date_origin=200, nbin=7, logy=False, trend=False, cum=False):
    variablepl = plural(variable)
    print('Plotting {} for {}'.format(variablepl, ', '.join(countries)))
    fig = plt.figure(1)
    fig.clf()
    # fig.subplots_adjust(top=0.98,bottom=0.11, right=0.98)
    ax = fig.add_subplot(111)
    ax.set_xlabel('days since {}th {}'.format(date_origin, variable))
    if nbin == 1:
        if cum:
            ax.set_ylabel('total {}'.format(variablepl))
        else:
            ax.set_ylabel('new {} in the last day'.format(variablepl))
    else:
        ax.set_ylabel('new {} in the last {} days'.format(variablepl, nbin))
    if logy:
        ax.set_yscale('symlog', linthreshy=1)
    for i, country in enumerate(countries):
        date, value = get_country_data(tab, country, variablepl,    
                        cum=cum, nbin=nbin, date_origin=date_origin)
        if not len(date):
            print('    {} skipped: no enough {}'.format(country, variablepl)) 
            continue
        y0 = np.interp(0, date, value)
        p = ax.plot(date, value)
        ax.text(1.0 * date[-1], 1.01* value[-1], country, 
            color=p[0].get_color(), ha='left', va='bottom',
            bbox=dict(facecolor='white', alpha=0.5, pad=0, lw=0))
    ax.set_xlim(-7, ax.get_xlim()[1])
    if logy:
        ax.set_ylim(1, 10 ** np.ceil(np.log10(ax.get_ylim()[1])))
    else:
        ax.set_ylim(*ax.get_ylim())
    if trend:
        d = np.linspace(-7, ax.get_xlim()[1])
        ax.plot(d, y0*2**(d/3), 'c:', label='doubles every 3 days', zorder=-1)
        ax.plot(d, y0*2**(d/7), 'g:', label='doubles every week', zorder=-1)
        ax.legend()
    fig.tight_layout()
    return fig

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=
        'Plot the evolution of daily or total covid-19 statistics for selected'
        ' countries'
    )
    parser.add_argument('-c', '--countries', nargs='+',
        default=['ITA', 'ESP', 'FRA', 'USA', 'GBR', 'DEU'],
        help='country names or codes'
    )
    parser.add_argument('-s', '--stat', dest='variable',
        choices=['case', 'death', 'recovery'],
        default='case',
        help='statistic to display'
    )
    parser.add_argument('--origin', type=int, dest='origin', 
        default=50,
        help='given number of cases/deaths from which days are counted'
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--binsize', type=int, dest='nbin', 
        default=1,
        help='number of days binned together'
    )
    group.add_argument('--cumulated', '--total', action='store_true', dest='cum',
        default=False,
        help='plot the cumulated statistic instead of the daily one'
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-o', type=str, dest='output',
        default=None,
        help='filename to save to'
    )
    group.add_argument('-f', '--format', dest='fmt', 
        default='pdf',  choices=['png', 'pdf'],
        help='plot format (pdf or png)',
    )
    parser.add_argument('-l', '--log', action='store_true', dest='logy', 
        default=False,
        help='semilog plot (by default: linear)'
    )
    parser.add_argument('-t', '--trend', action='store_true', dest='trend', 
        default=False,
        help='plot growth trends for doubling every 2 days/week'
    )
    parser.add_argument('--source', 
        default='EU', choices=['EU', 'JohnHopkins'],
        help='data source'
    )
    parser.add_argument('--style',
        default='fivethirtyeight',
        help='plot style (classic, fivethirtyeight, xkcd, etc.)'
    )
    parser.add_argument('--debug',
        action='store_true', default=False,
        help='debug mode (internal error message displayed)'
    )
    arg = parser.parse_args()
    # output file
    if arg.output is None:
        pdfname = 'covid-19-{}s.{}'.format(arg.variable, arg.fmt)
    else:
        pdfname = arg.output 
    # bin
    try:
        tab = retrieve_data_set(source=arg.source)
        if arg.style == 'xkcd':
            plt.xkcd()
        else:
            plt.style.use(arg.style)
        fig = country_comparison_plot(tab, arg.countries, arg.variable, 
                date_origin=arg.origin, logy=arg.logy,  
                nbin=arg.nbin, cum=arg.cum, trend=arg.trend)
        fig.savefig(pdfname)
    except Exception as e:
        print('error:', e)
        if arg.debug:
            raise e
