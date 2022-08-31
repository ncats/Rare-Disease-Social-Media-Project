#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Top2Vec class for calling Top2Vec for use with topic generation. Saves the model to a file once the
model is finished generating. The file can then be loaded with Top2Vec.load('filename') for use
with the topic_tools script for analysis of topic generation results without having to retrain the
model.

Documentation for using Top2Vec was retrieved from the github repository at:
(https://github.com/ddangelov/Top2Vec)
"""
from pathlib import Path
from typing import Union, Optional
from top2vec import Top2Vec
import psutil
from rdsmproj import utils

class Top2VecModel:
    """
    name: str
        Name of the collection of documents for use in title and saving file
        (e.g. 'CysticFibrosis')

    model_name: str
        Name of the model for use in saving the model to a file in the directory
        associated with name and path. (e.g. 'CysticFibrosis_doc2vec')

    path: str, Path (Optional, default None)
        Path to store the model files to.

    documents: List of str
        Input corpus, should be a list of strings.

    min_count: int (Optional, default 50)
        Ignores all words with total frequency lower than this. For smaller
        corpora a smaller min_count will be necessary.

    ngram_vocab: bool (Optional, default False)
        Add phrases to topic descriptions.

        Uses gensim phrases to find common phrases in the corpus and adds them
        to the vocabulary.

        For more information visit:
        https://radimrehurek.com/gensim/models/phrases.html

    ngram_vocab_args: dict (Optional, default None)
        Pass custom arguments to gensim phrases.

        For more information visit:
        https://radimrehurek.com/gensim/models/phrases.html

    embedding_model: string or callable
        This will determine which model is used to generate the document and
        word embeddings. The valid string options are:

            * doc2vec
            * universal-sentence-encoder
            * universal-sentence-encoder-large
            * universal-sentence-encoder-multilingual
            * universal-sentence-encoder-multilingual-large
            * distiluse-base-multilingual-cased
            * all-MiniLM-L6-v2
            * paraphrase-multilingual-MiniLM-L12-v2

        For large data sets and data sets with very unique vocabulary doc2vec
        could produce better results. This will train a doc2vec model from
        scratch. This method is language agnostic. However multiple languages
        will not be aligned.

        Using the universal sentence encoder options will be much faster since
        those are pre-trained and efficient models. The universal sentence
        encoder options are suggested for smaller data sets. They are also
        good options for large data sets that are in English or in languages
        covered by the multilingual model. It is also suggested for data sets
        that are multilingual.

        For more information on universal-sentence-encoder options visit:
        https://tfhub.dev/google/collections/universal-sentence-encoder/1

        The SBERT pre-trained sentence transformer options are
        distiluse-base-multilingual-cased,
        paraphrase-multilingual-MiniLM-L12-v2, and all-MiniLM-L6-v2.

        The distiluse-base-multilingual-cased and
        paraphrase-multilingual-MiniLM-L12-v2 are suggested for multilingual
        datasets and languages that are not
        covered by the multilingual universal sentence encoder. The
        transformer is significantly slower than the universal sentence
        encoder options(except for the large options).

        For more information on SBERT options visit:
        https://www.sbert.net/docs/pretrained_models.html

        If passing a callable embedding_model note that it will not be saved
        when saving a top2vec model. After loading such a saved top2vec model
        the set_embedding_model method will need to be called and the same
        embedding_model callable used during training must be passed to it.

    speed: string (Optional, default 'learn')
        This parameter is only used when using doc2vec as embedding_model.
        It will determine how fast the model takes to train. The
        fast-learn option is the fastest and will generate the lowest quality
        vectors. The learn option will learn better quality vectors but take
        a longer time to train. The deep-learn option will learn the best
        quality vectors but will take significant time to train. The valid
        string speed options are:

            * fast-learn
            * learn
            * deep-learn

    workers: int (Optional)
        The amount of worker threads to be used in training the model. Larger
        amount will lead to faster training.

    umap_args: dict (Optional, default None)
        Pass custom arguments to UMAP.

    hdbscan_args: dict (Optional, default None)
        Pass custom arguments to HDBSCAN.

    top2vec_args: dict (Optional, default None)
        Pass custom arguments to Top2Vec
    """
    def __init__(self,
                 name:str,
                 model_name:str,
                 documents:list[str],
                 embedding_model,
                 path:Optional[Union[str,Path]]=None,
                 min_count:Optional[int] = 10,
                 speed: Optional[str] = 'learn',
                 workers:Optional[int]=None,
                 ngram_vocab:Optional[bool]=False,
                 ngram_vocab_args:Optional[dict]=None,
                 umap_args:Optional[dict]=None,
                 hdbscan_args:Optional[dict]=None,
                 top2vec_args:Optional[dict]=None,
                 ):

        self.name = name
        self.model_name = model_name
        self.documents = documents
        self.embedding_model = embedding_model
        self.min_count = min_count
        self.path = path
        self.speed = speed

        # Sets the number of workers.
        if not workers:
            # Number of workers equal to 1 less than total physical number of cores.
            self.workers = psutil.cpu_count(logical=False) - 1
            #print(f'Number of workers {workers}')
        else:
            self.workers = workers

        self.ngram_vocab = ngram_vocab
        self.ngram_vocab_args = ngram_vocab_args

        if not umap_args:
            self.umap_args = {'n_neighbors': 15,
                              'n_components': 5,
                              'metric': 'cosine',
                              'random_state':42}
        else:
            self.umap_args = umap_args

        if not hdbscan_args:
            self.hdbscan_args = {'min_cluster_size': 15,
                                 'metric': 'euclidean',
                                 'cluster_selection_method': 'eom'}
        else:
            self.hdbscan_args = hdbscan_args

        if not top2vec_args:
            self.top2vec_args = {'verbose':False}
        else:
            self.top2vec_args = top2vec_args

    def fit(self):
        """
        Trains the Top2Vec model using the parameters from initializing the class. Saves the
        Top2Vec model to a file for use later with analysis. Also saved for reproducibility as
        there is some randomness associated with subfunctions such that there can be some variance
        in the number and quality of topics each time that the model is ran even with the same
        initialized values and input data.

        Returns
        -------
        model:
            Top2Vec model.
        """
        try:
            model = Top2Vec(documents=self.documents,
                                embedding_model = self.embedding_model,
                                min_count=self.min_count,
                                speed=self.speed,
                                workers=self.workers,
                                ngram_vocab=self.ngram_vocab,
                                ngram_vocab_args=self.ngram_vocab_args,
                                umap_args=self.umap_args,
                                hdbscan_args=self.hdbscan_args,
                                **self.top2vec_args)

            # Sets the path to save the model to.
            if self.path is None:
                model_path = utils.get_data_path('models')
                file_path = Path(model_path, self.name)
                utils.check_folder(file_path)
                fname = Path(file_path, self.model_name)
            else:
                utils.check_folder(self.path)
                fname = Path(self.path, self.model_name)

            # Saves the model for later use.
            model.save(fname)
            return model
        except ValueError:
            pass
