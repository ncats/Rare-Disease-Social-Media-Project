#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Legacy script for querying gard database and writing result to file.
Currently cannot query the GARD database.
"""

from pathlib import Path
from typing import Union
from neo4j import GraphDatabase
from rdsmproj import utils

class App:
    """
    Queries the Neo4j NCATS database on rare diseases. Optional $is_rare can be set to False to
    retrieve the non-rare diseases in the rare disease database. Writes results to a .json file.

    :param uri: url for connecting to NCATS GARD database.

    :param path: Path for storing the .csv file of the results of the query.
    """

    def __init__(self, uri:str, path:Union[str, Path, None] = None):
        self.driver = GraphDatabase.driver(uri)
        # If no path is given, uses default data path.
        if path is None:
            path = utils.find_data_path()
        self.path = path
        # Checks if folder for data path exists, creates if it does not.
        utils.check_folder(self.path)

    def close(self) -> None:
        """
        Closes driver connection.
        """
        # Don't forget to close the driver connection when you are finished with it.
        self.driver.close()

    def find_gard_data(self, is_rare:bool=True) -> dict:
        """
        Queries the GARD database.

        :param is_rare: boolean for is_rare column in GARD data. True yields only rare diseases.
                        False only yields non-rare diseases.

        :return: Result of the query.
        """
        # Queries the database.
        with self.driver.session() as session:
            result = session.read_transaction(self._find_and_return_data,is_rare)
        return result

    @staticmethod
    def _find_and_return_data(tx, is_rare:bool) -> dict:
        """
        Neo4j query finds all nodes (d) in DATA. It then finds the nodes that satisfy the
        is_rare == $is_rare statement. Finally, it returns all nodes that satisfy the statement
        along with the gard_id, name, is_rare, synonyms, and categories properties. These are the
        only properties that seemed relevant at the time.

        :param is_rare: Boolean value for is_rare property in DATA.

        :return: Dictionary of resulting query.
        """

        # Neo4j Query finds all nodes (d) in DATA.
        # It then finds the nodes that satisfies the is_rare == $is_rare statement.
        # Finally, it returns all nodes that satisfy above statement along with the gard_id, name,
        # is_rare, synonyms, and categories properties.
        query = (
            "MATCH (d:DATA) "
            "WHERE d.is_rare = $is_rare "
            "RETURN d.gard_id, d.name, d.is_rare, d.synonyms, d.categories"
        )
        result = tx.run(query, is_rare=is_rare)

        # Returns a dictionary of the resulting query data.
        return [{'GARD id': record['d.gard_id'],
                 'Name': record['d.name'],
                 'Synonyms': record['d.synonyms'],
                 'Categories': record['d.categories'],
                 'is_rare': record['d.is_rare']} for record in result]


if __name__ == "__main__":
    # NCATS Database at: bolt://disease.ncats.io:80
    SCHEME = "bolt"  # BoltDriver with no encryption
    HOST_NAME = "disease.ncats.io"
    PORT = 80
    url = f"{SCHEME}://{HOST_NAME}:{PORT}"
    app = App(url)
    query_result = app.find_gard_data()
    utils.dump_json(query_result, app.path, 'neo4j_rare_disease_list')
    app.close()
