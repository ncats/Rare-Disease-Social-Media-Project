"""
.. currentmodule:: data_gathering.match_gard_subreddit.py

Matches rare diseases from neo4j GARD database (neo4j_rare_disease_list.csv) to the primary
subreddit list (primary_subreddit_list.parquet or .csv) to identify rare disease subreddits.
Saves a .csv file of the matches.
"""
from os.path import join
import sys
import os
import re
import json
import pandas as pd
from tqdm import tqdm

def dump_json(json_dict,path,filename):
    """
    Dumps data to a json file given a filename.

    :param json_dict: Dictionary to be written as JSON file.
    :type: dict.

    :param path: Path for folder of file to be written.
    :type path: str.

    :param filename: Filename of file to be written.
    :type filename: str.
    """
    # Checks if folder exists.
    check_folder(path)

    # Writes json file to path using given filename.
    taxon_ids_path = os.path.join(path,filename+'.json')
    with open(taxon_ids_path,mode= 'w+',encoding='utf-8') as file:
        json.dump(json_dict, file)

def check_folder(path):
    """
    Checks if path exists and creates it if it does not.

    :param path: Path for folder.
    :type path: str
    """
    # Checks if folder exists.
    if not os.path.exists(path):
        # If folder does not exist it creates it.
        os.makedirs(path)

class MatchGardSubreddit:
    """
    A class to match rare disease data to Reddit subreddits.
    """
    def __init__(self,path = "../data"):
        self.path = path
        self.gard = self._read_gard_data()
        self.subreddit = self._read_subreddit_data()
        self.matches = self._find_matches()

        # 175 diseases with 1396 subreddit matches with 1280 unique subreddits.
        # Several diseases have large amounts of matches (N > 10):
        #   EAF 542 -> No matches to (2) synonyms.
        #   Noma 288 -> No matches to (5) synonyms.
        #   SARS 74 -> 1 false positive to (1) synonym:
        #       ('severe acute respiratory syndrome': 'COVID19NYC)
        #   Kuru 64 -> No synonyms.
        #   Koro 58 -> No matches to (3) synonyms.
        #   N syndrome 34 -> (2) synonyms with 36 false positives.
        #   Cluttering 29 -> No matches to (1) synonym.
        #   Rickets 15 -> No matches to (4) synonyms.

        dump_json(self.matches,self.path,'GARD_and_subreddit_matches_data_interim')

    def _read_gard_data(self):
        """
        Reads the neo4j rare disease data in as a pandas DataFrame.

        :return: pandas DataFrame.
        """
        return pd.read_csv(join(self.path,'neo4j_rare_disease_list.csv'))

    def _read_subreddit_data(self):
        """
        Reads the subreddit data in as a pandas DataFrame. Tries to read the .csv in as default,
        then tries to read the .parquet version if the .csv is not found.

        :return: pandas DataFrame.
        """
        try:
            data = pd.read_csv(join(self.path,'primary_subreddit_list.csv'))
        except FileNotFoundError:
            data = pd.read_parquet(join(self.path,'primary_subreddit_list.parquet'))
        return data

    def _find_matches(self):
        """
        Finds indexes of subreddits that match the diseases contained in the gard data. Only uses
        name of disease. Using synonyms of diseases to match creates too many false positive
        matches to filter out with very little intersection of matches with names. Higher quality
        matches found using disease name only to subreddit description.

        :return: Dictionary of matches.
        """
        # Creates the progress bar since this may take up to 30 minutes or more.
        with tqdm(total=len(self.gard['Name']),file=sys.stdout) as pbar:
            # Sets the progress bar description.
            pbar.set_description('Matching GARD ids to subreddit descriptions: ')
            # Initialize match dictionary.
            match_dict = {}
            # Iterate over diseases in GARD data.
            for disease in self.gard['Name']:
                # Uses the pandas.Series.str.contains method to find indexes of matches.
                #   na: fill value for missing values.
                #   case: if False, case insensitive.
                #   regex: if True, assumes pattern is a regular expression.
                # Set na = False to fill in missing values as False, case = False so that search
                # ignored case, and regex = False to not use regular expressions which slightly
                # reduced the search time.
                match_index = self.subreddit.index[self.subreddit['description'].str.contains(
                            disease, na=False, case=False, regex=False)].tolist()
                # Only adds indexes found.
                if match_index:
                    match_dict[disease] = match_index
                # Updates progress bar.
                pbar.update()
        return match_dict

    def find_synonyms(self, disease):
        """
        Function to find the synonyms of a disease in the GARD data.

        :param disease: Name of a disease.
        :type disease: str.

        :return: List of synonyms for a disease.
        """
        synonyms = self.gard[self.gard['Name'] == disease]['Synonyms'].item()
        if isinstance(synonyms, float):
            synonyms = re.findall("'([^']*)'", synonyms)
        return synonyms

    def find_synonym_matches(self, disease):
        """
        Function to find the subreddit matches to a disease in the GARD data.

        :param disease: Name of a disease.
        :type disease: str.

        :return: Dictionary of subreddit matches with keys being the synonyms.
        """
        synonyms = self.find_synonyms(disease)
        match_dict = {}

        if isinstance(synonyms, float):
            print('No synonyms')
            return match_dict

        if len(synonyms) > 1:
            for synonym in synonyms:
                match_index = self.subreddit.index[self.subreddit['description'].str.contains(
                    synonym,na=False,case=False,regex=False)].tolist()
                match_dict[synonym] = match_index
        else:
            match_index = self.subreddit.index[self.subreddit['description'].str.contains(
                synonyms[0],na=False,case=False,regex=False)].tolist()
            match_dict[synonyms[0]] = match_index

        return match_dict

    def find_subreddit(self,index):
        """
        Function to find the subreddit name given an index.

        :param index: Index or list of indexes from subreddit data.
        :type index: int, int array, list of int.

        :return: List of the subreddit name(s) for the subreddit index(es)
        """
        if len(index) >= 1:
            result = self.subreddit.iloc[index]['name'].tolist()
        else:
            result = False
        return result

def main():
    """
    Matches Gard data from query_gard to subreddit data from convert_subreddit.
    Creates a csv of resulting matches.
    """
    MatchGardSubreddit()

if __name__ == '__main__':
    main()
