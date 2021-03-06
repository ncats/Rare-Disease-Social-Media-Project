# NIHSocialMediaProject
Rare Diseases Social Media Project for NIH. This project looks at mining information from social media (Reddit) and finding subreddits that are related to different rare diseases found in the GARD database. The project matches rare diseases to Reddit subreddits, downloads the post and comment data, and then analyzes the text data to find the different topics that people are talking about.

The project is split into two parts. The first is matching the Reddit data to the GARD database and downloading the relevant information. The second part is analyzing the downloaded data to extract information about the topics being talked about for the identified subreddits.


TO DO:
- [ ] Update README.md
- [ ] Update setup.py
- [ ] Update query_gard.py
- [ ] Update convert_subreddit.py
- [ ] Update and generalize identify_subreddits.py
- [ ] Update get_post_data.py
- [ ] Update get_comment_data.py
- [ ] Finish Topic Modeling scripts


## Project Part 1 : Data Gathering and Classification
Scripts for gathering and processing data.
* `query_gard.py` : Retrieves GARD data. *Currently not working due to server being down.
* `convert_subreddit.py` : Converts Subreddit data into format for use with identify_subreddits.py
* `identify_subreddits.py` : Matches data to GARD data.
* `get_post_data.py` : Retrieves post data for matched subreddits.
* `get_comment_data.py` : Retrieves comment data for matched subreddits.

### Data files used.
* `reddit_subreddits.ndjson.zst` : Subreddit information from https://files.pushshift.io/reddit/subreddits/ retrieved Sept 23, 2021.

### Data files created.
* `neo4j_rare_disease_list.json` : Rare disease data from GARD database.
* `preprocessed_subreddit_list.json` : Processed reddit data for use in matching script.
* `primary_subreddit_list.csv` : Raw data uncompressed from reddit data file.
* `normalized_subreddit_matches.json` : Raw subreddit matches to GARD data.
* `subreddit_GARD_matches.json` : Filtered subreddit matches to GARD data with subreddits matched to rare diseases.
* `posts\*.json` : File for each subreddit with retrieved post data.
* `comments\*.json` : File for each subreddit with retrieved post data and comment data.

## Project Part 2 : Topic Modeling
Scripts for creating topic models
* `lda_model.py` : Uses gensim to create LDA topic models.
* `top2vec_model.py` : Uses Top2Vec to create topic models.