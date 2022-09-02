#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Get posts from subreddits.
"""
import logging
from pathlib import Path
from typing import Union, Optional
import datetime as dt
import time
from pmaw import PushshiftAPI
import pandas as pd
from rdsmproj import utils


# Sets the PushshiftAPI to ignore shards_down messages.
api = PushshiftAPI(shards_down_behavior=None)

class GetPosts:
    """
    Class to retrieve post data in a subreddit.
    Parameters
    ----------
    name: str
        Name of the subreddit to retrieve post data from.

    path: str, Path (Optional, default None)
        Path to where the subreddit data will be stored.

    silence: bool (Optional, default True)
        Silences the PushshiftAPI logger.
    
    pmaw_args: dict (Optional, default None)
        Pass arguments to pmaw api.search_comments
    """

    def __init__(self, name:str, path:Union[str,Path] = None,
                 silence:bool=True, pmaw_args:dict=None):

        # Sets name of subreddit.
        self.name = name

        # If silence is True, then it will silence the PushshiftAPI logger. Default is True.
        if silence:
            # Silences the PushshiftAPI logger.
            logger = logging.getLogger('pmaw')
            logger.setLevel(logging.WARNING)

        # Checks if path is given. Uses a default if not provided.
        if path is None:
            self.path = utils.get_data_path('posts')
        else:
            self.path = path

        # Sets the posts retrieved to 0 initially.
        self.post_num = 0

        # Passes optional arguments if pmaw_args is given.
        if pmaw_args:
            self.pmaw_args = pmaw_args
        else:
            self.pmaw_args = None

        # Calls the api to search for submissions.
        self._get_post_data()
        # Writes posts retrieved data from subreddit.
        self._write_post_data()

    def _get_post_data(self) -> None:
        """
        Calls the api to search for submissions for the subreddit.
        """
        try:
            # Tries to query PushShift for submission data of a given subreddit.
            posts = list(api.search_submissions(subreddit=self.name,
                                                metadata=True,
                                                **self.pmaw_args))
            # Checks if any posts were retrieved.
            if posts:
                # Sets the filename.
                filename = f'{self.name}_posts'
                # Dumps the retrieved data to a json file.
                utils.dump_json(posts, self.path, filename)
                # Sets the number of posts retrieved.
                self.post_num = len(posts)
                print(f'Retrieved {self.post_num} posts from the subreddit: {self.name}')
            else:
                print(f"No post data to be retrieved from subreddit: {self.name}")

        # Some subreddits give an IndexError when trying to retrieve data.
        except IndexError:
            print(f'IndexError for {self.name}!')

        # Pauses in between calls to the api.
        time.sleep(1)

    def _write_post_data(self) -> None:
        """
        Writes the post data for subreddits completed and number of posts retrieved.
        """
        # Sets the path to the post data file.
        post_file = Path(self.path, 'post_data.json')

        # Initializes post_temp dictionary.
        post_temp = {}
        # Checks if post data file exists.
        if post_file.is_file():
            # Loads the existing post data file.
            post_temp = utils.load_json(post_file)

        # Adds subreddit and number of posts retrieved to the dictionary.
        post_temp[self.name] = self.post_num
        # Writes the post data dictionary to a json file.
        utils.dump_json(post_temp, self.path, 'post_data')

def main():
    """
    Auto-magically gets the post data for subreddits that were matched to GARD data.
    """
    # Gets the data path.
    data_path = utils.find_data_path()
    # Path for match data.
    match_path = Path(data_path, 'subreddit_GARD_matches.csv')
    # Loads the .csv match data file.
    df = pd.read_csv(match_path)
    # Sorts the subreddits by size; smallest to largest number of subscribers.
    df = df.sort_values(by=['subscribers'], ascending=True)

    # Sets the subreddit_list to the data from the .csv file.
    subreddit_list = list(df['r/'])
    # Appends FND to list.
    subreddit_list.append('FND')
    # Reinitializes dataframe to None.
    df = None
    print(f'Total Number of Subreddit Matches: {len(subreddit_list)}')

    # Finds the data path for the posts data.
    post_path = utils.get_data_path('posts')
    # Scans the files in the comments folder for completed subreddit json files.
    completed_list = [file.name for file in Path(post_path).rglob('*.json')]
    # Gets only the subreddit name from completed json files.
    completed_list = [subreddit.split('_posts.json')[0] for subreddit in completed_list]
    # Prunes the completed subreddits from the subreddit list.
    subreddit_list = [subreddit for subreddit in subreddit_list if subreddit not in completed_list]

    # Total number of subreddits.
    total = len(subreddit_list)
    # Count of subreddits completed.
    count = 1
    # Iterates over subreddit list and retrieves the posts.
    for subreddit in subreddit_list:
        # Calls th class and retrieves the post data. Writes the data to a json file.
        GetPosts(name=subreddit, silence=False)
        print(f'Subreddit {subreddit}: {count} out of {total} completed.\n')
        count += 1

if __name__ == '__main__':
    main()
