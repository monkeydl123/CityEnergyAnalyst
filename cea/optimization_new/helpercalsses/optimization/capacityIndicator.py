"""
Capacity Indicator Vector Class:
Capacity indicators are float values in [0,1] that indicate to what percentage of the maximum capacity
each viable component of a supply system structure is installed in a specific configuration of that supply system.

E.g. The supplySystemStructure-object indicates that the maximum viable capacity for a vapour compression chiller is
2MW (since this structure is laid out to provide a maximum of 2MW of cooling). If the capacity indicator is 0.5, that
would mean, that the capacity of the installed vapour compression chiller in that system configuration would be 1MW.

Detailed Capacity Indicator Vector Example:
values = [0.3, 0.1, 0.2, 0.3, 0.4, 0.7, 0.8, 0.2, 0.3]
categories = ['primary', 'primary', 'primary', 'secondary', 'secondary', 'secondary', 'secondary', 'tertiary', 'tertiary']
codes = ['VCC1', 'VCC2', 'ACH1', 'BO1', 'BO2', 'OEHR1', 'FORC1', 'CT1', 'CT2']

The <CapacityIndicatorVector>-class behaves like a sequence (which is relevant for some methods of the deap-library)
"""

__author__ = "Mathias Niffeler"
__copyright__ = "Copyright 2023, Cooling Singapore"
__credits__ = ["Mathias Niffeler"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "NA"
__email__ = "mathias.niffeler@sec.ethz.ch"
__status__ = "Production"

import copy
import random
import numpy as np

from deap import tools

from cea.optimization_new.helpercalsses.optimization.fitness import Fitness


class CapacityIndicator(object):
    def __init__(self, component_category=None, component_code=None, value=None):
        if value:
            self.value = value
        else:
            self.value = 1
        self.code = component_code
        self.category = component_category

    @property
    def category(self):
        return self._category

    @category.setter
    def category(self, new_category):
        if new_category and not (new_category in ['primary', 'secondary', 'tertiary']):
            raise ValueError("The capacity indicators' associated supply system category needs to be either: "
                             "'primary', 'secondary' or 'tertiary'")
        else:
            self._category = new_category

    @property
    def code(self):
        return self._code

    @code.setter
    def code(self, new_code):
        if new_code and not isinstance(new_code, str):
            raise ValueError("Component codes need to be of type string.")
        else:
            self._code = new_code

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        if new_value and not 0 <= new_value <= 1:
            raise ValueError("The capacity indicator values each need to be between 0 and 1.")
        else:
            self._value = round(new_value, 2)

    def change_value(self, new_value, inplace=True):
        if inplace:
            self.value = new_value
            return self
        else:
            new_capacity_indicator = copy.deepcopy(self)
            new_capacity_indicator.value = new_value
            return new_capacity_indicator


class CapacityIndicatorVector(object):

    def __init__(self, capacity_indicators_list=None):
        if not capacity_indicators_list:
            self._capacity_indicators = [CapacityIndicator()]
        else:
            self.capacity_indicators = capacity_indicators_list
        self.fitness = Fitness()

    @property
    def capacity_indicators(self):
        return self._capacity_indicators

    @capacity_indicators.setter
    def capacity_indicators(self, new_capacity_indicators):
        if not all([isinstance(capacity_indicator, CapacityIndicator) for capacity_indicator in new_capacity_indicators]):
            raise ValueError("Elements of the capacity indicators vector can only be instances of CapacityIndicator.")
        elif not new_capacity_indicators == [] and \
                not all(CapacityIndicatorVector._categories_cover_demand(new_capacity_indicators)):
            self._capacity_indicators = CapacityIndicatorVector._correct_values(new_capacity_indicators)
        else:
            self._capacity_indicators = new_capacity_indicators

    @property
    def values(self):
        ci_values = [capacity_indicator.value for capacity_indicator in self.capacity_indicators]
        return ci_values

    @values.setter
    def values(self, new_values):
        if not (isinstance(new_values, list) and len(new_values) == len(self)):
            raise ValueError("The new capacity indicator vector values need to be a list and correspond to the "
                             "length of the supply system structure's capacity indicator vector.")
        elif not new_values == [] and \
                not all([sum([value for i, value in enumerate(new_values)
                              if self.capacity_indicators[i].category == category]) >= 1
                         for category in set([ci.category for ci in self.capacity_indicators])]):
            raise ValueError("The capacity indicator values for each supply system placement category need to "
                             "add up to at least 1 (so that the system demand can be met).")
        else:
            for i in range(len(self)):
                self[i] = new_values[i]

    @property
    def fitness(self):
        return self._fitness

    @fitness.setter
    def fitness(self, new_fitness):
        if not isinstance(new_fitness, Fitness):
            raise ValueError("The indicated fitness value is not an object of the Fitness class. The deap library's "
                             "selection functions need the attributes of that class to operate properly.")
        else:
            self._fitness = new_fitness

    def __len__(self):
        return len(self.capacity_indicators)

    def __getitem__(self, item):
        """
        Allows calling the capacity indicator vector (civ) values easily, by indexing the civ directly.
        (e.g. civ.values: [0.8, 0.2, 0.5, 0.2, 1.0],
        """
        if isinstance(item, slice):
            selected_capacity_indicators = self._capacity_indicators[item]
            return [capacity_indicator.value for capacity_indicator in selected_capacity_indicators]
        elif isinstance(item, int):
            return self.capacity_indicators[item].value
        else:
            return None

    def __setitem__(self, key, value):
        """
        Allows resetting the values of the capacity indicator vector (civ) easily, by assigning the list of new
        values to the civ directly. (e.g. civ = [0.3, 0.4, 0.8, 0.1, 0.9] -> civ.values: [0.3, 0.4, 0.8, 0.1, 0.9])
        """
        if isinstance(key, slice):
            if key.start:
                ind_start = key.start
            else:
                ind_start = 0
            if key.stop:
                ind_stop = key.stop
            else:
                ind_stop = len(self)
            if key.step:
                ind_step = key.step
            else:
                ind_step = 1
            for index in list(range(ind_start, ind_stop, ind_step)):
                self.capacity_indicators[index].value = round(value[index-ind_start], 2)
        elif isinstance(key, int):
            self.capacity_indicators[key].value = round(value, 2)

    def reset(self):
        """
        Reset the entire capacity indicator vector at once in order to correct capacity indicator values if necessary
        (checked in the setter) after mutation or recombination.
        e.g. if the capacity indicators of a given category are <1, i.e. cannot supply the required demand
        """
        self.capacity_indicators = self.capacity_indicators

        return self

    def get_cat(self, category):
        """
        Get values of all capacity indicators corresponding to the chosen supply system category.
        """
        if not (category in ['primary', 'secondary', 'tertiary']):
            raise ValueError(f"The indicated supply system category ({category}) doesn't exist.")
        else:
            values_of_cat = [self.capacity_indicators[i].value for i in range(len(self))
                             if self.capacity_indicators[i].category == category]
            return values_of_cat

    def set_cat(self, category, new_values):
        """
        Set values of all capacity indicators corresponding to the chosen supply system category.
        """
        if not (category in ['primary', 'secondary', 'tertiary']):
            raise ValueError(f"The indicated supply system category ({category}) doesn't exist.")
        else:
            new_val_vector = []
            for cat in ['primary', 'secondary', 'tertiary']:
                if cat == category:
                    new_val_vector += new_values
                else:
                    new_val_vector += self.get_cat(cat)
            self.values = new_val_vector

    @staticmethod
    def _categories_cover_demand(new_capacity_indicators):
        """
        check if the component categories in a list of new capacity indicators cover the maximum required demand
        (i.e. add up to >= 1)
        """
        categories_cover_demand = [sum([capacity_indicator.value for capacity_indicator in new_capacity_indicators
                                        if capacity_indicator.category == category]) >= 1
                                   for category in list(set([ci.category for ci in new_capacity_indicators]))
                                   if any([capacity_indicator.category == category
                                           for capacity_indicator in new_capacity_indicators])]
        return categories_cover_demand

    @staticmethod
    def _correct_values(new_capacity_indicators):
        """
        Correct a tentative capacity indicator vector's values by following these steps:
            1. Find out which category's capacity indicators do not add up to 1 (i.e. potentially can not meet demand)
            2. For the relevant categories identify the component with the highest tentative capacity indicator
            3. Change that components capacity indicator so that the category's CIs add up to 1.
        """
        # Step 1
        component_categories = list(set([ci.category for ci in new_capacity_indicators]))
        categories_cover_demand = CapacityIndicatorVector._categories_cover_demand(new_capacity_indicators)
        understocked_categories = [category for i, category in enumerate(component_categories)
                                   if not categories_cover_demand[i]]

        for category in understocked_categories:
            # Step 2
            ci_values_in_cat = {ci.code: ci.value for ci in new_capacity_indicators if ci.category == category}
            highest_ci_component = [component for component, value in ci_values_in_cat.items()
                                    if value == max(ci_values_in_cat.values())][0]
            # Step 3
            corrected_ci_value = 1 - (sum(ci_values_in_cat.values()) - max(ci_values_in_cat.values()))
            new_capacity_indicators = [ci if not ci.code == highest_ci_component
                                       else ci.change_value(corrected_ci_value)
                                       for ci in new_capacity_indicators]

        return new_capacity_indicators

    @staticmethod
    def generate(civ_structure, method='random'):
        """
        Generate a new capacity indicator vector randomly.
        :param civ_structure: structure of the capacity indicator vector (i.e. defined codes and categories attributes)
        :param method: method of generation of the capacity indicators values
        """
        civ = copy.deepcopy(civ_structure)

        if method == 'random':
            i = 0
            while i <= 10:
                try:
                    civ.values = [random.randint(0, 100) / 100 for _ in civ_structure]
                except ValueError:
                    i += 1
                    continue
                break

        return civ.capacity_indicators

    @staticmethod
    def mutate(civ, algorithm=None):
        """
        Mutate a capacity indicator vector (inplace) based on the chosen mutation algorithm.
        """
        if algorithm.mutation == "UniformBounded":  # by dividing by setting low=0, up=100 and dividing by 0)
            i = 0
            while i <= 0:
                try:
                    civ_values_percentages = np.array(civ.values) * 100
                    mut_percentages = tools.mutUniformInt(civ_values_percentages, low=0, up=100, indpb=algorithm.mut_prob)
                    civ.values = list(np.array(mut_percentages[0]) / 100)
                except ValueError:
                    i += 1
                    continue
                break
            mutated_civ = tuple([civ])
        elif algorithm.mutation == "PolynomialBounded":
            mutated_civ = tools.mutPolynomialBounded(civ, eta=algorithm.mut_eta, low=0, up=1, indpb=algorithm.mut_prob)
        else:
            raise ValueError(f"The chosen mutation method ({algorithm.mutation}) has not been implemented for "
                             f"capacity indicator vectors.")

        # reset to correct potential format of the capacity indicator vector
        mutated_civ[0].reset()

        return mutated_civ

    @staticmethod
    def mate(civ_1, civ_2, algorithm=None):
        """
        Recombine two capacity indicator vectors (inplace) based on the chosen crossover algorithm
        """
        if algorithm.crossover == "OnePoint":
            recombined_civs = tools.cxOnePoint(civ_1, civ_2)
        elif algorithm.crossover == "TowPoint":
            recombined_civs = tools.cxTwoPoint(civ_1, civ_2)
        elif algorithm.crossover == "Uniform":
            recombined_civs = tools.cxUniform(civ_1, civ_2, indpb=algorithm.cx_prob)
        else:
            raise ValueError(f"The chosen crossover method ({algorithm.crossover}) has not been implemented for "
                             f"capacity indicator vectors.")

        # reset to correct potential error in format of the capacity indicator vectors
        recombined_civs[0].reset()
        recombined_civs[1].reset()

        return recombined_civs