#! /usr/bin/env python3

import os
import re
import time
import urllib.request
import asciitable
import numpy as np
import datetime
from matplotlib import pylab as plt
import argparse 

def get_data(url, local, default_encoding='utf-8', max_time=2 * 3600):
    if (not os.path.exists(local) 
            or time.time() - os.path.getmtime(local) > max_time):
        print('Download data from', url)
        with urllib.request.urlopen(url) as response:
            encoding = response.headers.get_content_charset()
            if encoding is None:
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
    # why is dealing with date such a pain?
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
    start = (len(value) + nbin - 1) % nbin
    binned = total[nbin:] - total[:-nbin]
    # we estimate when there was date_origin number of cases and
    # shift curve by that amount.
    date0 = np.interp(date_origin, total, date)
    date = (date - date0)[nbin:]
    return date, binned

def plot_countries(tab, countries, variable, date_origin=200, nbin=7):
    ls = ['k-', 'b-', 'r-', 'm-', 'k--', 'b--', 'r--', 'm--']
    fig = plt.figure(1)
    fig.clf()
    fig.subplots_adjust(top=0.99,bottom=0.11, right=0.99)
    ax = fig.add_subplot(111)
    ax.set_xlabel('Days since {}th {}'.format(date_origin, variable))
    ax.set_ylabel('{}s in the last {} days'.format(variable, nbin))
    for i, country in enumerate(countries):
        date, value = get_country_data(tab, country, variable)
        date, value = bin_data(date, value, date_origin=date_origin)
        ax.plot(date, value, ls[i], label=country)
        ax.text(1.01 * date[-1], 1.01 * value[-1], country, color=ls[i][0],
            bbox=dict(facecolor='white', alpha=0.2, pad=1, lw=0))
    ax.set_xlim(-7, ax.get_xlim()[1])
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
    parser.add_argument('-f', '--format', dest='fmt', 
        default='pdf',  choices=['png', 'pdf'],
        help='plot format (pdf or png)',
    )
    arg = parser.parse_args()
    url = 'https://opendata.ecdc.europa.eu/covid19/casedistribution/csv'
    csvname = 'covid-19.csv'
    pdfname = 'covid-19-{}s.{}'.format(arg.variable, arg.fmt)
    tab = get_data(url, csvname, default_encoding='latin-1', max_time=7200)
    fig = plot_countries(tab, arg.countries, arg.variable, 
            date_origin=arg.origin)
    fig.savefig(pdfname)
