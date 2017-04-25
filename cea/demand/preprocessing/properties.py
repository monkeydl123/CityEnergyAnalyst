"""
building properties algorithm
"""

# HISTORY:
# J. A. Fonseca  script development          22.03.15

from __future__ import division
from __future__ import absolute_import

import numpy as np
import pandas as pd
from cea.utilities.dbfreader import dbf2df, df2dbf

import cea.inputlocator

__author__ = "Jimeno A. Fonseca"
__copyright__ = "Copyright 2015, Architecture and Building Systems - ETH Zurich"
__credits__ = ["Jimeno A. Fonseca", "Daren Thomas"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Daren Thomas"
__email__ = "cea@arch.ethz.ch"
__status__ = "Production"


def properties(locator, prop_architecture_flag, prop_hvac_flag, prop_comfort_flag, prop_internal_loads_flag):
    """
    algorithm to query building properties from statistical database
    Archetypes_HVAC_properties.csv. for more info check the integrated demand
    model of Fonseca et al. 2015. Appl. energy.

    :param InputLocator locator: an InputLocator instance set to the scenario to work on
    :param boolean prop_architecture_flag: if True, get properties about the construction and architecture.
    :param boolean prop_comfort_flag: if True, get properties about thermal comfort.
    :param boolean prop_hvac_flag: if True, get properties about types of HVAC systems, otherwise False.
    :param boolean prop_internal_loads_flag: if True, get properties about internal loads, otherwise False.

    The following files are created by this script, depending on which flags were set:

    - building_HVAC: .dbf
        describes the queried properties of HVAC systems.

    - architecture.dbf
        describes the queried properties of architectural features

    - building_thermal: .shp
        describes the queried thermal properties of buildings

    - indoor_comfort.shp
        describes the queried thermal properties of buildings
    """

    # get occupancy and age files
    building_occupancy_df = dbf2df(locator.get_building_occupancy())
    list_uses = list(building_occupancy_df.drop(['PFloor', 'Name'], axis=1).columns) #parking excluded in U-Values
    building_age_df = dbf2df(locator.get_building_age())

    # prepare shapefile to store results (a shapefile with only names of buildings
    names_shp = building_age_df[['Name']]

    # define main use:
    building_occupancy_df['mainuse'] = calc_mainuse(building_occupancy_df, list_uses)

    # dataframe with jonned data for categories
    categories_df = building_occupancy_df.merge(building_age_df, on='Name')

    # get properties about the construction and architecture
    if prop_architecture_flag:
        architecture_DB = get_database(locator.get_archetypes_properties(), 'ARCHITECTURE')

        categories_df['cat_architecture'] = categories_df.apply(lambda x: calc_category(x['mainuse'], x['built'],  x['envelope']),axis=1)

        # define architectural characteristics
        prop_architecture_df = categories_df.merge(architecture_DB, left_on='cat_architecture', right_on='Code')

        # write to shapefile
        prop_architecture_df_merged = names_shp.merge(prop_architecture_df, on="Name")
        fields = ['Hs', 'win_wall', 'type_cons', 'type_leak',  'type_roof', 'type_wall', 'type_win', 'type_shade']
        prop_architecture_dbf = names_shp.copy()
        for field in fields:
            prop_architecture_dbf[field] = prop_architecture_df_merged[field].copy()
        df2dbf(prop_architecture_dbf, locator.get_building_architecture())


    # get properties about types of HVAC systems
    if prop_hvac_flag:
        HVAC_DB = get_database(locator.get_archetypes_properties(), 'HVAC')

        categories_df['cat_HVAC'] = categories_df.apply(lambda x: calc_category(x['mainuse'], x['built'],  x['HVAC']),axis=1)

        # define HVAC systems types
        prop_HVAC_df = categories_df.merge(HVAC_DB, left_on='cat_HVAC', right_on='Code')

        # write to shapefile
        prop_HVAC_df_merged = names_shp.merge(prop_HVAC_df, on="Name")
        fields = ['type_cs', 'type_hs', 'type_dhw', 'type_ctrl', 'type_vent']
        prop_HVAC_shp = names_shp.copy()
        for field in fields:
            prop_HVAC_shp[field] = prop_HVAC_df_merged[field].copy()
        df2dbf(prop_HVAC_shp, locator.get_building_hvac())

    if prop_comfort_flag:
        comfort_DB = get_database(locator.get_archetypes_properties(), 'INDOOR_COMFORT')

        # define comfort
        prop_comfort_df = categories_df.merge(comfort_DB, left_on='mainuse', right_on='Code')

        # write to shapefile
        prop_comfort_df_merged = names_shp.merge(prop_comfort_df, on="Name")
        fields = ['Tcs_set_C', 'Ths_set_C', 'Tcs_setb_C', 'Ths_setb_C', 'Ve_lps']
        prop_comfort_dbf = names_shp.copy()
        for field in fields:
            prop_comfort_dbf[field] = prop_comfort_df_merged[field].copy()
        df2dbf(prop_comfort_dbf, locator.get_building_comfort())

    if prop_internal_loads_flag:
        internal_DB = get_database(locator.get_archetypes_properties(), 'INTERNAL_LOADS')

        # define comfort
        prop_internal_df = categories_df.merge(internal_DB, left_on='mainuse', right_on='Code')

        # write to shapefile
        prop_internal_df_merged = names_shp.merge(prop_internal_df, on="Name")
        fields = ['Qs_Wp', 'X_ghp', 'Ea_Wm2', 'El_Wm2',	'Epro_Wm2',	'Ere_Wm2', 'Ed_Wm2', 'Vww_lpd',	'Vw_lpd']
        prop_internal_shp = names_shp.copy()
        for field in fields:
            prop_internal_shp[field] = prop_internal_df_merged[field].copy()
        df2dbf(prop_internal_shp, locator.get_building_internal())


def calc_mainuse(uses_df, uses):

    databaseclean = uses_df[uses].transpose()
    array_min = np.array(databaseclean[databaseclean[:] > 0].idxmin(skipna=True), dtype='S10')
    array_max = np.array(databaseclean[databaseclean[:] > 0].idxmax(skipna=True), dtype='S10')
    mainuse = np.array(map(calc_comparison, array_min, array_max))

    return mainuse


def get_database(path_database, sheet):
    database = pd.read_excel(path_database, sheet)
    return database


def calc_comparison(array_min, array_max):
    if array_max == 'PARKING':
        if array_min != 'PARKING':
            array_max = array_min
    return array_max

def calc_category(a, x, y):
    if 0 < x <= 1920:
        result = '1'
    elif x > 1920 and x <= 1970:
        result = '2'
    elif x > 1970 and x <= 1980:
        result = '3'
    elif x > 1980 and x <= 2000:
        result = '4'
    elif x > 2000 and x <= 2020:
        result = '5'
    elif x > 2020:
        result = '6'

    if 0 < y <= 1920:
        result = '7'
    elif 1920 < y <= 1970:
        result = '8'
    elif 1970 < y <= 1980:
        result = '9'
    elif 1980 < y <= 2000:
        result = '10'
    elif 2000 < y <= 2020:
        result = '11'
    elif y > 2020:
        result = '12'

    category = a + result
    return category


def run_as_script(scenario_path=None, prop_thermal_flag=True, prop_architecture_flag=True, prop_hvac_flag=True,
                  prop_comfort_flag=True, prop_internal_loads_flag=True):
    """
    Run the properties script with input from the reference case and compare the results. This ensures that changes
    made to this script (e.g. refactorings) do not stop the script from working and also that the results stay the same.
    """
    import cea.globalvar
    gv = cea.globalvar.GlobalVariables()
    if not scenario_path:
        scenario_path = gv.scenario_reference
    locator = cea.inputlocator.InputLocator(scenario_path=scenario_path)
    properties(locator=locator, prop_architecture_flag=prop_architecture_flag,
               prop_hvac_flag=prop_hvac_flag, prop_comfort_flag=prop_comfort_flag,
               prop_internal_loads_flag=prop_internal_loads_flag)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--scenario', help='Path to the scenario folder')
    args = parser.parse_args()

    run_as_script(scenario_path=args.scenario)
