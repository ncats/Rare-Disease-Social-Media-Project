#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Get comment data from subreddit posts.
"""
import logging
from pathlib import Path
from typing import Union, Optional
from pmaw import PushshiftAPI
from tqdm import tqdm
from rdsmproj import utils


# Sets the PushshiftAPI to ignore shards_down messages.
api = PushshiftAPI(shards_down_behavior=None)

class GetRedditComments:
    """
    Class to retrieve comments from the posts contained in a subreddit.

    Parameters
    ----------
    data: list[dict]
        JSON data from get_posts.py that is a list of dictionaries, with one dictionary
        for each post.
    data_path: str, Path (Optional, default None)
        Path for data to be written to. Default is to a comments folder in data folder.
    silence: bool (Optional, default True)
        Silences the PushshiftAPI logger.
    pmaw_args: dict (Optional, default None)
        Pass arguments to pmaw api.search_submission_comment_ids.
    """
    def __init__(self, data:list[dict] = None,
                 data_path:Union[str, Path] = None,
                 missing_list:Optional[list[dict]] = None,
                 silence:bool=True,
                 pmaw_args:dict=None) -> None:

        # Uses given path or default if none provided.
        if data_path:
            self.path = data_path
        else:
            self.path = utils.get_data_path('comments')

        # Initializes data.
        self.data = data
        self.num_comments = 0

        # Sets name of subreddit.
        self.name = self.data[0]['subreddit']
        # Checks if a temp file is present and replaces data with temp file.
        self._check_tempfile()

        # If silence is True, then it will silence the PushshiftAPI logger. Default is True.
        if silence:
            # Silences the PushshiftAPI logger.
            logger = logging.getLogger('pmaw')
            logger.setLevel(logging.WARNING)

        # Checks for missing_list. In further versions, will contain an update method to retrieve
        # comments from a given missing_list.
        if missing_list is None:
            # Sets missing comment list to empty list.
            self.missing_list = []
        
        # Passes optional arguments if pmaw_args is given.
        if pmaw_args:
            self.pmaw_args = pmaw_args
        else:
            self.pmaw_args = None

        # Gets the comment data. Updates the self.data with comments.
        self._get_comments()

        # Saves the new data updated with the comment data to self.path.
        utils.dump_json(self.data, path = self.path, filename=f'{self.name}_comments')

        # If there were errors, saves the list of posts with errors.
        if self.missing_list:
            print(f'Saving {len(self.missing_list)} post ids with errors for {self.name}')
            utils.dump_json(self.missing_list,Path(data_path,'missing'),f"{self.name}_missing_list")

    def _get_comments(self) -> None:
        """
        Retrieves the comments from the list of reddit posts provided in self.data that do not
        have 'all_text' as a key for updating from temporary files.
        """

        # Count of posts with comment data retrieved.
        count = 0
        # Count of posts parsed whether data retrieved or not.
        posts = 0
        # Total number of posts in self.data.
        total = len(self.data)

        # Iterates over posts in self.data and creates the progress bar.
        for submission in tqdm(iterable = self.data, total = total, desc=f'{self.name}'):
            # Checks if 'all_text' is a key for the submission.
            if 'parsed' not in submission:
                try:
                    # Tries to query PushShift for the comment list of a given post.
                    comment_id_list = list(api.search_submission_comment_ids(ids=submission['id'],
                                                                             **self.pmaw_args))
                    # If comment list exists, tries to retrieve comments.
                    if comment_id_list:
                        try:
                            # Retrieves comments from list of ids.
                            comments = list(api.search_comments(ids=comment_id_list))
                            # Retrieves body text from each comment.
                            text = [comment['body'] for comment in comments]
                            # Adds number of comments found to comment total.
                            self.num_comments += len(text)
                            # Concatenates the comment text list into one string.
                            text = ' '.join(text)
                            # Gets post title.
                            title = submission['title']
                            # Gets post text.
                            if 'selftext' in submission:
                                selftext = submission['selftext']
                            else:
                                selftext = ''
                            # Saves the title, post text, and comment text to 'all_text'
                            submission['all_text'] = f"{title} {selftext} {text}"
                            # Updates count of posts with comment data retrieved.
                            count+=1

                        # If error in retrieving comments, append post id to missing list.
                        except UserWarning:
                            self.missing_list.append(submission['id'])

                # If error in querying PushShift for the comment list,
                # append post id to missing list.
                except UserWarning:
                    self.missing_list.append(submission['id'])

                posts += 1
                submission['parsed'] = True
                # Every 100 posts parsed it will write a temporary file to be used in case of
                # interrupted downloads.
                if posts % 100 == 0:
                    utils.dump_json(self.data,
                                    path = self.path,
                                    filename = f'{self.name}_temp')
                    utils.dump_json(self.num_comments,
                                    path=self.path,
                                    filename = f'{self.name}_count')

        # Removes the temporary file if it exists.
        self._remove_tempfile()
        # Writes the final number of comments retrieved.
        utils.dump_json(self.num_comments, path=self.path, filename = f'{self.name}_count')

    def _check_tempfile(self) -> None:
        """
        Checks if the temporary file exists. If it does, then it replaces self.data with the data
        found in the temporary file.
        """
        # Sets the temporary file path to path/subreddit_temp.json.
        temporary_file = Path(self.path, f'{self.name}_temp.json')
        comment_count = Path(self.path, f'{self.name}_count.json')
        # Checks if temporary file exists. Loads data if it does exist.
        if temporary_file.is_file():
            print(f'Using temporary file for {self.name}.')
            self.data = utils.load_json(temporary_file)

        if comment_count.is_file():
            self.num_comments = utils.load_json(comment_count)

    def _remove_tempfile(self) -> None:
        """
        Checks if the temporary file exists. If it does, then it removes the temporary file.
        """
        # Sets the temporary file path to path/subreddit_temp.json.
        temporary_file = Path(self.path, f'{self.name}_temp.json')
        # Checks if temporary file exists. Removes the file if it does.
        if temporary_file.is_file():
            temporary_file.unlink()

def main():
    """
    Auto-magically gets all the comment data for subreddits with > 10 posts and < 50000.
    """

    # Finds the data path for the posts data.
    path = utils.get_data_path('posts')
    # Finds the data path for the comments data to be written to.
    comment_path = utils.get_data_path('comments')
    # Scans the files in the comments folder for completed subreddit json files.
    comments_list = [file.name for file in Path(comment_path).rglob('*.json')]
    # Replaces comments with posts in filename to make it easier to compare lists.
    comments_list = [file.replace('comments', 'posts') for file in comments_list]

    # Creates path for post data file.
    post_data_path = Path(path, 'post_data.json')
    # Loads post data file.
    post_data = utils.load_json(post_data_path)
    # Sorts the post data in reverse order by size.
    post_data = {subreddit:posts for subreddit, posts in
                 sorted(post_data.items(), key=lambda item: item[1])}
    # Creates list of subreddits from post_data that are between 100 and 100000 posts.
    subreddit_list = [f'{subreddit}_posts.json' for subreddit, posts in post_data.items()
                      if (posts >= 100 and posts < 100000)]
    # Prunes the subreddit list if the subreddit is already in the comments folder.
    subreddit_list = [subreddit for subreddit in subreddit_list if subreddit not in comments_list]

    # Total number of subreddits.
    total = len(subreddit_list)
    # Count of subreddits completed.
    count = 1
    print(subreddit_list)
    # Iterates over all subreddits in the list.
    for subreddit in subreddit_list:
        print(subreddit)
        if subreddit not in ['tinnitus_posts.json',
                             'Snus_posts.json',
                             'Fibromyalgia_posts.json',
                             'optometry_posts.json',
                             'ChronicPain_posts.json',
                             'cancer_posts.json']:
            # Loads the subreddit data.
            data = utils.load_json(Path(path,subreddit))
            # Gets name of subreddit.
            name = data[0]['subreddit']
            # Calls the class and retrieves the comment data. Writes the data to a json file.
            GetRedditComments(data)
            # Reinitializes data to None.
            data = None
            print(f'Subreddit {name}: {count} out of {total} completed.\n')
            count += 1

if __name__ == '__main__':
    main()
