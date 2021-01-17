import sys
import logging
import time
import itertools
import os


"""
Some runtime optimizations for CPU (using tur nodes)
os.environ["OMP_NUM_THREADS"] = 32
tf.config.threading.set_inter_op_parallelism_threads(32)
tf.config.threading.set_intra_op_parallelism_threads(16)
tf.config.set_soft_device_placement(enabled)
tf.config.optimizer.set_jit(
    True
)
"""


"""
SM: I dont know what this is doing, please explain :)

os.environ["KMP_BLOCKTIME"] = "1"
os.environ["KMP_SETTINGS"] = "1"
os.environ["KMP_AFFINITY"] = "granularity=fine,verbose,compact,1,0"
"""
import pymc4 as pm
import tensorflow as tf
import tensorflow_probability as tfp
import numpy as np
import time
import os
import matplotlib.pyplot as plt
import arviz as az

"""
SM: I dont know what this is doing, please explain :)

old_opts = tf.config.optimizer.get_experimental_options()
print(old_opts)
tf.config.optimizer.set_experimental_options(
    {
        "autoparallel_optimizer": True,
        "layout_optimizer": True,
        "loop_optimizer": True,
        "dependency_optimizer": True,
        "shape_optimizer": True,
        "function_optimizer": True,
        "constant_folding_optimizer": True,
    }
)
print(tf.config.optimizer.get_experimental_options())
"""
sys.path.append("../")
import covid19_npis

""" # Debugging and other snippets
"""

# Logs setup
log = logging.getLogger()
# Needed to set logging level before importing other modules
# log.setLevel(logging.DEBUG)
covid19_npis.utils.setup_colored_logs()
logging.getLogger("parso.python.diff").disabled = True
# Mute Tensorflow warnings ...
# logging.getLogger("tensorflow").setLevel(logging.ERROR)

# For eventual debugging:
# tf.config.run_functions_eagerly(True)
# tf.debugging.enable_check_numerics(stack_height_limit=50, path_length_limit=50)

if tf.executing_eagerly():
    log.warning("Running in eager mode!")

# Force CPU
# covid19_npis.utils.force_cpu_for_tensorflow()
# covid19_npis.utils.split_cpu_in_logical_devices(32)


""" # 1. Data Retrieval
    Load data for different countries/regions, for now we have to define every
    country by hand maybe we want to automatize that at some point.

    TODO: maybe we want to outsource that to a different file at some point
"""

# Load our data from csv files into our own custom data classes

countries = [
    "Germany",
    #    "Belgium",
    #    "Czechia",
    #    "Denmark",
    #    "Finland",
    #    "Greece",
    # "Italy",
    # "Netherlands",
    "Portugal",
    # "Romania",
    # "Spain",
    #    "Sweden",
    "Switzerland",
]
c = [
    covid19_npis.data.Country(f"../data/coverage_db/{country}",)
    for country in countries
]

# Construct our modelParams from the data.
modelParams = covid19_npis.ModelParams(countries=c, minimal_daily_deaths=1)
# modelParams = covid19_npis.ModelParams.from_folder("../data/Germany_bundesländer/")

# Define our model
this_model = covid19_npis.model.model.main_model(modelParams)

# Test shapes, should be all 3:
def print_dist_shapes(st):
    for name, dist in itertools.chain(
        st.discrete_distributions.items(), st.continuous_distributions.items(),
    ):
        if dist.log_prob(st.all_values[name]).shape != (3,):
            log.warning(dist.log_prob(st.all_values[name]).shape, name)
    for p in st.potentials:
        if p.value.shape != (3,):
            log.warning(p.value.shape, p.name)


_, sample_state = pm.evaluate_model_transformed(this_model, sample_shape=(3,))
print_dist_shapes(sample_state)

""" # 2. MCMC Sampling
"""

begin_time = time.time()
log.info("start")
num_chains = 4


trace_tuning, trace = pm.sample(
    this_model,
    num_samples=60,
    num_samples_binning=10,
    burn_in_min=10,
    burn_in=100,
    use_auto_batching=False,
    num_chains=num_chains,
    xla=False,
    initial_step_size=0.00001,
    ratio_tuning_epochs=1.3,
    max_tree_depth=4,
    decay_rate=0.75,
    target_accept_prob=0.75,
    # num_steps_between_results = 9,
    #    state=pm.evaluate_model_transformed(this_model)[1]
    # sampler_type="nuts",
)

end_time = time.time()
log.info("running time: {:.1f}s".format(end_time - begin_time))

"""
step_size = np.mean(trace.sample_stats.isel(draw=-1)["step_size"])
step_sizes = []
print("Burn-in finished")
for n_draws in n_window:
    trace, step_size = adapting_sampling(trace, sampler_state, n_draws, step_size)
    step_sizes.append(step_size)
"""


plt.plot(trace_tuning.sample_stats["step_size"][0])
plt.figure()
plt.plot(trace_tuning.sample_stats["lp"].T)
plt.show()

"""
fpath = '/home/jdehning/repositories/covid19_npis_europe/scripts/traces/'
name = '21_01_08_21'
modelParams, trace = covid19_npis.utils.load_trace(name, fpath)
values = {
    var_name: tf.convert_to_tensor(value)
    for var_name, value in trace.posterior.isel(draw=-1).items()
}
num_chains = 2
trace, sampler_state = pm.sample(
    this_model,
    init=values,
    num_samples=3,
    burn_in=0,
    use_auto_batching=False,
    num_chains=None,
    xla=False,
    num_adaptation_steps=100,
    step_size=0.00001,
    max_tree_depth=3,
    max_energy_diff=1e5,
    reduce_fn=tfp.math.reduce_log_harmonic_mean_exp,
    target_accept_prob=0.25,
    return_sampler_state = True
    #    state=pm.evaluate_model_transformed(this_model)[1]
    # sampler_type="nuts",
)
values = {
    var_name: tf.convert_to_tensor(value)
    for var_name, value in trace.posterior.isel(draw=-1).items()
}

trace, sampler_state = pm.sample(
    this_model,
    init=values,
    num_samples=3,
    burn_in=0,
    use_auto_batching=False,
    num_chains=None,
    xla=False,
    num_adaptation_steps=100,
    step_size=0.00001,
    max_tree_depth=3,
    max_energy_diff=1e5,
    reduce_fn=tfp.math.reduce_log_harmonic_mean_exp,
    target_accept_prob=0.25,
    return_sampler_state = True,
    sampler_state = sampler_state
    #    state=pm.evaluate_model_transformed(this_model)[1]
    # sampler_type="nuts",
)

_, state = pm.evaluate_model_posterior_predictive(
    this_model, values=values, sample_shape=(2,)
)
"""

# We also Sample the prior for the kde in the plots (optional)
trace_prior = pm.sample_prior_predictive(
    this_model, sample_shape=(1000,), use_auto_batching=False
)

# Save our traces for the plotting script
name, fpath = covid19_npis.utils.save_trace(
    trace, modelParams, fpath="./traces", trace_prior=trace_prior
)


# Run plotting script
path = os.path.abspath(f"{fpath}/{name}")
os.system(f"python plot_trace.py {path}")
