from abc import ABC, abstractmethod
import os


# Base mapper class, cannot be instantiated but will populate all common data between inherited classes
class Map(ABC):
    @abstractmethod
    def __init__(self):
        pass

# Mapper for GARD type input
class GardMap(Map):
    def __init__(self):
        self.root = os.getcwd()
        print(self.root)

    def _get_gard_data(self):
        pass
    def _create_gard_data(self,data):
        pass
    def _convert_disease_string(self,text):
        pass
    def _convert_data(self):
        pass
    def _use_phrasematcher(self):
        pass

# Mapper for Article Abstract type input
class AbstractMap(Map):
    def __init__(self):
        self.root = os.getcwd()
        print('abstract')

    

