#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Decompresses and reads in the subreddit file from https://files.pushshift.io/reddit/subreddits/
and then saves the file.
"""

import json
import re
from typing import Union
from pathlib import Path
from tqdm import tqdm
import pandas as pd
from rdsmproj.sm_reddit.zreader import Zreader as zreader
from rdsmproj import utils


def create_dataframe(subreddit_dict:dict) -> pd.DataFrame:
    """
    Takes the subreddit dictionary and converts it into a pandas DataFrame.

    :param subreddit_dict: Dictionary of results.

    :return: pandas DataFrame of results.
    """

    subreddit_df = pd.DataFrame(list(subreddit_dict.values()))
    subreddit_df['new'] = subreddit_dict.keys()
    subreddit_df.columns = ['title', 'description', 'subscribers', 'created_utc',
                            'public_description','name']
    return subreddit_df

class ConvertSubreddit:
    """
    A class to read in the subreddit file (reddit_subreddits.ndjson.zst found at above web address)
    and save it as either a parquet or csv.

    :param path: Path for storing the file of subreddit data.
    """

    def __init__(self, path:Union[str, Path, None] = None):
        # If no path is given, uses default data path.
        if path is None:
            path = utils.find_data_path()
        self.path = path
        # Checks if folder for data path exists, creates if it does not.
        utils.check_folder(self.path)
        # Creates pandas DataFrame from reading in data file.
        self._read_data()

        # Processes data.
        self._preprocess_data()
        self.df = create_dataframe(self.subreddit_dict)

        # Writes pandas DataFrame to .csv file.
        self.df.to_csv(Path(self.path,'primary_subreddit_list.csv'), index=False)

    def _read_data(self) -> None:
        """
        From Eric:
        ndjson has to be read one line at a time. so I chose to store the information we want from
        the file into a dictionary which will in turn be transformed into a dataframe.

        To create a smaller/more relevant subset of data I only grabbed subreddits that were in the
        English language and Public (as opposed to private).

        This file contained many attributes for each row, I examined all the attributes and decided
        which ones would be useful and should be taken and included in the final dataframe.

        :return: Dictionary of result including title, description, subscribers, and created_utc.
        """
        print('Reading in Reddit subreddit data...')
        # Reads compressed NDJSON .zst file using zreader.
        reader = zreader(Path(self.path,'reddit_subreddits.ndjson.zst'))
        # Finds total length of file.
        total = sum(1 for line in reader.readlines())
        # Initializes dictionary.
        self.subreddit_dict = {}
        # Re-initializes the generator.
        reader = zreader(Path(self.path,'reddit_subreddits.ndjson.zst'))

        # Read each line from the reader.
        for line in tqdm(iterable = reader.readlines(), total = total, desc='Reading in data.'):
            # Loads the json line.
            obj = json.loads(line)
            # Checks for public subreddit and English language.
            # Possibly open up to check other languages and translate to English?
            if (obj['subreddit_type'] == 'public') and (obj['lang']== 'en'):
                # Creates dictionary entries for title, description, subscribers and creation time.
                # These were the attributes chosen by Eric. Are these sufficient?
                self.subreddit_dict[obj['display_name']] = [obj['title'],
                                                    obj['description'],
                                                    obj['subscribers'],
                                                    obj['created_utc'],
                                                    obj['public_description']]

        # Other possible attributes available from the file are as follows:

        # ['accounts_active', 'accounts_active_is_fuzzed', 'active_user_count',
        # 'advertiser_category', 'all_original_content', 'allow_chat_post_creation',
        # 'allow_discovery', 'allow_galleries', 'allow_images', 'allow_polls', 'allow_videogifs',
        # 'allow_videos', 'banner_background_color', 'banner_background_image', 'banner_img',
        # 'banner_size', 'can_assign_link_flair', 'can_assign_user_flair',
        # 'collapse_deleted_comments', 'comment_score_hide_mins', 'community_icon', 'created_utc',
        # 'description', 'description_html', 'disable_contributor_requests', 'display_name',
        # 'display_name_prefixed', 'emojis_custom_size', 'emojis_enabled', 'free_form_reports',
        # 'has_menu_widget', 'header_img', 'header_size', 'header_title', 'hide_ads', 'icon_img',
        # 'icon_size', 'id', 'is_chat_post_feature_enabled', 'is_crosspostable_subreddit',
        # 'is_enrolled_in_new_modmail', 'key_color', 'lang', 'link_flair_enabled',
        # 'link_flair_position', 'mobile_banner_image', 'name', 'notification_level',
        # 'original_content_tag_enabled', 'over18', 'primary_color', 'public_description',
        # 'public_description_html', 'public_traffic', 'quarantine', 'restrict_commenting',
        # 'restrict_posting', 'retrieved_utc', 'show_media', 'show_media_preview',
        # 'spoilers_enabled', 'submission_type', 'submit_link_label', 'submit_text',
        # 'submit_text_html', 'submit_text_label', 'subreddit_type', 'subscribers',
        # 'suggested_comment_sort', 'title', 'url', 'user_can_flair_in_sr',
        # 'user_flair_background_color', 'user_flair_css_class', 'user_flair_enabled_in_sr',
        # 'user_flair_position', 'user_flair_richtext', 'user_flair_template_id', 'user_flair_text',
        # 'user_flair_text_color', 'user_flair_type', 'user_has_favorited', 'user_is_banned',
        # 'user_is_contributor', 'user_is_moderator', 'user_is_muted', 'user_is_subscriber',
        # 'user_sr_flair_enabled', 'user_sr_theme_enabled', 'videostream_links_count',
        # 'whitelist_status', 'wiki_enabled', 'wls']

    def _preprocess_data(self) -> None:
        """
        Preprocesses reddit data for use in spaCy Python scripts.
        It will be a list of tuples (doc, context) of the form of:

        data = [('description text', {'name': display_name, 'title': title,
                                    'subscribers':subscribers,
                                    'created_utc': created_utc}),
                ('description text', {'name': display_name, 'title': title,
                                    'subscribers':subscribers,
                                    'created_utc': created_utc}),...]

        Finally, it writes the preprocessed data to a JSON file.
        """
        # Initializes data -> Tuple[str,dict].
        data = []
        # Finds length of dictionary to preprocess.
        total = len(self.subreddit_dict)
        # Preprocesses dictionary of subreddits and converts to correct data format.
        for key, values in tqdm(iterable=self.subreddit_dict.items(),
                                total=total, desc='Preprocessing data'):
            # Concatenates the title, description, and public description into one text string.
            description = [values[0], values[1], values[4]]
            description = [text for text in description if text]
            description = '. '.join(description)
            if description:
                # Issues with encoding/decoding. Partial fix.
                description = description.encode('ISO-8859-1').decode('latin1').encode('utf-8').decode('utf-8')
                # Removing brackets [], parentheses (), and slashes /.
                description = re.sub("[(\[\])/]", ' ', description)
                # Brute force fix for apostrophe's that snuck through as â\x80\x99 instead.
                description = re.sub(r'â\x80\x99', "'", description)
                data.append((description, {'name': key,
                                           'title': values[0],
                                           'subscribers': values[2],
                                           'created_utc': values[3]}))

        # Writes the processed data to a JSON file.
        utils.dump_json(data,self.path,'preprocessed_subreddit_list')

def main():
    """
    Calls class with default values and converts subreddit archive to .csv
    """
    ConvertSubreddit()

if __name__ == '__main__':
    main()
