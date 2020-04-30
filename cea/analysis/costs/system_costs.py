"""
costs according to supply systems
"""
from __future__ import division

import numpy as np
import pandas as pd
from geopandas import GeoDataFrame as gpdf

import cea.config
import cea.inputlocator

__author__ = "Jimeno A. Fonseca"
__copyright__ = "Copyright 2015, Architecture and Building Systems - ETH Zurich"
__credits__ = ["Jimeno A. Fonseca"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Daren Thomas"
__email__ = "cea@arch.ethz.ch"
__status__ = "Production"


def costs_main(locator, config):
    # get local variables
    capital = config.costs.capital
    operational = config.costs.operational

    demand = pd.read_csv(locator.get_total_demand())
    supply_systems = gpdf.from_file(locator.get_building_supply()).drop('geometry', axis=1)
    data_all_in_one_systems = pd.read_excel(locator.get_database_supply_assemblies(), sheet_name=None)
    factors_heating = data_all_in_one_systems['HEATING']
    factors_dhw = data_all_in_one_systems['HOT_WATER']
    factors_cooling = data_all_in_one_systems['COOLING']
    factors_electricity = data_all_in_one_systems['ELECTRICITY']
    factors_resources = pd.read_excel(locator.get_database_feedstocks(), sheet_name=None)

    # get the mean of all values for this
    factors_resources_simple = [(name, values['Opex_var_buy_USD2015kWh'].mean()) for name, values in
                                factors_resources.items()]
    factors_resources_simple = pd.DataFrame(factors_resources_simple,
                                            columns=['code', 'Opex_var_buy_USD2015kWh']).append(
        # append NONE choice with zero values
        {'code': 'NONE'}, ignore_index=True).fillna(0)

    # local variables
    # calculate the total operational non-renewable primary energy demand and CO2 emissions
    ## create data frame for each type of end use energy containing the type of supply system use, the final energy
    ## demand and the primary energy and emissions factors for each corresponding type of supply system
    heating_costs = factors_heating.merge(factors_resources_simple, left_on='feedstock', right_on='code')[
        ['code_x', 'feedstock', 'scale', 'Opex_var_buy_USD2015kWh', 'CAPEX_USD2015kW', 'LT_yr', 'O&M_%', 'IR_%']]
    cooling_costs = factors_cooling.merge(factors_resources_simple, left_on='feedstock', right_on='code')[
        ['code_x', 'feedstock', 'scale', 'Opex_var_buy_USD2015kWh', 'CAPEX_USD2015kW', 'LT_yr', 'O&M_%', 'IR_%']]
    dhw_costs = factors_dhw.merge(factors_resources_simple, left_on='feedstock', right_on='code')[
        ['code_x', 'feedstock', 'scale', 'Opex_var_buy_USD2015kWh', 'CAPEX_USD2015kW', 'LT_yr', 'O&M_%', 'IR_%']]
    electricity_costs = factors_electricity.merge(factors_resources_simple, left_on='feedstock', right_on='code')[
        ['code_x', 'feedstock', 'scale', 'Opex_var_buy_USD2015kWh', 'CAPEX_USD2015kW', 'LT_yr', 'O&M_%', 'IR_%']]

    heating = supply_systems.merge(demand, on='Name').merge(heating_costs, left_on='type_hs', right_on='code_x')
    dhw = supply_systems.merge(demand, on='Name').merge(dhw_costs, left_on='type_dhw', right_on='code_x')
    cooling = supply_systems.merge(demand, on='Name').merge(cooling_costs, left_on='type_cs', right_on='code_x')
    electricity = supply_systems.merge(demand, on='Name').merge(electricity_costs, left_on='type_el', right_on='code_x')

    fields_to_plot = []

    """"
    CAPEX Calculations
    FIXED OPEX Calculations
    """
    ### calculate Capex for the Heating systems and their Operation & Maintenance contribution to the Opex
    heating_services = ['Qhs_sys', 'Qhpro_sys']
    for service in heating_services:
        fields_to_plot.extend([service + '_total_capex_USD', service + '_capex_a_USD', service + '_opex_fixed_USD'])
        # calculate the total and relative costs
        heating[service + '_total_capex_USD'] = heating[service + '0_kW'] * heating['CAPEX_USD2015kW']
        heating[service + '_capex_a_USD'] = np.vectorize(calc_capex_annualized)(heating[service + '_total_capex_USD'],
                                                                             heating['IR_%'] / 100,
                                                                             heating['LT_yr'])
        heating[service + '_opex_fixed_USD'] = heating[service + '_total_capex_USD'] * heating['O&M_%'] / 100
        heating[service + '_opex_fixed_a_USD'] = np.vectorize(calc_opex_annualized)(heating[service + '_opex_fixed_USD'],
                                                                                   heating['IR_%'] / 100,
                                                                                   heating['LT_yr'])

    ### calculate Capex for the Hot water systems and their Operation & Maintenance contribution to the Opex
    dhw_services = ['Qww_sys']
    for service in dhw_services:
        fields_to_plot.extend([service + '_total_capex_USD', service + '_capex_a_USD', service + '_opex_yr'])
        # calculate the total and relative costs
        dhw[service + '_total_capex_USD'] = dhw[service + '0_kW'] * dhw['CAPEX_USD2015kW']
        dhw[service + '_capex_a_USD'] = np.vectorize(calc_capex_annualized)(dhw[service + '_total_capex_USD'],
                                                                         dhw['IR_%'] / 100,
                                                                         dhw['LT_yr'])
        dhw[service + '_opex_fixed_USD'] = dhw[service + '_total_capex_USD'] * dhw['O&M_%'] / 100
        dhw[service + '_opex_fixed_a_USD'] = np.vectorize(calc_opex_annualized)(dhw[service + '_opex_fixed_USD'],
                                                                               dhw['IR_%'] / 100,
                                                                               dhw['LT_yr'])

    ### calculate Capex for the cooling systems and their Operation & Maintenance contribution to the Opex
    cooling_services = ['QC_sys']
    for service in cooling_services:
        fields_to_plot.extend([service + '_total_capex_USD', service + '_capex_a_USD', service + '_opex_yr'])
        # change price to that of local electricity mix
        # calculate the total and relative costs
        cooling[service + '_total_capex_USD'] = cooling[service + '0_kW'] * cooling['CAPEX_USD2015kW']
        cooling[service + '_capex_a_USD'] = np.vectorize(calc_capex_annualized)(cooling[service + '_total_capex_USD'],
                                                                             cooling['IR_%'] / 100,
                                                                             cooling['LT_yr'])
        cooling[service + '_opex_fixed_USD'] = cooling[service + '_total_capex_USD'] * cooling['O&M_%'] / 100
        cooling[service + '_opex_fixed_a_USD'] = np.vectorize(calc_opex_annualized)(cooling[service + '_opex_fixed_USD'],
                                                                                   cooling['IR_%'] / 100,
                                                                                   cooling['LT_yr'])

    ###  Calculate Capex for the electrical systems(E/I&C and PV) and their Operation & Maintenance contribution to the Opex
    electricity_services = ['E_sys']
    for service in electricity_services:
        fields_to_plot.extend([service + '_total_capex_USD', service + '_capex_a_USD', service + '_opex_yr'])
        electricity[service + '_total_capex_USD'] = electricity[service + '0_kW'] * electricity['CAPEX_USD2015kW']
        electricity[service + '_capex_a_USD'] = np.vectorize(calc_capex_annualized)(electricity[service + '_total_capex_USD'],
                                                                                 electricity['IR_%'] / 100,
                                                                                 electricity['LT_yr'])
        electricity[service + '_opex_fixed_USD'] = electricity[service + '_sys_total_capex'] * electricity['O&M_%'] / 100
        electricity[service + '_opex_fixed_a_USD'] = np.vectorize(calc_opex_annualized)(electricity[service + '_opex_fixed_USD'],
                                                                                        electricity['IR_%'] / 100,
                                                                                         electricity['LT_yr'])

    """"
    VARIABLE OPEX Calculations
    """
    ### calculate the Opex of feedstock consumption for heating
    heating_services = ['OIL_hs', 'NG_hs', 'WOOD_hs', 'COAL_hs', 'GRID_hs']
    for service in heating_services:
        fields_to_plot.extend([service + '_opex_var_USD', service + '_opex_var_a_USD'])
        heating[service + '_opex_var_USD'] = heating[service + '_MWhyr'] * heating['Opex_var_buy_USD2015kWh'] * 1000
        heating[service + '_opex_var_a_USD'] = np.vectorize(calc_opex_annualized)(heating[service + '_opex_var_USD'],
                                                                                 heating['IR_%'] / 100,
                                                                                 heating['LT_yr'])

    ### calculate the Opex of feedstock consumption for dhw
    dhw_services = ['OIL_ww', 'NG_ww', 'WOOD_ww', 'COAL_ww', 'GRID_ww']
    for service in dhw_services:
        fields_to_plot.extend([service + '_opex_var_USD', service + '_opex_var_a_USD'])
        dhw[service + '_opex_var_USD'] = dhw[service + '_MWhyr'] * dhw['Opex_var_buy_USD2015kWh'] * 1000
        dhw[service + '_opex_var_USD'] = np.vectorize(calc_opex_annualized)(dhw[service + '_opex_var_USD'],
                                                                             dhw['IR_%'] / 100, dhw['LT_yr'])

    ### calculate the Opex of feedstock consumption for cooling
    cooling_services = ['GRID_cs', 'GRID_cdata', 'GRID_cre', 'DC_cs']
    for service in cooling_services:
        fields_to_plot.extend([service + '_opex_var_USD', service + '_opex_var_a_USD'])
        cooling[service + '_opex_var_USD'] = cooling[service + '_MWhyr'] * cooling['Opex_var_buy_USD2015kWh'] * 1000
        cooling[service + '_opex_var_a_USD'] = np.vectorize(calc_opex_annualized)(cooling[service + '_opex_var_USD'],
                                                                                 cooling['IR_%'] / 100,
                                                                                 cooling['LT_yr'])

    ### calculate the Opex of feedstock consumption for rest electricity (appliances, lighting, etc.)
    electricity_services = ['GRID_pro', 'GRID_l', 'GRID_aux', 'GRID_v', 'GRID_a',
                            'GRID_data']  # PV is internal(only O&M)
    for service in electricity_services:
        fields_to_plot.extend([service + '_opex_var_USD', service + '_opex_var_a_USD'])
        electricity[service + '_opex_var_USD'] = electricity[service + '_MWhyr'] * electricity[
            'Opex_var_buy_USD2015kWh'] * 1000
        electricity[service + '_opex_var_a_USD'] = np.vectorize(calc_opex_annualized)(
            electricity[service + '_opex_var_USD'],
            electricity['IR_%'] / 100, electricity['LT_yr'])

    # create and save results
    result = heating.merge(dhw, on='Name', suffixes=('', '_dhw'))
    result = result.merge(cooling, on='Name', suffixes=('', '_cooling'))
    result = result.merge(electricity, on='Name', suffixes=('', '_electricity'))

    #sum up for all fields
    result['Capex_sys_total_USD'] = 0.0
    result['Capex_sys_a_USD'] = 0.0
    result['Opex_sys_var_USD'] = 0.0
    result['Opex_sys_var_a_USD'] = 0.0
    result['Opex_sys_fixed_USD'] = 0.0
    result['Opex_sys_fixed_a_USD'] = 0.0
    for field in fields_to_plot:
        #capex system
        if '_total_capex_USD' in field:
            result['Capex_sys_total_USD'] += result[field]
        if '_capex_a_USD' in field:
            result['Capex_sys_a_USD'] += result[field]

        # opex system
        if '_opex_var_USD' in field:
            result['Opex_var_USD'] += result[field]
        if '_opex_fixed_USD' in field:
            result['Opex_fixed_USD'] += result[field]
        if '_opex_var_a_USD' in field:
            result['Opex_var_a_USD'] += result[field]
        if '_opex_fixed_a_USD' in field:
            result['Opex_fixed_a_USD'] += result[field]

    # Yearly OPEX
    result['Opex_sys_USD'] = result['Opex_sys_fixed_USD'] + result['Opex_sys_var_USD']

    # Annualized (Discounted) OPEX
    result['Opex_sys_a_USD'] = result['Opex_sys_fixed_a_USD'] + result['Opex_sys_var_a_USD']

    # Total Annualized (Discounted) Cost = Equivalent Annualized Cost
    result['TAC_sys_a_USD'] = result['Capex_sys_a_USD'] + result['Opex_sys_a_USD']


    # CapEx
    if capital:
        fields_to_plot.extend(['Capex_a_sys_disconnected_USD',
                               'Capex_a_sys_connected_USD',
                               'Capex_total_sys_connected_USD',
                               'Capex_total_sys_disconnected_USD',
                               'Capex_total_sys_USD',
                               'Capex_sys_a_USD',
                               'TAC_sys_a_USD'])
    # OpEx
    if operational:
        fields_to_plot.extend(['Opex_a_sys_connected_USD',
                               'Opex_a_sys_disconnected_USD',
                               'Opex_fixed_USD',
                               'Opex_fixed_a_USD',
                               'Opex_var_USD',
                               'Opex_var_a_USD',
                               'Opex_sys_USD',
                               'Opex_sys_a_USD'
                               ])





    """
    SPLIT INTO DISCONNECTED AND cONNECTED:
    annualized costs for DHW and electricity services (appliances, lighting, etc.) assigned to disconnected, 
    assuming WW and electricity services are always decentralized
    """

    result['Opex_a_sys_disconnected_USD'] = result['Qww_sys_a_opex_yr'] + \
                                            result['GRID_sys_a_opex_yr'] + \
                                            result['PV_sys_a_opex_yr'] + \
                                            result['OIL_ww_sys_a_opex_yr'] + \
                                            result['NG_ww_sys_a_opex_yr'] + \
                                            result['WOOD_ww_sys_a_opex_yr'] + \
                                            result['COAL_ww_sys_a_opex_yr'] + \
                                            result['GRID_ww_sys_a_opex_yr'] + \
                                            result['GRID_pro_sys_a_opex_yr'] + \
                                            result['GRID_l_sys_a_opex_yr'] + \
                                            result['GRID_aux_sys_a_opex_yr'] + \
                                            result['GRID_v_sys_a_opex_yr'] + \
                                            result['GRID_a_sys_a_opex_yr'] + \
                                            result['GRID_data_sys_a_opex_yr']

    result['Capex_a_sys_disconnected_USD'] = result['Qww_sys_capex_yr'] + \
                                             result['GRID_sys_capex_yr'] + \
                                             result['PV_sys_capex_yr']

    result['Capex_total_sys_disconnected_USD'] = result['Qww_sys_total_capex'] + \
                                                 result['GRID_sys_total_capex'] + \
                                                 result['PV_sys_total_capex']

    result['Opex_a_sys_connected_USD'] = 0
    result['Capex_a_sys_connected_USD'] = 0
    result['Capex_total_sys_connected_USD'] = 0

    ### assign the cost of heating and cooling to the connected/ disconnected Costs depending on chosen system

    ### check heating system scale and assign costs accordingly
    scale_technology = heating['scale']
    if scale_technology.str.contains('BUILDING').sum():
        print('building scale heating system')
        # index_list = factors_heating.index[factors_heating['scale'].str.contains("NONE")].tolist()
        result['Opex_a_sys_disconnected_USD'] += result['QH_sys_a_opex_yr'] + \
                                                 result['OIL_hs_sys_a_opex_yr'] + \
                                                 result['NG_hs_sys_a_opex_yr'] + \
                                                 result['WOOD_hs_sys_a_opex_yr'] + \
                                                 result['COAL_hs_sys_a_opex_yr'] + \
                                                 result['GRID_hs_sys_a_opex_yr']

        result['Capex_a_sys_disconnected_USD'] += result['QH_sys_capex_yr']
        result['Capex_total_sys_disconnected_USD'] += result['QH_sys_total_capex']

    elif scale_technology.str.contains("DISTRICT").sum():
        print('district scale heating system')
        result['Opex_a_sys_connected_USD'] += result['QH_sys_a_opex_yr'] + \
                                              result['OIL_hs_sys_a_opex_yr'] + \
                                              result['NG_hs_sys_a_opex_yr'] + \
                                              result['WOOD_hs_sys_a_opex_yr'] + \
                                              result['COAL_hs_sys_a_opex_yr'] + \
                                              result['GRID_hs_sys_a_opex_yr']

        result['Capex_a_sys_connected_USD'] += result['QH_sys_capex_yr']
        result['Capex_total_sys_connected_USD'] += result['QH_sys_total_capex']

    elif scale_technology.str.contains("NONE").sum():
        print("No heating in this scenario.")

    ### check cooling system scale and assign costs accordingly
    scale_technology = cooling['scale']
    if scale_technology.str.contains("BUILDING").sum():
        print('building scale cooling system')
        result['Opex_a_sys_disconnected_USD'] += result['QC_sys_a_opex_yr'] + \
                                                 result['GRID_cs_sys_a_opex_yr'] + \
                                                 result['GRID_cdata_sys_a_opex_yr'] + \
                                                 result['GRID_cre_sys_a_opex_yr']

        result['Capex_a_sys_disconnected_USD'] += result['QC_sys_capex_yr']
        result['Capex_total_sys_disconnected_USD'] += result['QC_sys_total_capex']

    elif scale_technology.str.contains("DISTRICT").sum():
        print('district scale cooling system')
        result['Opex_a_sys_connected_USD'] += result['QC_sys_a_opex_yr'] + \
                                              result['DC_cs_sys_a_opex_yr'] + \
                                              result['GRID_cs_sys_a_opex_yr'] + \
                                              result['GRID_cdata_sys_a_opex_yr'] + \
                                              result['GRID_cre_sys_a_opex_yr']

        result['Capex_a_sys_connected_USD'] += result['QC_sys_capex_yr']
        result['Capex_total_sys_connected_USD'] += result['QC_sys_total_capex']

    elif scale_technology.str.contains("NONE").sum():
        print("No cooling in this scenario.")

    result_out = result[['Name'] + fields_to_plot]
    # result_out = result_out.loc[:, (result_out != 0).any(axis=0)] #delete all columns which are 0

    result_out.to_csv(
        locator.get_costs_operation_file(), index=False, float_format='%.2f')


# Calculates the EQUIVALENT ANNUAL COSTS (1. Step PRESENT VALUE OF COSTS (PVC), 2. Step EQUIVALENT ANNUAL COSTS)
def calc_opex_annualized(OpC, Inv_IR, Inv_LT):
    opex_list = [0.0]
    opex_list.extend(Inv_LT * [OpC])
    opexnpv = np.npv(Inv_IR, opex_list)
    EAC = ((opexnpv * Inv_IR) / (1 - (1 + Inv_IR) ** (-Inv_LT)))  # calculate positive EAC
    return EAC


def calc_capex_annualized(InvC, Inv_IR, Inv_LT):
    return -((-InvC * Inv_IR) / (1 - (1 + Inv_IR) ** (-Inv_LT)))
    # InvC * Inv_IR) * (1 + Inv_IR) ** Inv_LT / ((1 + Inv_IR) ** Inv_LT - 1)


def main(config):
    locator = cea.inputlocator.InputLocator(scenario=config.scenario)

    print('Running system-costs with scenario = %s' % config.scenario)

    costs_main(locator=locator, config=config)


if __name__ == '__main__':
    main(cea.config.Configuration())
