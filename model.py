from scipy.special import gamma as Γ, \
                          gammainc as γ
from scipy.ndimage.interpolation import shift

# from download import retrieve_data_set

def resolution_model(new_cases, t_resol, dt_resol, epsilon_rep, sigma_rep):
    """Model the number of resolved cases using new_cases and time to resolution"""
    # We assume time to resolution follows γ distribution of mean t_resol 
    # and variance dt_resol ** 2.  Probability of resolution on day + n
    # is given by p(n) 
    ndays = len(new_cases)
    n = np.arange(0, ndays)
    β = t_resol / dt_resol ** 2
    α = β * t_resol
    p = γ(α, β*(n + 0.5)) - γ(α, β*max(0, n - 0.5))
    s0 = convolve(new_cases, p)[0:ndays]
    # besides the gross underdetermination of cases, data uncertainty is patent
    # with day-to-day variations of quasi-random appearance. It is mainly
    # driven by reporting delays (e.g. some nationalities don't like to die on
    # a Sunday).
    #
    # Let's call η(i) the fraction of cases/deaths on day i that are reported on
    # the following day.  Let's call 
    #
    #   ε(i)  = <η(i)>           [relative systematic error] 
    #
    #   σ(i)² = <[η(i)-η(i)]²>   [variance of the statistical term] 
    #
    # and assume they are independent, i.e. <η(i)η(j)> = 0 for i ≠ j.
    #
    # Since s(i) = s⁰(i) + η(i-1) s⁰(i-1) - η(i) s⁰(i)
    #
    #     <s(i)> = (1 - <ε(i)>) s⁰(i) + <ε(i-1)>  s⁰(i-1)
    #
    # the covariance matrix of s⁰ given by Σ(i, j) = <(s(i) - <s(i)>)(s(j) -
    # <s(j)>)
    #
    # is given by
    #
    #   Σ(1, 1)                   = σ(1)² s⁰(1)² 
    #   Σ(i, i)                   = σ(i-1)² s⁰(i-1)² + σ(i)² s⁰(i)²  if i > 1 
    #   Σ(i, i - 1) = Σ(i - 1, i) = σ(i-1)² s⁰(i-1)²                 if i > 1 
    #   Σ(i, j)                   = 0                          if |j - i| > 1
    #
    # Given a model s⁰, we can compute values and uncertainties to fit data /
    # perform Bayesian inference.
    ds = epsilon_rep * s0
    s = s0 - ds + shift(ds, 1)
    ds2 = (sigma_rep * new_resol) ** 2
    Sigma = (np.diag(ds2 + shift(ds2, 1)) 
             + np.diag(ds2[:-1], 1) + np.diag(ds2[:-1], -1))
    return s, Sigma


def merge_tables(tables):
    

if __name__ == "__main__":
    url = ('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/'
           'master/csse_covid_19_data/csse_covid_19_time_series/'
           'time_series_covid19_{}_global.csv')
    stat = ['confirmed', 'deaths', 'recovered']
    local = ['covid-19-{}.csv'.format(s) for s in stat]
    tables = [retrieve_table(url.format(s), l) for s, l in zip(stat, local)]
    table = merge_tables()
        
