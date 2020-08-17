import logging

import tensorflow as tf
import pymc4 as pm
import numpy as np

from covid19_npis import transformations

from covid19_npis.model.distributions import HalfCauchy

log = logging.getLogger(__name__)


def studentT_likelihood(modelParams, new_cases):
    # Get scale of likelihood

    sigma = yield HalfCauchy(
        name="sigma",
        scale=50.0,
        event_stack=(modelParams.num_countries),
        conditionally_independent=True,
        transform=transformations.SoftPlus(reinterpreted_batch_ndims=2),
        shape_label=("country"),
    )

    sigma = sigma[..., tf.newaxis]  # same across age groups
    sigma = sigma[tf.newaxis, ...]  # same across time
    if len(sigma.shape) == 4:  # Move batch to front again
        sigma = tf.transpose(sigma, perm=(1, 0, 2, 3))

    # Likelihood of the data
    data = modelParams.data_tensor
    mask = ~np.isnan(data)
    len_batch_shape = len(new_cases.shape) - 3

    log.debug(f"data:\n{tf.boolean_mask(data, mask)}")
    log.debug(f"new_cases without mask:\n{new_cases}")

    log.debug(
        f"new_cases w. mask:\n{tf.boolean_mask(new_cases, mask, axis=len_batch_shape)}"
    )

    likelihood = yield pm.StudentT(
        name="like",
        loc=tf.boolean_mask(new_cases, mask, axis=len_batch_shape),
        scale=tf.boolean_mask(
            sigma * tf.sqrt(new_cases) + 1, mask, axis=len_batch_shape
        ),
        df=4,
        observed=tf.boolean_mask(data, mask),
        reinterpreted_batch_ndims=1,
    )
    return likelihood
