import numpy as np
import matplotlib.pyplot as plt
from numpy.linalg import inv
from scipy.cluster.vq import whiten
import pandas as pd
from pandas.plotting import scatter_matrix
from scipy.stats import entropy, chi2_contingency, shapiro, norm

def kde_entropy(x, bandwidth = 'silverman', **kwargs):
    from statsmodels.nonparametric.kde import KDEUnivariate
    """Univariate Kernel Density Estimation with Statsmodels"""
    kde = KDEUnivariate(np.reshape(x, (-1,1)))
    kde.fit(bw = bandwidth, kernel = 'gau', fft = True, **kwargs)
    
    return kde.entropy

def KLdivergence(x, n_bins = None):
 
    if n_bins is None:
        bins_gaussian = len(np.histogram(np.random.normal(loc = np.mean(x), scale = np.std(x), 
                                                          size = len(x)), bins = 'fd')[0])
        bins_x = len(np.histogram(x, bins = 'fd')[0])
        n_bins = min(bins_gaussian, bins_x)
    #gaussian_hist = norm.pdf(np.linspace(-5, 5, n_bins), loc = np.mean(x), scale = np.std(x))
    gaussian_hist = np.histogram(np.random.normal(loc = np.mean(x), scale = np.std(x), 
                                                          size = len(x)), bins = n_bins)[0]
    x_hist = np.histogram(x, bins = n_bins)[0]
    
    return entropy(x_hist, gaussian_hist+1e-40)

def calculateNegentropy(x, kindOfNegentropy = 'empirical', n_bins = None):
   
    if kindOfNegentropy == 'KDE':
        return np.log(np.std(x)*np.sqrt(2*np.pi*np.exp(1))) - kde_entropy(x)
    
    elif kindOfNegentropy == 'empirical':
        if n_bins is None:
            bins_gaussian = len(np.histogram(np.random.normal(loc=np.mean(x), scale=np.std(x), 
                                                              size = len(x)), bins = 'fd')[0])
            bins_x = len(np.histogram(x, bins = 'fd')[0])
            n_bins = min(bins_gaussian, bins_x)
        gaussian_hist = np.histogram(np.random.normal(loc=np.mean(x), scale=np.std(x), 
                                                      size = len(x)), bins = n_bins)[0]
        x_hist = np.histogram(x, bins = n_bins)[0]
        negentropy = entropy(gaussian_hist) - entropy(x_hist)
        if negentropy < 0:
            negentropy = 0
        return negentropy
    
    else:
        print('Not implemented')
        return None
    
def resultsTable(y, n_bins = None, negentropyType = 'empirical'):
    import tabulate
    from IPython.display import HTML, display
    
    data = np.array([["Data", "Negentropy", "KL Divergence", "Shapiro-Wilk test W", "Shapiro-Wilk test P_value"]])
    for i, y_i in enumerate(y):
        shapiro_yi = shapiro(y_i)
        new_row = np.array([["%d"%i, "%.04f"%calculateNegentropy(y_i, n_bins = n_bins, 
                                                                 kindOfNegentropy = negentropyType),
                             "%0.4f"%KLdivergence(y_i, n_bins = n_bins),
                             "%.04f"%shapiro_yi[0], "%.04E"%shapiro_yi[1]]])
        data = np.concatenate((data, new_row))
    display(HTML(tabulate.tabulate(data, tablefmt = 'html', headers = 'firstrow')))
    return None

def mutualInformation_matrix(signal, kde=False, n_bins=None):
    from statsmodels.sandbox.distributions.mv_measures import mutualinfo_kde, mutualinfo_binned
    rows, cols = signal.shape
    mat = np.zeros((rows, rows))
    np.fill_diagonal(mat, 1)
    # Upper diagonal
    for r in range(rows):
        for c in range(r, rows):
            if r == c:
                continue
            p = signal[r].flatten() + 1e-12
            q = signal[c].flatten() + 1e-12
            if kde:
                mi = mutualinfo_kde(p, q)
            else:
                if n_bins is None:
                    p_bins = len(np.histogram(p, bins='fd')[0])
                    q_bins = len(np.histogram(q, bins='fd')[0])
                    n_bins = min(p_bins, q_bins)
                elif n_bins == 'auto':
                    qs = np.sort(q)
                    ps = np.sort(p)
                    qbin_sqr = np.sqrt(5./cols)
                    quantiles = np.linspace(0, 1, 1./qbin_sqr)
                    quantile_index = ((cols-1)*quantiles).astype(int)
                    #move edges so that they don't coincide with an observation
                    shift = 1e-6 + np.ones(quantiles.shape)
                    shift[0] -= 2*1e-6
                    q_bins = qs[quantile_index] + shift
                    p_bins = ps[quantile_index] + shift
                    n_bins = min(p_bins, q_bins)

                #mi = mutualinfo_binned(p, q, n_bins)[0]
                
                fx, binsx = np.histogram(p, bins = p_bins)
                fy, binsy = np.histogram(q, bins = q_bins)
                fyx, binsy, binsx = np.histogram2d(q, p, bins = (binsy, binsx))

                pyx = fyx * 1. / cols
                px = fx * 1. / cols
                py = fy * 1. / cols


                mi_obs = pyx * (np.log(pyx + 1e-12) - np.log(py + 1e-12)[:,None] - np.log(px + 1e-12))
                mi_obs[np.isnan(mi_obs)] = 0
                mi_obs[np.isinf(mi_obs)] = 0
                mi = mi_obs.sum()
            if np.isnan(mi):
                mi = 1
            elif mi > 1:
                mi = 1
            mat[r][c] = mi
            mat[c][r] = mi
            
    return mat

def plot_MutualInformation(mixtures, y, KDE = False, nbins = None):
    import seaborn as sb

    
    fig, axs = plt.subplots(2, 2, figsize=(13, 10))
    
    sb.heatmap(mutualInformation_matrix(mixtures, kde=KDE, n_bins = nbins), ax=axs[0,0], annot=True, cmap = 'YlGnBu', vmin = 0, vmax = 1)
    axs[0, 0].set_title('Mutual Information: mixtures')
    sb.heatmap(np.abs(np.corrcoef(mixtures)), annot=True, cmap = 'YlOrRd', ax = axs[0,1], vmin = 0, vmax =  1)
    axs[0, 1].set_title('Abs Correlation matrix: mixtures')

    
    sb.heatmap(mutualInformation_matrix(y, kde = KDE, n_bins = nbins), ax=axs[1, 0], annot=True, cmap = 'YlGnBu', vmin = 0, vmax = 1)
    axs[1, 0].set_title('Mutual Information: outputs')
    
    sb.heatmap(np.abs(np.corrcoef(y)), annot=True, cmap = 'YlOrRd', ax = axs[1,1], vmin = 0, vmax =  1)
    axs[1, 1].set_title('Abs Correlation matrix: outputs')
    
    return None

def best_fit_distribution(data, bins=200, ax=None):
    import warnings
    import numpy as np
    import pandas as pd
    import scipy.stats as st
    import statsmodels as sm
    import matplotlib
    import matplotlib.pyplot as plt

    """Model data by finding best fit distribution to data"""
    # Get histogram of original data
    #y, x = np.histogram(data, bins=bins, density=True)
    y, x = np.histogram(data, bins = bins, normed = True)
    x = (x + np.roll(x, -1))[:-1] / 2.0

    # Distributions to check
    DISTRIBUTIONS = [        
        st.alpha,st.anglit,st.arcsine,st.beta,st.betaprime,st.bradford,st.burr,st.cauchy,st.chi,st.chi2,st.cosine,
        st.dgamma,st.dweibull,st.erlang,st.expon,st.exponnorm,st.exponweib,st.exponpow,st.f,st.fatiguelife,st.fisk,
        st.foldcauchy,st.foldnorm,st.frechet_r,st.frechet_l,st.genlogistic,st.genpareto,st.gennorm,st.genexpon,
        st.genextreme,st.gausshyper,st.gamma,st.gengamma,st.genhalflogistic,st.gilbrat,st.gompertz,st.gumbel_r,
        st.gumbel_l,st.halfcauchy,st.halflogistic,st.halfnorm,st.halfgennorm,st.hypsecant,st.invgamma,st.invgauss,
        st.invweibull,st.johnsonsb,st.johnsonsu,st.ksone,st.kstwobign,st.laplace,st.levy,st.levy_l,st.levy_stable,
        st.logistic,st.loggamma,st.loglaplace,st.lognorm,st.lomax,st.maxwell,st.mielke,st.nakagami,st.ncx2,st.ncf,
        st.nct,st.norm,st.pareto,st.pearson3,st.powerlaw,st.powerlognorm,st.powernorm,st.rdist,st.reciprocal,
        st.rayleigh,st.rice,st.recipinvgauss,st.semicircular,st.t,st.triang,st.truncexpon,st.truncnorm,st.tukeylambda,
        st.uniform,st.vonmises,st.vonmises_line,st.wald,st.weibull_min,st.weibull_max,st.wrapcauchy
    ]

    # Best holders
    best_distribution = st.norm
    best_params = (0.0, 1.0)
    best_pdf_statistics = st.norm.stats(loc = 0, scale = 1, moments = 'mvsk')
    #best_sse = np.inf
    best_p = 0
    best_chi2_stat = np.inf
    
    # Estimate distribution parameters from data
    for distribution in DISTRIBUTIONS:

        # Try to fit the distribution
        try:
            # Ignore warnings from data that can't be fit
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore')

                # fit dist to data
                params = distribution.fit(data)

                # Separate parts of parameters
                arg = params[:-2]
                loc = params[-2]
                scale = params[-1]

                # Calculate fitted PDF and error with fit in distribution
                pdf = distribution.pdf(x, loc=loc, scale=scale, *arg)
                pdf_statistics = distribution.stats(loc=loc, scale=scale, moments = 'mvsk', *arg)

                #sse = np.sum(np.power(y - pdf, 2.0))
                deltaDof = len(params)
                #chisq, p_value = chisquare(f_obs = y, f_exp = pdf, ddof = deltaDof)
                chi_squared_stat = (((y - pdf)**2)/pdf).sum()
                p_value = 1 - st.chi2.cdf(x = chi_squared_stat, df = len(y) - 1 - deltaDof)
               
                
                # if axis pass in add to plot
                try:
                    if ax:
                        pd.Series(pdf, x).plot(ax = ax)
                    end
                except Exception:
                    pass

                # identify if this distribution is better
                #if best_sse > sse > 0:
                #if p_value > best_p:
                if best_chi2_stat > chi_squared_stat > 0:
                    best_distribution = distribution
                    best_params = params
                    #best_sse = sse
                    best_p = p_value
                    best_pdf_statistics = pdf_statistics
                    best_chi2_stat = chi_squared_stat
                    
        except Exception:
            pass

    return (best_distribution.name, best_params, best_chi2_stat, best_p, best_pdf_statistics)

def make_pdf(dist, params, size=10000):
    """Generate distributions's Propbability Distribution Function """

    # Separate parts of parameters
    arg = params[:-2]
    loc = params[-2]
    scale = params[-1]

    # Get sane start and end points of distribution
    start = dist.ppf(0.01, *arg, loc=loc, scale=scale) if arg else dist.ppf(0.01, loc=loc, scale=scale)
    end = dist.ppf(0.99, *arg, loc=loc, scale=scale) if arg else dist.ppf(0.99, loc=loc, scale=scale)

    # Build PDF and turn into pandas Series
    x = np.linspace(start, end, size)
    y = dist.pdf(x, loc=loc, scale=scale, *arg)
    #pdf = pd.Series(y, x)

    #return pdf
    return y

def graph_fittedData(data_to_be_fitted):
    from scipy.stats import laplace, chisquare, norm

    lnspace = np.linspace(np.amin(data_to_be_fitted), np.amax(data_to_be_fitted), len(data_to_be_fitted))

    plt.hist(data_to_be_fitted, bins = 'fd', normed=True)

    import seaborn as sb
    import scipy.stats as st
    best_fit_name, best_fit_paramms, chi2_stat, p_value, pdf_stats  = best_fit_distribution(data_to_be_fitted, bins = 'fd')
    best_dist = getattr(st, best_fit_name)

    arg = best_fit_paramms[:-2]
    pdf = best_dist.pdf(lnspace, loc = best_fit_paramms[-2], scale = best_fit_paramms[-1], *arg)

    mu = pdf_stats[0]
    var = pdf_stats[1]
    skew = pdf_stats[2]
    kurt = pdf_stats[3]

    plt.plot(lnspace, pdf, 'c')
    plt.title(best_fit_name + ' PDF')
    textstring = '$\mu = %.4f$\n$\delta ^2 = %.4f$\n$skew = %.4f$\n$kurt = %.4f$\n$\chi ^2 = %.4f$\n$p_{value} = %.4f$'%(mu, var, skew, kurt, chi2_stat, p_value)


    plt.text(4.2, 0.10, textstring)
    plt.show()

    return None