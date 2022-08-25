#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility functions.
"""

import json
from pathlib import Path
from typing import Union

__author__ = 'Bradley Karas'

def load_json(path:Union[str,Path]) -> dict:
    """
    Loads jsons given a path.

    Parameters
    ----------
    path: str, Path
        Path for file to be read.

    Returns
    -------
    Dictionary of data loaded from JSON file.
    """
    with open(path,mode='r',encoding='utf-8') as f:
        file = json.load(f)
    return file

def dump_json(json_dict:dict, path:Union[str,Path], filename:str):
    """
    Dumps data to a json file given a filename.

    Parameters
    ----------
    json_dict: dict
        Dictionary to be written as JSON file.

    path: str, Path
        Path for folder of file to be written.

    filename: str
        Filename of file to be written.
    """
    # Checks if folder exists.
    check_folder(path)

    # Writes json file to path using given filename.
    path = Path(path, filename+'.json')
    with open(path, mode= 'w+', encoding='utf-8') as file:
        json.dump(json_dict, file)

def check_folder(path:Union[str,Path]):
    """
    Checks if path exists and creates it if it does not.

    Parameters
    ----------
    path: str, Path
        Path for folder.
    """
    # Checks if folder exists.
    if not Path(path).is_dir():
        # If folder does not exist it creates it.
        Path(path).mkdir(parents=True, exist_ok=True)

def get_data_path(path:Union[Path, str]) -> Path:
    """
    Creates a data path: data/path where path is the directory for the data
    to be written to.

    Parameters
    ----------
    path: str, Path
        Directory for data to be written to.

    Returns
    -------
    Path object.
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

    Returns
    -------
    Path object.
    """
    # Find path for script.
    file_path = Path(__file__).parent.parent.resolve()
    # Create data path.
    data_path = Path(file_path, 'data')
    # Checks if directory exists and creates if it does not.
    check_folder(data_path)

    return data_path
