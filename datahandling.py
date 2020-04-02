#! /usr/bin/env python3

import pycountry
import os
import time
import urllib.request
from astropy.io import ascii as asciitable
from astropy.table import Table, Column, MaskedColumn
import numpy as np
import re
import datetime

# is there a way to define order in group matching?
_US_DATE_RE = '^([0-9]{1,2})/([0-9]{1,2})/([0-9]{2,4})$'
_EU_DATE_RE = '^([0-9]{1,2})/([0-9]{1,2})/([0-9]{2,4})$'

def retrieve_table(url, local, default_encoding='utf-8-sig', max_time=2 * 3600):
    # read if recent
    if (os.path.exists(local) 
            and time.time() - os.path.getmtime(local) < max_time):
        try:
            print('Read data from recent file', local)
            data = asciitable.read(local)
            return data
        except:
            print('Could not read from', local)
            pass
    # download
    print('Download recent data from', url)
    with urllib.request.urlopen(url) as response:
        encoding = response.headers.get_content_charset()
        if encoding is None: # 
            encoding = default_encoding 
        contents = response.read().decode(encoding)
    with open(local, 'w') as fh:
        fh.write(contents)
    data = asciitable.read(local)
    return data

def retrieve_data_set(source='EU', max_time = 2 * 3600):
    # read if recent
    filename = 'covid-{}.csv'.format(source)
    if (os.path.exists(filename) 
            and time.time() - os.path.getmtime(filename) < max_time):
        try:
            print('Read data from recent file', filename)
            data = asciitable.read(filename)
            return data
        except:
            print('Could not read from', filename)
            pass
    # process otherwise
    if source == 'EU':
        url = 'https://opendata.ecdc.europa.eu/covid19/casedistribution/csv'
        csv = 'covid-19-eu.csv'
        tables = [retrieve_table(url, csv)[::-1]]
    elif source == 'JohnHopkins':
        url = ('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/'
               'master/csse_covid_19_data/csse_covid_19_time_series/'
               'time_series_covid19_{}_global.csv')
        stat = ['confirmed', 'deaths', 'recovered']
        csv = ['covid-19-{}.csv'.format(s) for s in stat]
        tables = [retrieve_table(url.format(s), c) for s, c in zip(stat, csv)]
    else:
        raise KeyError('No such data source: ' + source)
    print('Processing data and saving to', filename)
    # we want consistent column names
    tables = [_fix_colnames(t) for t in tables]
    # we want daily cases not aggregated number
    tables = [_convert_to_daily(t, source) for t in tables]
    # some tables list cases by region, we also want country total
    tables = [_sum_zones(t, source) for t in tables]
    # merge tables if cases/deaths are separate
    tab = _merge_tables(tables, source)
    # fix date formats and fill in missing dates in series
    tab = _fix_date(tab, source)
    # fix country codes
    tab = _fix_country(tab, source)
    tab.write(filename, overwrite=True)
    return tab

def _fix_country(tab, source):
    countries = pycountry.countries
    if source == 'JohnHopkins':
        for row in tab:
            c = countries.get(name=row['country'])
            if c:
                row['country_code_2'] = c.alpha_2
                row['country_code_3'] = c.alpha_3
    return tab

def _convert_to_daily(tab, source):
    if source == 'JohnHopkins':
        cols = [c for c in tab.colnames if re.match(_US_DATE_RE, c)]
        for c2, c1 in zip(cols[-1:1:-1], cols[-2:0:-1]):
            tab[c2] -= tab[c1]
    return tab

def _fix_colnames(tab):
    # date string and day,month,year are redundant... also longitude data...
    for name in ['day', 'month', 'year', 'Long', 'Lat']:
        if name in tab.colnames:
            tab.remove_column(name)
    for col in tab.columns.values():
        if col.name in ['countriesAndTerritories', 'Country/Region']:
            col.name = 'country'
        if col.name in 'Province/State':
            col.name = 'region'
        elif col.name == 'geoId':
            col.name = 'country_code_2'
        elif col.name == 'countryterritoryCode':
            col.name = 'country_code_3'
        elif col.name == 'popData2018':
            col.name = 'population' 
        elif col.name == 'dateRep':
            col.name = 'date'
    return tab 

def _select_zone(tab, country, region):
    same_country = tab['country'] == country
    same_region = tab['region'] == region
    index = np.logical_and(same_country, same_region)
    return tab[index]

def _iterzone(tab):
    for country in np.unique(tab['country']):
        for region in np.unique(tab['region']):
            yield _select_zone(tab, country, region)

def _fix_date(tab, source):
    rows = []
    names = tab.colnames
    for zone in _iterzone(tab):
        previous_date = None
        for row in zone:
            row = row.as_void().tolist()
            if source == 'EU':
                d, m, y = re.match(_EU_DATE_RE, row[0]).groups()
            else:
                m, d, y = re.match(_US_DATE_RE, row[0]).groups()
            y, m, d = [int(x) for x in [y, m, d]]
            if y < 50:
                y += 2000
            elif y < 100:
                y += 1950
            date = datetime.date(y, m, d)
            if previous_date is not None:
                while True:
                    previous_date += datetime.timedelta(days=1)
                    if previous_date >= date:
                        break
                    newrow = (previous_date.isoformat(), 0, 0, 0, *row[3:])
                    rows.append(newrow)
            newrow = (date.isoformat(), *(row[1:]))
            rows.append(newrow)
    tab = Table(rows=rows, names=names)
    return tab
 
def _sum_zones(tab, source):
    # if no region column, in means it's already a total #... just add
    # the region column
    if 'region' not in tab.columns:
        region = np.full_like(tab['country'].data, 'all')
        tab.add_column(Column(region, 'region'))
        return tab
    # if there is no global stat for country, sum all of its regions
    for country in np.unique(tab['country']):
        same_country = tab['country'] == country
        is_region = tab['region'].mask == False
        is_global = np.logical_and(np.logical_not(is_region), same_country)
        if any(is_global):
            tab['region'][is_global] = 'all'
            continue
        is_region = np.logical_and(is_region, same_country)
        if not any(is_region):
            continue
        regions = tab[is_region] 
        row = ['all', country]
        if source == 'JohnHopkins':
            datacols = [n for n in tab.colnames if re.match(_US_DATE_RE, n)]
            row += [np.sum(regions[col]) for col in datacols]
        tab.add_row(row)    
    return tab
        
def _merge_tables(tables, source):
    colnames = ('date', 'cases', 'deaths',
                'recoveries', 'country', 'region', 
                'country_code_3', 'country_code_2', 'population')
    if source == 'JohnHopkins':
        rows = []
        cases, deaths, recov = tables
        for row_c in cases:
            # John Hopkins give total numbers, go back to daily new cases/deaths
            region, country = row_c['region'], row_c['country']
            row_d = _select_zone(deaths, country, region)
            row_r = _select_zone(recov, country, region)
            for usdate in cases.colnames:
                if not re.match(_US_DATE_RE, usdate):
                    continue
                num_cases = row_c[usdate]
                num_recov = 0
                num_deaths = 0
                if len(row_d) and usdate in row_d.columns:
                    num_deaths = row_d[usdate].item()
                if len(row_r) and usdate in row_r.columns:
                    try:
                        num_recov = row_r[usdate].item()
                    except Exception as e:
                        raise e
                row = (usdate, num_cases, num_deaths, num_recov, 
                        country, region, '   ', '  ', 0)
                rows.append(row)
        tab = Table(rows=rows, names=colnames)
    elif source == 'EU':
        tab = tables[0]
        recov = np.ma.masked_array([0] * len(tab), mask=True)
        tab.add_column(MaskedColumn(recov, 'recoveries'), 7)
        return tab[colnames]
    return tab
