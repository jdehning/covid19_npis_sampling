import logging

import pymc4 as pm
import tensorflow as tf
import numpy as np

# Needed to set logging level before importing other modules
# logging.basicConfig(level=logging.DEBUG)

import covid19_npis
from covid19_npis import transformations

#  from covid19_npis.benchmarking import benchmark


from covid19_npis.model import *

from covid19_npis.model.distributions import (
    LKJCholesky,
    Deterministic,
    Gamma,
    HalfCauchy,
    Normal,
    LogNormal,
)
from covid19_npis.model.utils import convolution_with_varying_kernel, gamma

log = logging.getLogger(__name__)


@pm.model()
def main_model(modelParams):

    """# Create initial Reproduction Number R_0:
    The returned R_0 tensor has the |shape| batch, country, age_group.
    """
    R_0 = yield reproduction_number.construct_R_0(
        name="R_0",
        modelParams=modelParams,
        loc=2.0,
        scale=0.5,
        hn_scale=0.3,  # Scale parameter of HalfNormal for each country
    )
    log.debug(f"R_0:\n{R_0}")

    """ # Create time dependent reproduction number R(t):
    Create interventions and change points from model parameters and initial reproduction number.
    Finally combine to R(t).
    The returned R(t) tensor has the |shape| time, batch, country, age_group.
    """
    R_t = yield reproduction_number.construct_R_t(
        name="R_t", modelParams=modelParams, R_0=R_0
    )
    log.debug(f"R_t:\n{R_t}")

    """ # Create Contact matrix C:
    We use the Cholesky version as the non Cholesky version uses tf.linalg.slogdet which isn't implemented in JAX.
    The returned tensor has the |shape| batch, country, age_group, age_group.
    """
    C = yield LKJCholesky(
        name="C_cholesky",
        dimension=modelParams.num_age_groups,
        concentration=4,  # eta
        conditionally_independent=True,
        event_stack=modelParams.num_countries,
        validate_args=True,
        transform=transformations.CorrelationCholesky(),
        shape_label=("country", "age_group_i", "age_group_j"),
    )
    log.debug(f"C:\n{C}")
    # We add C to the trace via Deterministics
    C = yield Deterministic(
        name="C",
        value=tf.einsum("...an,...bn->...ab", C, C),
        shape_label=("country", "age_group_i", "age_group_j"),
    )
    # Finally we normalize C
    C, _ = tf.linalg.normalize(C, ord=1, axis=-1)
    log.debug(f"C_normalized:\n{C}")

    """ # Create generation interval g:
    """
    len_gen_interv_kernel = 12
    # Create normalized pdf of generation interval
    (
        gen_kernel,  # shape: countries x len_gen_interv,
        mean_gen_interv,  #  shape g_mu: countries x 1
    ) = yield construct_generation_interval(l=len_gen_interv_kernel)
    log.debug(f"gen_interv:\n{gen_kernel}")

    """ # Generate exponential distribution initial infections h_0(t):
    We need to generate initial infectious before our data starts, because we do a convolution
    in the infectiousmodel loops. This convolution needs start values which we do not want
    to set to 0!
    The returned h_0(t) tensor has the |shape| time, batch, country, age_group.
    """
    h_0_t = yield construct_h_0_t(
        modelParams=modelParams,
        len_gen_interv_kernel=len_gen_interv_kernel,
        R_t=R_t,
        mean_gen_interv=mean_gen_interv,
        mean_test_delay=0,
    )
    # Add h_0(t) to trace
    yield Deterministic(
        name="h_0_t",
        value=tf.einsum("t...ca->...tca", h_0_t),
        shape_label=("time", "country", "age_group"),
    )
    log.debug(f"h_0(t):\n{h_0_t}")

    """ # Get population size tensor from modelParams:
    Should be done earlier in the real model i.e. in the modelParams
    The N tensor has the |shape| country, age_group.
    """
    N = modelParams.N_data_tensor
    log.debug(f"N:\n{N}")

    """ # Create new cases new_I(t):
    This is done via Infection dynamics in InfectionModel, see describtion
    The returned tensor has the |shape| batch, time,country, age_group.
    """
    new_E_t = InfectionModel(
        N=N, h_0_t=h_0_t, R_t=R_t, C=C, gen_kernel=gen_kernel  # default valueOp:AddV2
    )
    log.debug(f"new_E_t:\n{new_E_t[0,:]}")  # dimensons=t,c,a

    # Clip in order to avoid infinities
    new_E_t = tf.clip_by_value(new_E_t, 1e-7, 1e9)

    # Add new_E_t to trace
    new_E_t = yield Deterministic(
        name="new_E_t",
        value=new_E_t,
        shape_label=("time", "country", "age_group"),
    )
    log.debug(f"new_E_t\n{new_E_t.shape}")

    """ # Number of tests and deaths
        We simulate our reported cases i.e positiv test and totalnumber of tests total
        and deaths.
    """
    # Tests
    total_tests, positive_tests = yield number_of_tests.generate_testing(
        name_total="total_tests",
        name_positive="positive_tests",
        modelParams=modelParams,
        new_E_t=new_E_t,
    )

    # Deaths

    # Infection fatality ratio
    death_Phi = yield deaths._calc_Phi_IFR(name="IFR", modelParams=modelParams)
    # Death reporting delay
    death_m, death_theta = yield deaths._construct_reporting_delay(
        name="delay_deaths", modelParams=modelParams
    )
    # Calculate new deaths delayed
    deaths_delayed = yield deaths.calc_delayed_deaths(
        name="cases_delayed_deaths",
        new_cases=new_E_t,
        Phi_IFR=death_Phi,
        m=death_m,
        theta=death_theta,
    )

    """ add weekly modulations
    TODO    - put in wrapper function?
            - get proper parameters
            - write function
            - check: which ones should be modulated? (mostly: positive tests!)
            - check: are case numbers same as in unmodulated case? need some kind of normalization?
    """

    # total_tests = yield modulation.weekly_modulation(
    #     name="tests_total_modulated",
    #     modelParams=modelParams,
    #     cases=total_tests,
    #     week_modulation_type="abs_sine",
    #     pr_mean_weekend_factor=0.3,
    #     pr_sigma_weekend_factor=0.5,
    # )
    #
    # positive_tests = yield modulation.weekly_modulation(
    #     name="tests_positive_modulated",
    #     modelParams=modelParams,
    #     cases=positive_tests,
    #     week_modulation_type="abs_sine",
    #     pr_mean_weekend_factor=0.3,
    #     pr_sigma_weekend_factor=0.5,
    # )
    #
    # deaths_delayed = yield modulation.weekly_modulation(
    #     name="cases_deaths_modulated",
    #     modelParams=modelParams,
    #     cases=deaths_delayed,
    #     week_modulation_type="abs_sine",
    #     pr_mean_weekend_factor=0.3,
    #     pr_sigma_weekend_factor=0.5,
    # )

    """ Likelihood
    TODO    - description on fitting data
            - add deaths and total tests
    """

    likelihood = yield studentT_likelihood(
        modelParams, positive_tests, total_tests, deaths_delayed
    )
    return likelihood
