#! /usr/bin/env python3

from astropy.io import ascii
import numpy as np

import matplotlib
from matplotlib import pylab as plt
from matplotlib.dates import DateFormatter, WeekdayLocator, DayLocator, MO
from matplotlib.ticker import StrMethodFormatter
from scipy.stats import linregress


def grafica_curacavi(plot_log=False):

    HABITANTES = 36430 # proyección 2020
    DAY = np.timedelta64(24, 'h')
    tabla = ascii.read('input/curacavi.dat')
    fecha = np.array([np.datetime64(d) for d in tabla['fecha']])
    casos = tabla['casos totales']
    activos = tabla['casos activos']
    hosp = tabla['hospitalizados']
    muertos = tabla['fallecidos']

    # keep = ~casos.mask
    keep = fecha - fecha[-1] > -12 * DAY 
    dia = np.array([(f - fecha[0]).item().days for f in fecha[keep]])
    reg = linregress(dia, np.log(casos[keep]))
    tendencia_casos = np.exp(reg.slope * dia + reg.intercept) 

    #keep = ~activos.mask
    keep = fecha - fecha[-1] > -12 * DAY 
    dia = np.array([(f - fecha[0]).item().days for f in fecha[keep]])
    reg = linregress(dia, np.log(activos[keep]))
    tendencia_activos = np.exp(reg.slope * dia + reg.intercept) 
    dias_duplicacion = np.log(2) / reg.slope


    nplot = 1 + plot_log
    fig = plt.figure(1, figsize=(6, 2 + 3 * nplot))
    fig.clf()
    for i in range(nplot):
        ax = fig.add_subplot(nplot, 1, i + 1)
        ax.plot(fecha, casos, 'bo', label='casos totales')
        ax.plot(fecha[keep], tendencia_casos, '--', color=(0, 0, .5), 
            label='tendencia últimos 12 días' )
        ax.plot(fecha, activos, 'gv', label='casos activos')
        ax.plot(fecha[keep], tendencia_activos, '--', color=(0, .5, 0), 
            label='tendencia últimos 12 días')
        ax.plot(fecha, hosp, 'r>', label='hospitalizados')
        ax.plot(fecha, muertos, 'ko', label='fallecidos')
        ax.xaxis.set_major_formatter(DateFormatter('Lun %d/%m'))
        ax.xaxis.set_major_locator(WeekdayLocator(byweekday=MO))
        ax.set_xlim(min(fecha) - 1, max(fecha) + 1)
        ax.set_ylabel('número de casos')
        if i == 0:
            ax.set_ylim(0, 1.05 * max(casos))
        else:
            ax.set_ylim(0, 1.2 * max(casos))
        ax2 = ax.twinx()
        y1, y2 = ax.get_ylim()
        y1 *= 100 / HABITANTES 
        y2 *= 100 / HABITANTES
        ax2.set_ylabel('incidencia en la población [%]')
        ax3 = ax.twiny()
        ax3.set_xticks([])
        fuente = 'Municipalidad Informa'
        if i == 1:
            linthreshy = 1.
            ax.set_yscale('symlog', linthreshy=linthreshy)
            linthreshy *= 100 / HABITANTES
            ax2.set_yscale('symlog', linthreshy=linthreshy)
            ax.yaxis.set_major_formatter(StrMethodFormatter('{x:.0f}'))
            ax2.yaxis.set_major_formatter(StrMethodFormatter('{x:g}'))
            ax.text(.02, 0.98, 'escala logarítmica', va='top',
                    transform=ax.transAxes)
        else:
            text = '×2 en {:.0f} días'.format(dias_duplicacion)
            y_text = 0.8 * min(tendencia_activos[-1], activos[-1])
            ax.text(fecha[-1], y_text, text,
                rotation=62, va='top', ha='right', color=(0,.5,0),
                fontsize=12)
            ax.legend(loc='upper left')
            if nplot == 2:
                ax.set_xticklabels([])
            ax3.set_xlabel('Casos de Covid-19 en Curacaví. Fuente: ' + fuente)
        ax2.set_ylim(y1, y2)
    for label in ax.get_xticklabels():
        label.set_rotation(30)
        label.set_ha('right')
    fig.savefig('graphics/curacavi.png')
    fig.tight_layout()
    fig.show()

if __name__ == "__main__":
    grafica_curacavi()
