#! /usr/bin/env python3

import os
import re
import time
import urllib.request
from astropy.io import ascii as asciitable
import numpy as np
import datetime
from matplotlib import pylab as plt
import argparse 
from cycler import cycler

def get_data(url, local, default_encoding='utf-8-sig', max_time=2 * 3600):
    # there should be a robust, built-in way to download stuff
    if (not os.path.exists(local) 
            or time.time() - os.path.getmtime(local) > max_time):
        print('Download data from', url)
        with urllib.request.urlopen(url) as response:
            encoding = response.headers.get_content_charset()
            if encoding is None: # 
                encoding = default_encoding 
            contents = response.read().decode(encoding)
        # we don't want to leave a half written file, so remove it
        # if write was interrupted.
        print('Write data to', local)
        try:
            with open(local, 'w') as fh:
                fh.write(contents)
        except KeyboardInterrupt as e: 
            # disk full also, but then it's the least of your worries ^^
            os.remove(local)
            raise e
    print('Read data from', local)
    data = asciitable.read(local)
    return data

def get_country_data(tab, country, variable):
    # country names or code?
    country_col = 'countriesAndTerritories'
    if re.match('^[A-Z]{2,3}[0-9]*$', country):
        country_col = 'countryterritoryCode'
        if len(country) != 3:
            country_col = 'geoId'
    tab = tab[tab[country_col] == country]
    if not len(tab):
        raise RuntimeError('no data for country ' + country)
    # why is dealing with dates such a pain?
    tab_date = [datetime.datetime.strptime(d, '%d/%m/%Y').timestamp() / 86_400
                 for d in tab['dateRep']]
    tab_value = tab[variable + 's'].tolist()
    # some dates may be missing
    date_range = np.arange(min(tab_date), max(tab_date) + 1)
    value = [tab_value.pop() if d in tab_date else 0 for d in date_range]
    return date_range, np.array(value)

def bin_data(date, value, date_origin=50, nbin=7):
    nbin = 7
    total = np.cumsum(value)
    if max(total) < date_origin:
        return np.array([]), np.array([])
    start = (len(value) + nbin - 1) % nbin
    binned = total[nbin:] - total[:-nbin]
    # we estimate when there was date_origin number of cases and
    # shift curve by that amount.
    date0 = np.interp(date_origin, total, date)
    date = (date - date0)[nbin:]
    return date, binned

def plot_countries(tab, countries, variable, 
        date_origin=200, nbin=7, logy=False, bw=False, trend=False):
    print('Plotting {} for {}'.format(variable + 's', ', '.join(countries)))
    mycycler = cycler(linestyle=['-', '--', '-.'])
    if bw:
        mycycler *= cycler(color=[(0, 0, 0), (.25, .25, .25), (.5, .5, .5)])
    else:
        mycycler *= cycler(color=['k', 'r', 'b', 'm']) 
    fig = plt.figure(1)
    fig.clf()
    fig.subplots_adjust(top=0.98,bottom=0.11, right=0.99)
    ax = fig.add_subplot(111)
    ax.set_xlabel('days since {}th {}'.format(date_origin, variable))
    ax.set_ylabel('new {}s in the last {} days'.format(variable, nbin))
    ax.set_prop_cycle(mycycler)
    if logy:
        ax.set_yscale('symlog', linthreshy=1)
    for i, country in enumerate(countries):
        date, value = get_country_data(tab, country, variable)
        date, value = bin_data(date, value, date_origin=date_origin)
        if not len(date):
            print('    {} skipped: no enough {}s'.format(country, variable)) 
            continue
        p = ax.plot(date, value)
        ax.text(1.01 * date[-1], 1.01 * value[-1], country, 
            color=p[0].get_color(),
            bbox=dict(facecolor='white', alpha=0.5, pad=1, lw=0))
    ax.set_xlim(-7, ax.get_xlim()[1])
    if logy:
        ax.set_ylim(1, 10 ** np.ceil(np.log10(ax.get_ylim()[1])))
    else:
        ax.set_ylim(*ax.get_ylim())
    if trend:
        d = np.linspace(-7, ax.get_xlim()[1])
        y0 = np.interp(0, date, value)
        ax.plot(d, y0*2**(d/3), 'c:', label='doubles every 3 days', zorder=-1)
        ax.plot(d, y0*2**(d/7), 'g:', label='doubles every week', zorder=-1)
        ax.legend()
    return fig

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Plot daily covid-19 statistics')
    parser.add_argument('-c', '--countries', nargs='+',
        default=['ITA', 'ESP', 'FRA', 'USA', 'GBR', 'DEU'],
        help='country names or codes'
    )
    parser.add_argument('-s', '--stat', dest='variable',
        choices=['case', 'death'],
        default='case',
        help='statistic to display'
    )
    parser.add_argument('--binsize', 
        default=7,
        help='number of days binned together'
    )
    parser.add_argument('-o', '--origin', type=int, dest='origin', 
        default=50,
        help='given number of cases/deaths from which days are counted'
    )
    parser.add_argument('-l', '--log', action='store_true', dest='logy', 
        default=False,
        help='semilog plot (by default: linear)'
    )
    parser.add_argument('-t', '--trend', action='store_true', dest='trend', 
        default=False,
        help='plot growth trends for doubling every 2 days/week'
    )
    parser.add_argument('-f', '--format', dest='fmt', 
        default='pdf',  choices=['png', 'pdf'],
        help='plot format (pdf or png)',
    )
    parser.add_argument('--bw', action='store_true', 
        default=False,  
        help='black & white plot',
    )
    arg = parser.parse_args()
    url = 'https://opendata.ecdc.europa.eu/covid19/casedistribution/csv'
    csvname = 'covid-19.csv'
    pdfname = 'covid-19-{}s.{}'.format(arg.variable, arg.fmt)
    try:
        tab = get_data(url, csvname, max_time=7200) # encoding changed overnight
        fig = plot_countries(tab, arg.countries, arg.variable, 
                date_origin=arg.origin, logy=arg.logy, bw=arg.bw,
                trend=arg.trend)
        fig.savefig(pdfname)
    except Exception as e:
        print('error:', e)
