#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility functions.
"""

import json
from pathlib import Path
from typing import Union


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

def get_data_path(path:Union[Path, str], data_path:Union[Path,str]=None) -> Path:
    """
    Creates a data folder for the results to be written to.

    Parameters
    ----------
    path: str, Path
        Directory for data to be written to (eg. data\path).
    
    data_path: str, Path (Optional, default None)
        Directory where the data folder will be written to.
        Default is Path(Path.cwd(), 'data')

    Returns
    -------
    Path object for folder of results.
    """
    if data_path is None:
        folder = Path(Path.cwd(), 'data')
    else:
        folder = data_path
    
    folder_path = Path(folder, path)
    check_folder(folder_path)
    return folder_path
