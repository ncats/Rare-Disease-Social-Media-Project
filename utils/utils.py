#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility functions.
"""

import json
import os
from pathlib import Path
from typing import Union


def load_json(path):
    """
    Loads jsons given a path.

    :param path: Path for file to be read.
    :type param: str.

    :return: Dictionary of data loaded from JSON file.
    """
    with open(path,mode='r',encoding='utf-8') as f:
        file = json.load(f)
    return file

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
    path = Path(path, filename+'.json')
    with open(path, mode= 'w+', encoding='utf-8') as file:
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

def get_data_path(path:Union[Path, str]) -> Path:
    """
    Creates a data path: data/path where path is the directory for the data
    to be written to.

    :param path: directory for data to be written to.
    :return: Path object path.
    """

    data_path = find_data_path()
    # Create data path.
    data_path = Path(data_path, path)
    # Checks if directory exists and creates if it does not.
    check_folder(data_path)

    return data_path

def find_data_path() -> Path:
    """
    Creates a data path: /data where the data will be written to.
    """
    # Find path for script.
    file_path = Path(__file__).parent.parent.resolve()
    # Create data path.
    data_path = Path(file_path, 'data')
    # Checks if directory exists and creates if it does not.
    check_folder(data_path)

    return data_path
