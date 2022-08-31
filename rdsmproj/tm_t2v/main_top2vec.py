#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script for generating Top2Vec models.
"""

from pathlib import Path
from typing import Optional, Union
from gensim.models.phrases import ENGLISH_CONNECTOR_WORDS
from rdsmproj import utils
from rdsmproj import preprocess as pp
from rdsmproj.tm_t2v.top2vec_model import Top2VecModel
import rdsmproj.tm_t2v.top2vec_topic_tools as ttt


def model_gen(name:str,
              path:Optional[Union[str, Path]] = None,
              preprocess_args:Optional[dict] = None,
              topic_tools:Optional[bool] = True):
    """
    model_gen generates top2vec models for use in the extended paper.
    *<insert link to paper once published>*

    Parameters
    ----------
    name: str
        Name of subreddit.
    path: str,Path (Optional, default data/models/name)
        Path for location of models to be written to.
    preprocess_args: dict (Optional)
        Arguments to pass to preprocess.
    topic_tools: bool (Optional, default True)
        Defines whether to automatically run the analysis script after generating model.
    """

    if preprocess_args:
        data = pp.PreProcess(name, **preprocess_args)
    else:
        data = pp.PreProcess(name)

    if not path:
        path = Path.cwd()
        data_path = Path(f'{path}', 'data', 'models', name)
    else:
        data_path = path

    utils.check_folder(data_path)
    documents, tokenized_documents, id2word, corpus = data()

    print(f'Number of documents: {len(documents)}')

    embedding_models = ['universal-sentence-encoder','universal-sentence-encoder-multilingual',
                        'distiluse-base-multilingual-cased','all-MiniLM-L6-v2',
                        'paraphrase-multilingual-MiniLM-L12-v2', 'doc2vec']

    ngram_vocab_args = {'connector_words':ENGLISH_CONNECTOR_WORDS,
                        'min_count': 5,
                        'threshold': 10.0}

    for embedding_model in embedding_models:

        if embedding_model == 'doc2vec':
            for cluster_selection_method in ['leaf', 'eom']:
                hdbscan_args = {'min_cluster_size': 15,
                                'metric': 'euclidean',
                                'cluster_selection_method': cluster_selection_method}
                for i in range(5):
                    fname = f'{name}_{embedding_model}_{cluster_selection_method}_{i}'
                    model_path = Path(data_path,fname)
                    if not model_path.exists():
                        model = Top2VecModel(name,
                                            fname,
                                            documents,
                                            embedding_model,
                                            data_path,
                                            speed='deep-learn',
                                            ngram_vocab=True,
                                            ngram_vocab_args=ngram_vocab_args,
                                            hdbscan_args=hdbscan_args).fit()

                        if topic_tools and model:
                            ttt.AnalyzeTopics(model=model,
                                            model_name=fname,
                                            subreddit_name=name,
                                            tokenized_docs=tokenized_documents,
                                            id2word=id2word,
                                            corpus=corpus,
                                            model_type='Top2Vec')
        else:
            model_path = Path(data_path, f'{name}_{embedding_model}')
            if not model_path.exists():
                model = Top2VecModel(name,
                                     f'{name}_{embedding_model}',
                                     documents,
                                     embedding_model,
                                     data_path,
                                     speed='deep-learn',
                                     ngram_vocab=True,
                                     ngram_vocab_args=ngram_vocab_args).fit()
                if topic_tools and model:
                    ttt.AnalyzeTopics(model=model,
                                     model_name=f'{name}_{embedding_model}',
                                     subreddit_name=name,
                                     tokenized_docs=tokenized_documents,
                                     id2word=id2word,
                                     corpus=corpus,
                                     model_type='Top2Vec')

def main():
    """
    Auto-magically creates the top2vec models for subreddit data.
    """

    # Finds the data path for the comments data to be written to.
    comment_path = utils.get_data_path('comments')
    # Scans the files in the comments folder for completed subreddit json files.
    subreddit_list = [file.name for file in Path(comment_path).rglob('*.json')
                      if 'temp' not in file.name]
    # Removes comments from list of names.
    subreddit_list = [file.replace('_comments.json', '') for file in subreddit_list]

    remove_list = ['LearningDisabilities', 'Blind','trollingforababy','achalasia','Strabismus',
               'DisabilityFitness','neurology','dyscalculia','ADPKD','Staphacne','Menieres',
               'hearing', 'glutenfree','vulvodynia','dysgraphia','nsclc','fuckmosquitoes',
               'dementia','endocrinology', 'Dissociation','audiology','primaryimmune',
               'IBD','Anger', 'leukemia', 'mito', 'crazyitch','Ophthalmology','poliosis',
               'DupuytrenDisease','Pandemic','disability']

    subreddit_list = [entry for entry in subreddit_list if entry not in remove_list]

    print(f'Number of subreddits: {len(subreddit_list)}')

    for subreddit in subreddit_list:
        print(f'\n*** Creating models for: {subreddit}\n')
        model_gen(name=subreddit)

if __name__ == '__main__':
    main()
