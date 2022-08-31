#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Legacy script for analyzing LDA models.

A Class-based TF-IDF procedure using scikit-learns TfidfTransformer as a base. Originally written
by Maarten Grootendorst as part of BERTopic: https://github.com/MaartenGr/BERTopic from
_bertopic.py and _ctfidf.py. Adapted as standalone script to calculate c-TF-IDF.
"""

from typing import Union, Dict, Optional
from bertopic import _ctfidf
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from scipy.sparse.csr import csr_matrix
from rdsmproj.preprocess import tokenize_text

def _top_n_idx_sparse(matrix: csr_matrix, n: int) -> np.ndarray:
    """ Return indices of top n values in each row of a sparse matrix
    Retrieved from:
        https://github.com/MaartenGr/BERTopic/blob/master/bertopic/_bertopic.py
        https://stackoverflow.com/questions/49207275/finding-the-top-n-values-in-a-row-of-a-scipy-sparse-matrix
    Args:
        matrix: The sparse matrix from which to get the top n indices per row
        n: The number of highest values to extract from each row
    Returns:
        indices: The top n indices per row
    """
    indices = []
    for left, right in zip(matrix.indptr[:-1], matrix.indptr[1:]):
        n_row_pick = min(n, right - left)
        values = matrix.indices[left +
                                np.argpartition(matrix.data[left:right], -n_row_pick)[-n_row_pick:]]
        values = [values[index] if len(values) >= index + 1 else None for index in range(n)]
        indices.append(values)
    return np.array(indices)

def _top_n_values_sparse(matrix: csr_matrix, indices: np.ndarray) -> np.ndarray:
    """ Return the top n values for each row in a sparse matrix
    Retrieved from:
        https://github.com/MaartenGr/BERTopic/blob/master/bertopic/_bertopic.py
    Args:
        matrix: The sparse matrix from which to get the top n indices per row
        indices: The top n indices per row
    Returns:
        top_values: The top n scores per row
    """
    top_values = []
    for row, values in enumerate(indices):
        scores = np.array([matrix[row, value] if value is not None else 0 for value in values])
        top_values.append(scores)
    return np.array(top_values)


class CTFIDF:
    """
    Class to calculate the c-TF-IDF using BERTopic (https://github.com/MaartenGr/BERTopic)
    to extract the top n words in each class. c-TF-IDF is a TF-IDF formula adopted for multiple
    classes by joining all documents per class. Each class is then converted to a single
    document instead of a set of documents.

    c-TF-IDF_i = (t_i / w_i) x log (m / Sum from j to n(t_j))

    Frequency of words (t) are extracted for each class (i) and divided by total number of
    words (w). Next, the total, unjoined, number of documents across all classes (m) is
    divided by the total sum of word (j) across all classes.
    (https://github.com/MaartenGr/BERTopic/blob/master/bertopic/_ctfidf.py)

    Parameters
    ----------

    clustered_docs: list[str]
        List where each list is a single string made up of all the documents in that class
        (topic).

    topic_list: list[Union[int, str]]
        List of labels for the topics or classes.

    n: int
        Top n words to be extracted from each class (topic).
    """

    def __init__(self,
                 clustered_docs: list[str],
                 topic_list: list[Union[int, str]],
                 n:int=10):

        self.clustered_docs = clustered_docs
        self.labels = topic_list
        self.n = n

    def _extract_words_per_topic(self,
                                 ngram_range:Optional[tuple[int, int]] = (1,1)
                                 ) -> Dict[Union[int,str], list[tuple[str, float]]]:
        """
        Based on _extract_words_per_topic in _bertopic.py.
        Retrieved and adapted from:
            https://github.com/MaartenGr/BERTopic/blob/master/bertopic/_bertopic.py

        Extracts the top n words per topic based on c-TF-IDF matrix and its corresponding labels.

        Parameters
        ----------
        n_gram_range: int (Optional, default (1,1))
            N-gram range for CountVectorizer. Can create n-grams in the range of (a, b).

        Returns
        -------
        topics: Dict[Union[int,str], list[tuple[str, float]]]
            Dictionary where keys are labels from topic_list and values are lists of tuples of
            (word:str, score:float) for each label.
        """

        # Calculate the c-TF-IDF matrix from which to extract the top words.
        tokenizer = tokenize_text
        count = CountVectorizer(ngram_range=ngram_range,
                                stop_words="english",
                                tokenizer=tokenizer).fit(self.clustered_docs)
        count_transform = count.transform(self.clustered_docs)
        c_tf_idf = _ctfidf.ClassTFIDF().fit_transform(count_transform)
        words = count.get_feature_names_out()

        # Get the top n indices and values per row in a sparse c-TF-IDF matrix.
        indices = _top_n_idx_sparse(c_tf_idf, n=self.n)
        scores = _top_n_values_sparse(c_tf_idf, indices)
        sorted_indices = np.argsort(scores, 1)
        indices = np.take_along_axis(indices, sorted_indices, axis = 1)
        scores = np.take_along_axis(scores, sorted_indices, axis=1)

        # Get top n words per topic based on c-TF-IDF score.
        topics = {label: {words[word_index] if word_index and score > 0 else "":
                            score if word_index and score > 0 else 0.00001
                            for word_index, score in zip(indices[index][::-1], scores[index][::-1])
                        }
                    for index, label in enumerate(self.labels)}

        return topics
