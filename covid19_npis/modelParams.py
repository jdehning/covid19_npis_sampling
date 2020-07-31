import datetime
import numpy as np
import pandas as pd

import logging

log = logging.getLogger(__name__)


class ModelParams(object):
    """ 
        Class for all model params should be used if one wants to use the,
        plotting and data converters. Contains names and shapes with labels
        for every used distribution in the model.

        Distribution params can be changed by overwriting the defaults

        .. code-block:: 
            params = ModelParams()
            params.distributions["I_0"]["name"] = "my new fancy name"


        Parameters
        ----------
        data: pd.DataFrame
            DataFrame with country/age group multicolumn and datetime index
    """

    def __init__(self, data):

        # Get number of age groups and countries from data
        self.num_countries = len(data.columns.levels[0])
        self.num_age_groups = len(data.columns.levels[1])

        # Data object
        self.df = data

        # Configs for distribution
        self.distributions = self.__get_default_dist_config()
        # Config for input data
        self.data = self.__get_default_data_config(data)

    def get_data(self):
        return self.df

    def get_distribution_by_name(self, name):
        for dist, value in self.distributions.items():
            if value["name"] == name:
                this_dist = dist
        return self.distributions[this_dist]

    def __get_default_dist_config(self):
        """
            Get default values of distribution dict.
        """
        distributions = {
            "I_0": {
                "name": "I_0",
                "long_name": "Initial infectious people",
                "shape": (self.num_countries, self.num_age_groups),
                "shape_label": ("country", "age_group"),
                "math": "I_0",
            },
            "R": {
                "name": "R",
                "long_name": "Reproduction number",
                "shape": (self.num_countries, self.num_age_groups),
                "shape_label": ("country", "age_group"),
                "math": "R",
            },
            "C": {
                "name": "C",
                "long_name": "Contact matrix",
                "shape": (self.num_countries, self.num_age_groups, self.num_age_groups),
                "shape_label": ("country", "age_group_i", "age_group_j"),
                "math": "C",
            },
            "sigma": {
                "name": "sigma",
                "long_name": "likelihood scale",
                "shape": (1),
                "shape_label": ("likelihood scale"),
                "math": r"\sigma",
            },
            "g_mu": {
                "name": "g_mu",
                "long_name": "long_name g_mu",
                "shape": (1),
                "shape_label": ("g_mu"),
                "math": r"g_{\mu}",
            },
            "g_theta": {
                "name": "g_theta",
                "long_name": "long_name g_theta",
                "shape": (1),
                "shape_label": ("g_theta"),
                "math": r"g_{\theta}",
            },
            "new_cases": {
                "name": "new_cases",
                "long_name": "Daily new infectious cases",
                "shape": (len(self.df), self.num_countries, self.num_age_groups),
                "shape_label": ("time", "country", "age_group"),
            },
        }

        return distributions

    def __get_default_data_config(self, df):
        data = {  # Is set on init
            "begin": df.index.min(),
            "end": df.index.max(),
            "age_groups": [],
            "countries": [],
        }

        # Create countries lookup list dynamic from data dataframe
        for i in range(len(df.columns.levels[0])):
            data["countries"].append(df.columns.levels[0][i])

        # Create age group list dynamic from data dataframe
        for i in range(len(df.columns.levels[1])):
            data["age_groups"].append(df.columns.levels[1][i])

        return data