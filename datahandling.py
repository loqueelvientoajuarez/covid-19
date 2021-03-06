#! /usr/bin/env python3

import pycountry
import os
import time
import urllib.request
from astropy.io import ascii as asciitable
from astropy.table import Table, Column, MaskedColumn
from numpy import datetime64, timedelta64
import numpy as np
import re
import datetime


# is there a way to define order in group matching?
_US_DATE_RE = '^([0-9]{1,2})/([0-9]{1,2})/([0-9]{2,4})$'
_EU_DATE_RE = '^([0-9]{1,2})/([0-9]{1,2})/([0-9]{2,4})$'
INPUTDIR = "input"
OUTPUTDIR = "output"

def read_time_series(product_number, header_lines=1, columns=None, name=None,
        transposed=True):
    
    subdir = 'producto{}'.format(product_number)
    path = os.path.join('..', 'Datos-COVID19', 'output', subdir)

    suffix = ''
    if transposed:
        suffix = '_T'
    if name is None:
        basenames = [f for f in os.listdir(path) 
            if re.search(suffix  + '\.csv$', f)]
        basename = basenames[0]
    else:
        basename = name + suffix + '.csv'
    filename = os.path.join(path, basename)

    if transposed:
        
        if header_lines == 1:
            
            tab = asciitable.read(filename)
            
        else:    
            
            with open(filename, 'r') as input:
                lines = input.read().splitlines()

            names = lines[0].split(',')
            for line in lines[1:header_lines]:
                names = [n1 + ' ' + n2 for n1, n2 in zip(names, line.split(','))]

            tab = asciitable.read(lines[header_lines:], names=names)
        
        if columns is not None:
            cols = tab.columns
            return [cols[c].data for c in columns]
        
    else:
        
        tab = asciitable.read(filename)
 
    return tab

def retrieve_table(url, local, default_encoding='utf-8-sig', max_time=2 * 3600):
    # read if recent
    os.makedirs(INPUTDIR, exist_ok=True)
    local = os.path.join(INPUTDIR, local)
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

def build_international_data_set(source='EU', max_time = 2 * 3600):
    # read if recent
    os.makedirs(OUTPUTDIR, exist_ok=True)
    filename = 'covid-international-{}.csv'.format(source)
    filename = os.path.join(OUTPUTDIR, filename)
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

def _symptom_filename(date):
    inicio = 'FechaInicioSintomas.csv'
    if date is not None:
        inicio = date + '-' + inicio
    return inicio

def retrieve_chilean_data(overwrite=False, date=None):
    url = 'https://raw.githubusercontent.com/MinCiencia/Datos-COVID19/master/input/InformeEpidemiologico/'
    inicio = _symptom_filename(date)
    names =  ['CasosActivosPorComuna.csv', 'CasosAcumuladosPorComuna.csv',
        inicio, 'SemanasEpidemiologicas.csv']
    for name in names:
        retrieve_table(url + name, name, max_time=7200 * (1-overwrite))

def retrieve_chilean_vitals(year, vital='deaths', date=None, overwrite=False):
    if vital in ['death', 'deaths', 'defunciones', 'defuncion', 'defunción']:
        name = 'Defunciones'
    else:
        name = 'Nacimientos'
    if date is None:
        date = str(datetime64('now') - timedelta64(10, 'h'))
    yearnow = int(date[0:4])
    today = date[5:10]
    site = 'https://raw.githubusercontent.com'
    folder = 'MinCiencia/Datos-COVID19/master/input/RegistroCivil/' + name 
    start = '{}-01-01'.format(year)
    if year < yearnow:
        end = '{}-12-31'.format(year)
    else:
        end = '{}-{}'.format(yearnow, today)
    filename = '{}_{}_{}_DO.csv'.format(name, start, end)
    url = site + '/' + folder + '/' + filename
    localname = vital + '-' + str(year) + '.csv'
    if year < yearnow:
        max_time = 3e7
    else:
        max_time = 7200
    print(localname)
    tab = retrieve_table(url, localname, max_time=max_time * (1 - overwrite)) 
    return tab

def retrieve_chilean_region(region, overwrite=False, date=None):
    retrieve_chilean_data(overwrite=overwrite, date=date)
    tabs = []
    # parse epidemiological weeks 
    filename = os.path.join(INPUTDIR, 'SemanasEpidemiologicas.csv')
    weeks = asciitable.read(filename).columns[1:]
    weeks = {n: v[0] for n, v in weeks.items()}
    inicio = _symptom_filename(date)
    names = ['CasosAcumuladosPorComuna.csv', 'CasosActivosPorComuna.csv', inicio]
    for name in names:
        filename = os.path.join(INPUTDIR, name)
        tab = asciitable.read(filename)
        tab = tab[tab['Codigo region'] == region]
        tab = tab[tab['Comuna'] != 'Total']
        if name == inicio:
            names = [weeks.get(c, c) for c in tab.colnames]
            tab = Table(rows=tab, names=names)
        tabs.append(tab)
    return tabs

def get_country_data(tab, country, variable, region='all', cum=False,
        nbin=1, date_origin=None):
    # country names or code?
    country_col = 'country'
    if re.match('^[A-Z]{2,3}[0-9]*$', country):
        country_col = 'country_code_3'
        if len(country) != 3:
            country_col = 'country_code_2'
    is_country = tab[country_col] == country
    is_region = tab['region'] == region 
    index = np.logical_and(is_country, is_region)
    tab = tab[index]
    if not len(tab):
        raise RuntimeError('no data for country ' + country)
    tab_date = [datetime.date.fromisoformat(d).toordinal() for d in tab['date']]
    tab_value = np.array(tab[variable].tolist())
    cum_value = np.cumsum(tab_value)
    if date_origin is not None:
        if max(cum_value) < date_origin:
            return np.array([]), np.array([])
        tab_date -= np.interp(date_origin, cum_value, tab_date)
    if cum:
        tab_value = cum_value
    elif nbin > 1:
        bin_value = cum_value[nbin:] - cum_value[:-nbin]
        tab_value = np.hstack([tab_value[nbin-1], bin_value])
        tab_date = tab_date[nbin-1:]
    return tab_date, tab_value

def _fix_country(tab, source):
    countries = pycountry.countries
    if source == 'JohnHopkins':
        for row in tab:
            country = row['country']
            if country == 'US': # Bug in Hopkins data description
                row['country'] = 'United States'
                country = row['country']
            elif country == 'Korea, South':
                row['country'] = 'South Korea'
                country = 'Korea, Republic of'
            elif country == 'Taiwan*':
                row['country'] = 'Taiwan'
                country = 'Taiwan, Province of China'
            c = countries.get(name=country)
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
