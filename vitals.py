from astropy.io import ascii
import numpy as np

from datahandling import read_time_series

def get_population(region=None, sex=None, age=None, years=slice(2002,2036)):
    tab = ascii.read('input/population.csv')
    keep = np.ones((len(tab,)), dtype=bool)
    if region is not None:
        keep *= region == tab['Region']
    if sex is not None:
        keep *= sex == tab['Sexo']
    if age is not None:
        if np.dim(age) == 1:
            keep *= (age[0] <= tab['Edad']) * (tab['Edad'] < age[1])
        else:
            keep *= age == tab['Edad']
    tab = tab[keep]
    dates, populations = [], []
    step = years.step
    if step is None:
        step = 1
    for year in range(years.start, years.stop, step):
        name = 'a{}'.format(year)
        dates.append(np.datetime64('{}-06-30'.format(year)))
        populations.append(tab[name].sum())
    return np.array(dates), np.array(populations)

def get_rate(vital='Defunciones', region=None):

    product = 32 + (vital != 'Defunciones')

    date_pop, pop = get_population(region=region, years=slice(2009,2022)) 

    vitals = read_time_series(product, transposed=False, name=vital)
    if region is not None:
        vitals = vitals[vitals['Codigo region'] == region]
    date = np.array([np.datetime64(c) for c in vitals.colnames[4:]])
    events = np.array([vitals[c].sum() for c in vitals.columns[4:]])
    curr_pop = np.interp(date.astype(float), date_pop.astype(float), pop) 
    rate = 1000 * events / curr_pop * 365 

    return date, rate
   
