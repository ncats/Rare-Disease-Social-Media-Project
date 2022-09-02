<img src = "https://ncats.nih.gov/sites/all/themes/ncats-2014/images/assets/ncats-logo.png" align=right width="30%" height="30%">

# RDSMproj

RDSMproj (**R**are **D**iseases **S**ocial **M**edia **Proj**ect) for the [National Center for Advancing Translational Sciences](https://ncats.nih.gov/) at the [NIH](https://www.nih.gov/). This project looks at mining information from social media ([Reddit](https://www.reddit.com/)) and finding subreddits that are related to different rare diseases found in the [GARD](https://rarediseases.info.nih.gov/) database. The project matches rare diseases to Reddit subreddits, downloads the post and comment data, and then analyzes the text data to find the different topics that people are talking about.

## Overview

The project is split into four packages as part of rdsmproj:
1. [mapper](https://github.com/ncats/Rare-Disease-Social-Media-Project/tree/main/rdsmproj/mapper) is a python package that maps text to a rare disease(s) using [nltk](https://www.nltk.org/) and [spaCy](https://spacy.io/). An alternate name for this package is **NormMap V2**.
2. [sm_reddit](https://github.com/ncats/Rare-Disease-Social-Media-Project/tree/main/rdsmproj/sm_reddit) is a collection of scripts that utilizes [pmaw](https://github.com/mattpodolak/pmaw) to download Reddit post and comment text data for use in topic modeling or other text analyses.
3. [tm_t2v](https://github.com/ncats/Rare-Disease-Social-Media-Project/tree/main/rdsmproj/tm_t2v) is a python package that creates topic models of text using [Top2Vec](https://github.com/ddangelov/Top2Vec).
4. [tm_lda](https://github.com/ncats/Rare-Disease-Social-Media-Project/tree/main/rdsmproj/tm_lda) is a (**legacy**) python package that creates topic models of text primarily using LDA as implemented by [Gensim](https://radimrehurek.com/gensim/). This package was used in this [paper](https://doi.org/10.3389/frai.2022.948313).

## Installation
Ensure that you have up to date copies of `pip`, `setuptools`, and `wheel` prior to installation.
```bash
pip install --upgrade pip setuptools wheel
```


For now, each package above is installed separately.
```bash
pip install rdsmproj[mapper]
pip install rdsmproj[sm_reddit]
pip install rdsmproj[tm_t2v]
pip install rdsmproj[tm_tlda]
```

## Quick Start
### *For more information view the API guide.*
### Examples using sm_reddit

#### `sm_reddit.GetPosts`
```python
from rdsmproj import sm_reddit

pmaw_args = {'limit':1000}
# Example subreddit 'MachineLearning'.
# Passes pmaw arguments to search_submissions.
sm_reddit.GetPosts(name='MachineLearning', silence=False, pmaw_args=pmaw_args)
```

#### `sm_reddit.GetRedditComments`
```python
from rdsmproj import utils
from pathlib import Path

# Default path to where the post data is located.
path = utils.get_data_path('posts')
data = utils.load_json(Path(path,'MachineLearning_posts.json'))
# Example passes pmaw arguments to search_submission_comment_ids.
sm_reddit.GetRedditComments(data=data, silence=False, pmaw_args=pmaw_args)
```

### Example using preprocess to process text data.
#### `preprocess.Preprocess`
```python
from rdsmproj import preprocess as pp

# Example processes the comment data for use with tm_lda or tm_t2v.
data = pp.PreProcess(name='MachineLearning')
documents, tokenized_documents, id2word, corpus = data()
```

### Example using tm_t2v to create and analyze a top2vec model.
#### `tm_t2v.Top2VecModel`
```python
from rdsmproj import tm_t2v

embedding_model = 'doc2vec'
name = 'MachineLearning'
clustering_method = 'leaf'
i = 0

# Creates and saves a model.
model = tm_t2v.Top2VecModel(name,
                            f'{name}_{embedding_model}_{clustering_method}_{i}',documents=documents,
                            embedding_model=embedding_model,
                            speed='fast-learn'
                            ).fit()
```

#### `tm_t2v.AnalyzeTopics`
```python
# Analyzes model and records the results.
tm_t2v.AnalyzeTopics(model=model,
                     model_name=f'{name}_{embedding_model}_{clustering_method}_{i}',
                     subreddit_name=name,
                     tokenized_docs=tokenized_documents,
                     id2word=id2word,
                     corpus=corpus,
                     model_type='Top2Vec')
```

## To Do
- [x] Test package install from TestPyPI.
- [x] Update main README.md Quick Start with examples for most packages.
- [ ] Create [sm_reddit](https://github.com/ncats/Rare-Disease-Social-Media-Project/tree/main/rdsmproj/sm_reddit) README.md.
- [ ] Create [tm_t2v](https://github.com/ncats/Rare-Disease-Social-Media-Project/tree/main/rdsmproj/tm_t2v) README.md.
- [ ] Create [tm_lda](https://github.com/ncats/Rare-Disease-Social-Media-Project/tree/main/rdsmproj/tm_lda) README.md.
- [ ] Create API guide and documentation pages.
- [ ] Add visualizations and flowcharts to the readme files.
- [ ] Upload to PyPI.
