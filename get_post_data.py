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
from utils.utils import dump_json, get_data_path, load_json, find_data_path
import pandas as pd


# Sets the PushshiftAPI to ignore shards_down messages.
api = PushshiftAPI(shards_down_behavior=None)

class GetPosts:
    """
    Class to retrieve post data in a subreddit.
    """

    def __init__(self, name:str, path:Union[str,Path] = None,
                 after:Optional[int] = None, silence:bool=True):

        # Sets name of subreddit.
        self.name = name

        # If silence is True, then it will silence the PushshiftAPI logger. Default is True.
        if silence:
            # Silences the PushshiftAPI logger.
            logger = logging.getLogger('pmaw')
            logger.setLevel(logging.WARNING)

        # Checks if path is given. Uses a default if not provided.
        if path is None:
            self.path = get_data_path('posts')
        else:
            self.path = path

        # Sets the posts retrieved to 0 initially.
        self.post_num = 0

        # Checks if date for after is given. Uses default of 2010 if not given.
        if after:
            self.after = after
        else:
            self.after = int(dt.datetime(2010,1,1,0,0).timestamp())

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
                                                    after=self.after, metadata=True))
            # Checks if any posts were retrieved.
            if posts:
                # Sets the filename.
                filename = f'{self.name}_posts'
                # Dumps the retrieved data to a json file.
                dump_json(posts, self.path, filename)
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
            post_temp = load_json(post_file)

        # Adds subreddit and number of posts retrieved to the dictionary.
        post_temp[self.name] = self.post_num
        # Writes the post data dictionary to a json file.
        dump_json(post_temp, self.path, 'post_data')

def main():
    """
    Auto-magically gets the post data for subreddits that were matched to GARD data.
    """
    # Gets the data path.
    data_path = find_data_path()
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
    post_path = get_data_path('posts')
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
