#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Legacy script for running optimization of LDA models and generating Top2Vec models.
Used for paper:
    Karas, B., Qu, C., Xu, Y. and Zhu, Q., Experiments with LDA and Top2Vec for Embedded Topic
    Discovery on Social Media Data-A Case Study of Cystic Fibrosis. Frontiers in Artificial
    Intelligence, p.183. https://doi.org/10.3389/frai.2022.948313
"""
from pathlib import Path
from typing import Optional, Union
import optuna
from hyperopt import hp, tpe, Trials, fmin, atpe, rand
from gensim.models.phrases import ENGLISH_CONNECTOR_WORDS
from rdsmproj.tm_lda import lda_model as lm
from rdsmproj import preprocess as pp
from rdsmproj import utils
from rdsmproj.tm_t2v.top2vec_model import Top2VecModel


def lda_optuna(tokenized_documents,
               id2word,
               corpus,
               name,
               data_path,
               n_trials,
               coherence,
               sampler):
    """
    Function for optimizing LDA models using optuna.
    """
    study = optuna.create_study(direction='maximize', sampler=sampler)
    study.optimize(lm.OptunaObj(tokenized_documents,id2word, corpus, name, data_path, coherence),
                                n_trials=n_trials)

def lda_hyperopt(tokenized_documents,
                 id2word,
                 corpus,
                 name,
                 data_path,
                 n_trials,
                 coherence,
                 algo):
    """
    Function for optimizing LDA models using hyperopt.
    """

    # These variables were in other tests not part of the published paper.
    chunksize = [2**exponent for exponent in range(1, 15, 1)]
    decay = [0.5, 0.6, 0.7, 0.8, 0.9]
    offset = [2**exponent for exponent in range(11)]
    iterations = [2**exponent for exponent in range(5, 13, 1)]
    '''
    space = {'num_topics': hp.quniform('num_topics', 3, 100, 1),
             'passes': hp.quniform('passes', 1, 100, 1),
             'chunksize':hp.choice('chunksize', chunksize),
             'decay':hp.choice('decay', decay),
             'offset':hp.choice('offset', offset),
             'iterations':hp.choice('iterations', iterations)}
    '''
    space = {'num_topics': hp.quniform('num_topics', 5, 100, 1),
            'alpha' : hp.choice('alpha',
                                [.01, .05, .1, .2, .5, 1, 'asymmetric', 'symmetric', 'auto'])
                                }

    trials = Trials()
    count = 0
    fmin(lm.HyperoptObj(tokenized_documents,
                        id2word,
                        corpus,
                        name,
                        data_path,
                        count,
                        coherence),
         space=space, algo=algo, max_evals=n_trials, trials=trials)
    #dump_json(trials.results(), data_path, name)

def model_gen(name:str,
              coherence:str,
              n_trials:int,
              path:Optional[Union[str, Path]] = None,
              preprocess_args:Optional[dict] = None,
              optuna_tpe:Optional[bool] = False,
              optuna_rand:Optional[bool] = False,
              hyperopt_tpe:Optional[bool] = False,
              hyperopt_atpe:Optional[bool] = False,
              hyperopt_rand:Optional[bool] = False,
              top2vec:Optional[bool] = True):
    """
    Function for creating optimized LDA models with hyperopt and optuna as well as top2vec.
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
    if optuna_tpe:
        print(f'LDA Optuna TPE Optimization for {name} num trials: {n_trials}')
        lda_optuna(tokenized_documents, id2word, corpus, f'{name}_optuna_tpe_{coherence}',
                   data_path, n_trials, coherence, sampler = optuna.samplers.TPESampler())
    if optuna_rand:
        print(f'LDA Optuna TPE Optimization for {name} num trials: {n_trials}')
        lda_optuna(tokenized_documents, id2word, corpus, f'{name}_optuna_rand_{coherence}',
                   data_path, n_trials, coherence, sampler = optuna.samplers.RandomSampler())
    if hyperopt_atpe:
        print(f'LDA Hyperopt ATPE Optimization for {name} num trials: {n_trials}')
        lda_hyperopt(tokenized_documents, id2word, corpus, f'{name}_hp_atpe_alpha_{coherence}',
                     data_path, n_trials, coherence, atpe.suggest)
    if hyperopt_tpe:
        print(f'LDA Hyperopt TPE Optimization for {name} num trials: {n_trials}')
        lda_hyperopt(tokenized_documents, id2word, corpus, f'{name}_hp_tpe_{coherence}',
                     data_path, n_trials, coherence, tpe.suggest)
    if hyperopt_rand:
        print(f'LDA Hyperopt Random Optimization for {name} num trials: {n_trials}')
        lda_hyperopt(tokenized_documents, id2word, corpus, f'{name}_hp_rand_{coherence}',
                     data_path, n_trials, coherence, rand.suggest)
    if top2vec:
        embedding_models = ['universal-sentence-encoder','universal-sentence-encoder-multilingual',
                            'distiluse-base-multilingual-cased','all-MiniLM-L6-v2',
                            'paraphrase-multilingual-MiniLM-L12-v2', 'doc2vec']

        ngram_vocab_args = {'connector_words':ENGLISH_CONNECTOR_WORDS}

        for embedding_model in embedding_models:
            Top2VecModel(name, f'CysticFibrosis_{embedding_model}', documents,
                         embedding_model, data_path, speed='deep-learn',
                         ngram_vocab=True, ngram_vocab_args=ngram_vocab_args).fit()

def main():
    """
    Calls model_gen for CysticFibrosis as an example of use with model_gen on the subreddit data.
    """
    name = 'CysticFibrosis'
    coherence = 'c_v'
    n_trials = 200

    model_gen(name, coherence, n_trials,
              optuna_tpe=False,
              optuna_rand=False,
              hyperopt_atpe=False,
              hyperopt_tpe=False,
              hyperopt_rand=True,
              top2vec=False)

if __name__ == '__main__':
    main()
