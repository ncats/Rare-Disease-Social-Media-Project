#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Legacy script for creating LDA models.

Classes and functions to support LDA model generation and optimization. This module relies heavily
on gensim (https://github.com/RaRe-Technologies/gensim) to create LDA models. As such, the
documentation from that package is used to describe the different parameters that are passed on to
gensim.
"""
from pathlib import Path
from typing import Union, Optional
import time
import logging

from gensim.models.ldamodel import LdaModel
from gensim.test.utils import datapath
from gensim.corpora.dictionary import Dictionary
import psutil
from hyperopt import STATUS_OK
from rdsmproj import utils
from rdsmproj.tm_lda import topic_tools as tt


#logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.WARNING)
logger = logging.getLogger('gensim')
logger.setLevel(logging.WARNING)


class OptunaObj:
    """
    Optuna objective function for use in optimization of LDA hyperparameters.

    Parameters
    ----------
    tokenized_documents: list[list[str]]
        List of lists of strings where each string corresponds to a token or word.

    id2word: gensim.corpora.dictionary.Dictionary
        Mapping of word ids to words.

    corpus: list[tuple[int, int]]
        Document vectors made up of list of tuples with (word_id, word_frequency)

    name: str
        Name of model.

    path: str, Path
        Path to store the model files to.

    coherence: str (default 'c_v')
        Currently through gensim supports following coherence measures: 'u_mass', 'c_v', 'c_uci',
        and 'c_npmi. Coherence measure 'c_uci = 'c_pmi'.


    Returns
    -------
    results: float
        Returns the coherence score used to optimize the LDA topic model generation using the
        Optuna package.
    """
    def __init__(self,
                 documents:list[str],
                 id2word:Dictionary,
                 corpus:list[tuple[int, int]],
                 name:str,
                 path:Union[str, Path],
                 coherence:str='c_v'):
        # documents to be passed on to LDAGen.
        self.documents = documents
        self.id2word = id2word
        self.corpus = corpus
        self.name = name
        self.path = path
        self.coherence = coherence

    def __call__(self, trial):
        # Objective function for optuna package.
        num_topics = trial.suggest_int('num_topics', 3, 100)
        passes = trial.suggest_int('passes', 1, 25)
        decay = trial.suggest_float('decay', 0.5, 0.9, step=0.1)
        initial = time.time()

        model = LDAGen(num_topics=num_topics, passes=passes).fit(id2word= self.id2word,
                                                                 corpus = self.corpus)

        post_dist = tt.find_distribution(model, self.documents, self.corpus)

        post_status = True
        for value in post_dist.values():
            if value < 1:
                post_status = False

        coherence_value = {}
        if not post_status:
            coherence_value = {'c_v': 1.0,
                               'c_npmi': 1.0,
                               'u_mass': 1.0,
                               'c_uci': 1.0}
        else:
            for coherence in ['c_v', 'c_npmi', 'u_mass', 'c_uci']:
                coherence_model = tt.create_coherence_model(model=model,
                                                        texts=self.documents,
                                                        id2word=self.id2word,
                                                        coherence=coherence)
                coherence_value[coherence] = coherence_model.get_coherence()




        temp_file = Path(self.path, f'{self.name}.json')
        results = {'c_v': coherence_value['c_v'],
                   'c_npmi':coherence_value['c_npmi'],
                   'u_mass':coherence_value['u_mass'],
                   'c_uci':coherence_value['c_uci'],
                   'eval_time': round(time.time() - initial, 1),
                   'num_topics': num_topics,
                   'passes': passes,
                   'decay':decay}

        if temp_file.is_file():
            temp_results = utils.load_json(temp_file)
            temp_results.append(results)

        else:
            temp_results = [results]

        fname = datapath(f'{self.path}/{self.name}_{trial.number}')
        model.save(fname)
        utils.dump_json(temp_results, self.path, f'{self.name}')

        return coherence_value[self.coherence]

class HyperoptObj:
    """
    Hyperopt objective function for use in optimization of LDA hyperparameters.

    Parameters
    ----------
    tokenized_documents: list[list[str]]
        List of lists of strings where each string corresponds to a token or word.

    id2word: gensim.corpora.dictionary.Dictionary
        Mapping of word ids to words.

    corpus: list[tuple[int, int]]
        Document vectors made up of list of tuples with (word_id, word_frequency)

    name: str
        Name of model.

    path: str, Path
        Path to store the model files to.

    count: int
        Count of trial used to index and name models.

    coherence: str (default 'c_v')
        Currently through gensim supports following coherence measures: 'u_mass', 'c_v', 'c_uci',
        and 'c_npmi. Coherence measure 'c_uci = 'c_pmi'.

    Returns
    -------
    results: list[dict]
        Lists of dictionaries of results of hyperparameter optimization including parameter
        values and loss (1-coherence).
    """

    def __init__(self,
                 tokenized_documents:list[list[str]],
                 id2word:Dictionary,
                 corpus:list[tuple[int, int]],
                 name:str,
                 path:Union[str, Path],
                 count:int,
                 coherence:str='c_v'):
        # documents to be passed on to LDAGen.
        self.documents = tokenized_documents
        self.id2word = id2word
        self.corpus = corpus
        self.name = name
        self.path = path
        self.count = count
        self.coherence = coherence

    def __call__(self, args):
         # Objective function for hyperopt package.
        initial = time.time()

        model = LDAGen(**args).fit(id2word= self.id2word,
                                   corpus = self.corpus)
        post_dist = tt.find_distribution(model, self.documents, self.corpus)
        post_dist = [num_docs for num_docs in post_dist.values()]
        max_post = max(post_dist)
        min_post = min(post_dist)
        zero_post = post_dist.count(0)
        coherence_value = {}
        coherence_model = tt.create_coherence_model(model=model,
                                                texts=self.documents,
                                                id2word=self.id2word,
                                                coherence=self.coherence)
        coherence = coherence_model.get_coherence()
        coherence_value[self.coherence] = coherence
        loss = 1 - coherence


        coherence_list = ['c_v', 'c_npmi', 'u_mass', 'c_uci']
        coherence_list.remove(self.coherence)


        for coherence in coherence_list:
            coherence_model = tt.create_coherence_model(model=model,
                                                    texts=self.documents,
                                                    id2word=self.id2word,
                                                    coherence=coherence)
            coherence_value[coherence] = coherence_model.get_coherence()


        temp_file = Path(self.path, f'{self.name}.json')
        '''
        Legacy results from prior lda_model optimization testing.

        results = {'loss': loss,
                   'c_v': coherence_value['c_v'],
                   'c_npmi':coherence_value['c_npmi'],
                   'u_mass':coherence_value['u_mass'],
                   'c_uci':coherence_value['c_uci'],
                   'max_post': max_post,
                   'min_post': min_post,
                   'zero_post': zero_post,
                   'status': STATUS_OK,
                   'eval_time': round(time.time() - initial, 1),
                   'num_topics': int(args['num_topics']),
                   'passes': int(args['passes']),
                   'chunksize':int(args['chunksize']),
                   'decay':float(args['decay']),
                   'offset':int(args['offset']),
                   'iterations':int(args['iterations']),
                   'count': self.count}
        '''
        results = {'loss': loss,
                   'c_v': coherence_value['c_v'],
                   'c_npmi':coherence_value['c_npmi'],
                   'u_mass':coherence_value['u_mass'],
                   'c_uci':coherence_value['c_uci'],
                   'max_post': max_post,
                   'min_post': min_post,
                   'zero_post': zero_post,
                   'status': STATUS_OK,
                   'eval_time': round(time.time() - initial, 1),
                   'num_topics': int(args['num_topics']),
                   'alpha': args['alpha'],
                   'count': self.count}

        if temp_file.is_file():
            temp_results = utils.load_json(temp_file)
            temp_results.append(results)
        else:
            temp_results = [results]

        fname = datapath(f'{self.path}/{self.name}_{self.count}')
        self.count += 1
        model.save(fname)
        utils.dump_json(temp_results, self.path, f'{self.name}')

        return results

class LDAGen:
    """
    Class to initialize a gensim.models.ldamulticore.LdaMulticore LDA model, and then train and fit
    the model using the initial parameters to generate a topic model representation of the text.

    Parameters
    ----------
    num_topics: int (default 10)
        Number of topics to be extracted from corpus.

    workers: int (Optional, default 1)
        Number of worker processes used for parallelization. If None, workers will be set to number
        of real cores - 1 for optimal performance.

    chunksize: int (Optional, default 4096)
        Number of documents to be used in each training chunk.

    passes: int (Optional, default 10)
        Number of passes through the corpus during training.

    alpha: float, np.ndarray of float, list[float], str (Optional, default 'asymmetric')
        A-priori belief on document-topic distribution. This can be:
        'symmetric': Uses fixed symmetric prior of 1.0 / num_topics.
        'asymmetric': Uses a fixed asymmetric prior of 1.0 / (topic_index + sqrt(num_topics)).
        scalar: symmetric prior over document-topic distribution.
        1-D array: Array of length = num_topics to denote an asymmetric user defined prior for
                   each topic.

    eta: float, np.ndarray of float, list[float], str (Optional, default 'symmetric')
        A-priori belief on topic-word distributiion. This can be:
        'symmetric': Uses a fixed symmetric prior of 1.0 / num_topics
        'auto': Learns an asymmetric prior from the corpus.
        scalar: symmetric prior over topic-word distribution.
        1-D array: Array of length = num_words to denote an asymmetric user defined prior for each
                   word.
        matrix: Matrix of shape (num_topics, num_words) to assign a probability for each word-topic
                combination.

    decay: float (Optional, default 0.5)
        Number between (0.5, 1] to weight what percentage of the previous lambda value is forgotten
        when each new document is examined. Corresponds to kappa from 'Online Learning for LDA'
        by Hoffman et al.

    offset: float (Optional, default 64)
        Hyper-parameter that controls how much we will slow down the first steps the first few
        iterations. Corresponds to tau_0 from 'Online Learning for LDA' by Hoffman et al.

    eval_every: int (Optional, default None)
        Log perplexity is estimated every that many updates. Setting this to one slows down
        training by ~2x.

    iterations: int (Optional, default 4096)
        Maximum number of iterations through the corpus when inferring the topic distribution of a
        corpus.

    gamma_threshold: float (Optional, default 0.001)
        Minimum change in the value of the gamma parameters to continue iterating.

    random_state: np.random.RandomState, int (Optional, default 84)
        Either a randomState object or a seed to generate one. Useful for reproducibility. Note
        that results can still vary due to non-determinism in OS scheduling of the worker
        processes.

    minimum_probability: float (Optional, default 0.01)
        Topics with a probability lower than this threshold will be filtered out.

    minimum_phi_value: float (Optional, default 0.01)
        If per_word_topics is True, then this represents a lower bound on the term probabilities.

    per_word_topics: bool (Optional, default True)
        If True, then the model also computes a list of topics, sorted in descending order of most
        likely topics for each word, along with their phi values multiplied by the feature length.
    """
    def __init__(self,
                 num_topics:Optional[int]=10,
                 workers:Optional[int]=1,
                 chunksize:Optional[int]=4096,
                 passes:Optional[int]=10,
                 alpha:Optional[Union[float, list[float], str]]='asymmetric',
                 eta:Optional[Union[float, list[float], str]]='symmetric',
                 decay:Optional[float]=0.5,
                 offset:Optional[float]=64,
                 eval_every:Optional[int]=None,
                 iterations:Optional[int]=4096,
                 gamma_threshold:Optional[float]=0.001,
                 random_state:Optional[int]=84,
                 minimum_probability:Optional[float]=0.01,
                 minimum_phi_value:Optional[float]=0.01,
                 per_word_topics:Optional[bool]=True,
                 ):

        # Sets the number of workers.
        if not workers:
            # Number of workers equal to 2 less than total physical number of cores.
            workers = psutil.cpu_count(logical=False) - 1

        # Initialize values for the gensim LDA topic model generation.
        self.num_topics = int(num_topics)
        self.workers = workers
        self.chunksize = chunksize
        self.passes = int(passes)
        self.alpha = alpha
        self.eta = eta
        self.decay = decay
        self.offset = offset
        self.eval_every = eval_every
        self.iterations = iterations
        self.gamma_threshold = gamma_threshold
        self.random_state = int(random_state)
        self.minimum_probability = minimum_probability
        self.minimum_phi_value = minimum_phi_value
        self.per_word_topics = per_word_topics

    def fit(self,
            id2word:Dictionary,
            corpus:list[tuple[int, int]]):
        """
        Trains the gensim.models.ldamulticore.LdaMulticore model with the initialized parameters on
        the training corpus given a training corpus and associated word ID to word mapping.

        Parameters
        ----------
        id2word: gensim.corpora.dictionary.Dictionary, dict[(int, str)]
            Mapping from word IDs to words. It is used to determine vocabulary size, as well as for
            debugging and topic printing.

        corpus: iterable of list[(int, float)], scipy.sparse.csc
            Stream of document vectors or sparse matrix of shape (num_documents, num_terms).

        Returns
        -------
        model:
            A trained gensim.models.ldamulticore.LdaMulticore model.
        """

        model = LdaModel(corpus=corpus,
                         num_topics = self.num_topics,
                         id2word=id2word,
                         chunksize=self.chunksize,
                         passes=self.passes,
                         alpha=self.alpha,
                         eta=self.eta,
                         decay=self.decay,
                         offset=self.offset,
                         eval_every=self.eval_every,
                         iterations=self.iterations,
                         gamma_threshold=self.gamma_threshold,
                         random_state=self.random_state,
                         minimum_probability=self.minimum_probability,
                         minimum_phi_value=self.minimum_phi_value,
                         per_word_topics=self.per_word_topics)

        return model
