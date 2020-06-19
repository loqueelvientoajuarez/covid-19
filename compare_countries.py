#! /usr/bin/env python3

from datahandling import build_international_data_set, get_country_data

import re
import numpy as np
from matplotlib import pylab as plt
import argparse 
from cycler import cycler
from unicodedata import normalize
import os

GRAPHICSDIR = "graphics"

# OK, I should learn how to do that with a proper library
TEXT = {
    'fr': {
        'death': ('deces', 'deces'),
        'recovered': ('recupere', 'recupes'),
        'case': ('cas', 'cas'),
        'duplication': ('double tous les 3 jours',
                        'double chaque semaine'),
        'since': 'jours depuis le {}e {}',
        'total': 'nombre total de {}',
        'new': 'nouveaux {} en 24h',
        'newcum': 'nouveaux {}  les {} derniers jours',
    },
    'es': {
        'death': ('muerto', 'muertos'),
        'recovered': ('recuperado', 'recuperados'),
        'case': ('caso', 'casos'),
        'duplication': ('se duplica cada 3 días',
                        'se duplica cada semana'),
        'since': 'días desde el {0}⁰ {1}',
        'total': 'numero total de {}',
        'new': '{} en el ultimo día',
        'newcum': '{} en los últimos {} días',
    },
    'en': {
        'death': ('death', 'deaths'),
        'recovered': ('recupery', 'recoveries'),
        'case': ('case', 'cases'),
        'duplication': ('doubles every 3 days',
                        'doubles every week'),
        'since': 'days since {}th {}',
        'total': 'total {}',
        'new': 'new {} in the last day',
        'newcum': 'new {} in the last {} days',
    },
}

def strip_accents(s):
    return normalize('NFD', '10⁰').encode('ascii', 'ignore').decode('utf-8')

def get_text(lang, what, number=None, strip=False):
    text = TEXT[lang][what]
    if number in [1, 'singular']:
        text = text[0]
    elif number in [2, 'plural']:
        text = text[1]
    if strip:
        text = normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8') 
    return text


def country_comparison_plot(tab, countries, variable, 
        date_origin=200, nbin=7, logy=False, trend=False, cum=False,
        lang='es', style='classic'):
    strip = arg.style == 'xkcd' # xkcd style can't do unicode
    if arg.style == 'xkcd':
        plt.xkcd()
    else:
        plt.style.use(arg.style)
    sing = get_text(lang, variable, 'singular', strip=strip)
    plur = get_text(lang, variable, 'plural', strip=strip)
    variablepl = get_text('en', variable, 'plural')
    print('Plotting {} for {}'.format(variable, ', '.join(countries)))
    fig = plt.figure(1)
    fig.clf()
    # fig.subplots_adjust(top=0.98,bottom=0.11, right=0.98)
    ax = fig.add_subplot(111)
    since = get_text(lang, 'since', strip=strip)
    ax.set_xlabel(since.format(date_origin, sing))
    if nbin == 1:
        if cum:
            total = get_text(lang, 'total', strip=strip)
            ax.set_ylabel(total.format(plur))
        else:
            new = get_text(lang, 'new', strip=strip)
            ax.set_ylabel(new.format(plur))
    else:
        newcum = get_text(lang, 'newcum', strip=strip)
        ax.set_ylabel(newcum.format(plur, nbin))
    if logy:
        print('Using log scale for y')
        ax.set_yscale('symlog', linthreshy=1)
    else:
        ax.set_yscale('linear')
    bgcolor = ax.get_facecolor()
    for i, country in enumerate(countries):
        date, value = get_country_data(tab, country, variablepl,    
                        cum=cum, nbin=nbin, date_origin=date_origin)
        if not len(date):
            print('    {} skipped: no enough {}'.format(country, variablepl)) 
            continue
        y0 = np.interp(0, date, value)
        p = ax.plot(date, value)
        ax.text(date[-1] + 2, value[-1], country, 
            color=p[0].get_color(), ha='left', va='center',
            bbox=dict(facecolor=bgcolor, alpha=0.5, pad=0, lw=0))
        print('   ', country, value[-1])
    ax.set_xlim(-7, ax.get_xlim()[1])
    if logy:
        ax.set_ylim(1, 10 ** np.ceil(np.log10(ax.get_ylim()[1])))
    else:
        ax.set_ylim(*ax.get_ylim())
    if trend:
        d = np.linspace(-7, ax.get_xlim()[1])
        dup3 = get_text(lang, 'duplication', 1, strip=strip)
        dup7 = get_text(lang, 'duplication', 2, strip=strip)
        ax.plot(d, y0*2**(d/3), 'c:', label=dup3, zorder=-1)
        ax.plot(d, y0*2**(d/7), 'g:', label=dup7, zorder=-1)
        ax.legend()
    fig.tight_layout()
    return fig

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=
        'Plot the evolution of daily or total covid-19 statistics for selected'
        ' countries'
    )
    parser.add_argument('-c', '--countries', nargs='+',
        default=['IT', 'ES', 'FR', 'US', 'GB', 'DE', 'BR', 'CL'],
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
        default=7,
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
    parser.add_argument('--lang', default='en', 
        choices=['en', 'es', 'fr'],
        help='language',
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
        default='JohnHopkins', choices=['EU', 'JohnHopkins'],
        help='data source'
    )
    parser.add_argument('--style',
        default='fivethirtyeight', choices=plt.style.available + ['xkcd'],
        help='plot style'
    )
    parser.add_argument('--debug',
        action='store_true', default=False,
        help='debug mode (internal error message displayed)'
    )
    arg = parser.parse_args()
    # output file
    if arg.output is None:
        pdfname = 'covid-19-international-{}s.{}'.format(arg.variable, arg.fmt)
    else:
        pdfname = arg.output 
    # bin
    try:
        tab = build_international_data_set(source=arg.source)
        fig = country_comparison_plot(tab, arg.countries, arg.variable, 
                date_origin=arg.origin, logy=arg.logy,  
                nbin=arg.nbin, cum=arg.cum, trend=arg.trend,
                lang=arg.lang, style=arg.style)
        os.makedirs(GRAPHICSDIR, exist_ok=True)
        pdfname = os.path.join(GRAPHICSDIR, pdfname) 
        fig.savefig(pdfname)
    except Exception as e:
        print('error:', e)
        if arg.debug:
            raise e

