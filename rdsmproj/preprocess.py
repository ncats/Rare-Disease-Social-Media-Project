#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Preprocessing functions for topic generation files needed for topic modeling algorithms.
"""

from pathlib import Path
from typing import Any, Union, Optional
import re
from tqdm import tqdm
from gensim.corpora.dictionary import Dictionary
from gensim.models.phrases import Phrases, Phraser, ENGLISH_CONNECTOR_WORDS
from gensim.parsing.preprocessing import STOPWORDS
from nltk.tokenize import word_tokenize
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from nltk import pos_tag
import contractions
from  rdsmproj import utils


def get_id2word(texts:list[str],
                no_above:float=1.0,
                no_below:int=10,
                keep_n:int=100000) -> Dictionary:
    """
    Creates a gensim.corpora.dictionary.Dictionary mapping from word IDs to words. It is used to
    determine vocabulary size, as well as for debugging and topic printing.

    Parameters
    ----------
    no_above: float (Optional, default 1.0)
        Keep tokens (words) that are contained in no more than no_above documents, which is the
        fraction of total corpus size.
    no_below: int (Optional, default 10)
        Keep tokens (words) that are contained in at least no_below documents.
    keep_n: int (Optional, default 100000)
        Keep only the first keep_n most frequent tokens.

    Returns
    -------
    id2word: gensim.corpora.dictionary.Dictionary
        Dictionary mapping from word IDs to words. dict[(int, str)]
    """
    # Creates gensim.corpora.dictionary.Dictionary mapping from word IDs to words.
    id2word = Dictionary(texts)
    # Filters out the extreme words.
    id2word.filter_extremes(no_above=no_above, no_below=no_below, keep_n=keep_n)
    return id2word

def get_docs(data:list[dict]) -> list[str]:
    """
    Retrieves subreddit text data for topic generation. Only needed for subreddit data and not
    general text. Creates list of documents with subreddit text data stripped of brackets,
    web links, and email addresses.

    Parameters
    ----------
    data: list[dict]
        Subreddit data for a given subreddit. Structure is a list of dictionaries, one for each
        post containing metadata as well as post title and associated text and comment text for
        that post.

    Returns
    -------
    documents: list[str]
        List of strings with each string (document) being the text for the title of the post along
        with the text of the post itself and any retrieved comments to that post.
    """
    # Initializes documents list.
    documents = []
    # Iterates over every dictionary item in data.
    for item in data:
        # Checks if 'all_text' is not in dictionary of item. This is for posts that do not have
        # associated comment data, which would be found in the 'all_text' key.
        if 'all_text' not in item:
            # Gets title text.
            title = item['title']
            # Checks if post text exists, then retrieves it.
            if 'selftext' in item:
                selftext = item['selftext']
            # If post text does not exist, then sets selftext to empty string.
            else:
                selftext = ''
            # Creates entry of retrieved title and post text data.
            all_text = f"{title} {selftext}"
        else:
            # Retrieves title, post, and comment data from item.
            all_text = item['all_text']

        # Ensures that encoding is utf-8 and removes junk items.
        all_text = strip_junk(all_text)
        # Expands contractions (e.g. can't -> cannot)
        try:
            all_text = contractions.fix(all_text, slang=False)
        except IndexError:
            pass
        documents.append(all_text)

    return documents

def get_unique(data:list[Any], verbose:Optional[bool] = False):
    """
    Finds the set of unique items in the data and returns that list of unique items.

    Parameters:
    ----------
    data: list[Any]
        List of text data to be parsed for duplicates.
    verbose: bool (Optional, default False)
        If True, will print out total number of items and final number of unique items.

    Returns
    -------
    data: list[Any]
        List of passed text data with only unique entries. Note that creating the set used to
        find unique values does NOT preserve order of the entries.
    """
    # Finds the number of entries in the list, for use in verbose.
    initial = len(data)
    # Uses set to quickly and efficiently find only unique entries.
    documents = list(set(data))
    # Finds the number of entries in the newer list, for use in verbose.
    final = len(data)
    # If verbose is True, prints text of before and after size of list.
    if verbose:
        print(f'Total number of documents: {initial}. Final unique number of documents: {final}.')
    return documents

def strip_junk(text:str) -> str:
    """
    Filters text by removing brackets and their text (e.g. [deleted]), internet links, and email
    addresses. Also ensures utf-8 encoding (e.g. '\u041d\u043ew \u0430r\u0435 \u0443\u043eu? ' ->
    'How are you? ')

    Parameters:
    ----------
    text: str
        Input text string to be processed.

    Returns
    -------
    text: str
        Output text string after filters applied.
    """
    # Ensures utf-8
    text = text.encode('utf-8').decode('utf-8')
    #remove brackets such as [deleted]
    text = re.sub(r"\[.*?\]", '', text)
    #remove www links
    text = re.sub(r"www\S+", '', text)
    #remove http(s) links
    text = re.sub(r"http\S+", '', text)
    #remove email addresses
    text = re.sub(r"\S*@\S+", '', text)

    return text

def get_phrases(tokenized_docs:list[list[str]],
                ngram_vocab_args:Optional[dict]=None) -> list[list[str]]:
    """
    Creates phrases of bigrams and trigrams from the tokenized documents using Gensim. The phrases
    replace the individual tokens. (e.g ['New', 'York'] becomes ['New York'])

    Parameters
    ----------
    tokenized_docs: list[list[str]]
        Tokenized list of documents.

    ngram_vocab_args: dict (Optional, default None)
        Pass custom arguments to gensim phrases.

        For more information visit:
        https://radimrehurek.com/gensim/models/phrases.html

    Returns:
        Tokenized list of documents with bigram and trigram phrases replacing related unigram
        tokens.
    """
    if not ngram_vocab_args:
        ngram_vocab_args = {'sentences':tokenized_docs,
                            'min_count': 5,
                            'threshold':10.0,
                            'delimiter': ' ',
                            'connector_words':ENGLISH_CONNECTOR_WORDS}
    else:
        ngram_vocab_args['sentences'] = tokenized_docs
        ngram_vocab_args['delimiter'] = ' '

    bigram = Phrases(**ngram_vocab_args)
    bigram_mod = Phraser(bigram)
    bigrams = [bigram_mod[doc] for doc in tqdm(tokenized_docs, desc='Creating Bigrams')]

    ngram_vocab_args['sentences'] = bigrams
    trigram = Phrases(**ngram_vocab_args)
    trigram_mod = Phraser(trigram)
    trigrams = [trigram_mod[doc] for doc in tqdm(bigrams, desc='Creating Trigrams')]

    return trigrams

def tokenize_docs(documents:list[str]) -> list[list[str]]:
    """
    Tokenizes a list of text documents for use in LDA topic model generation or coherence model
    generation.

    Parameters:
    ----------
    documents: list[str]
        List of strings with each string being a separate document.

    Returns
    -------
        List of string tokens (words) with each list corresponding to a document and the list of
        string tokens (words) associated with that document.
    """
    # Applies tokenization to each document in documents.
    return [tokenize_text(doc) for doc in tqdm(documents, desc='Tokenizing Text')]

def tokenize_text(text:str) -> list[str]:
    """
    Tokenizes text str into list of lowercase tokens.

    Parameters:
    ----------
    text: str
        Text to be tokenized.

    Returns
    -------
        List of str tokens (words).
    """
    text = word_tokenize(text)
    text = [word.lower() for word in text if word.isalpha() and word not in STOPWORDS]

    return text

def create_corpus(id2word:Dictionary,
                  tokenized_docs:list[list[str]]) -> list[list[tuple[int, int]]]:
    """
    Creates a corpus for use in LDA topic model generation or coherence model generation.

    Parameters:
    ----------
    id2word: gensim.corpora.dictionary.Dictionary, dict[(int, str)]
            Mapping from word IDs to words. It is used to determine vocabulary size, as well as for
            debugging and topic printing.

    tokenized_docs: list[list[str]]
        Tokenized list of documents.

    Returns:
    -------
        Stream of document vectors made up of lists of tuples with (word_id, word_frequency).
    """
    return [id2word.doc2bow(doc) for doc in tokenized_docs]

def get_word_net_pos(tag:str) -> str:
    """
    Parses POS tags and returns the wordnet POS tag for use in lemmatizer.

    Parameters:
    ----------
    tag: str
        text of POS tag from WordNetLemmatizer.

    Returns:
    -------
        POS tag if adjective, verb, noun, or adverb. None if other POS.
            'J', 'V', 'N', 'R', or None
    """
    if tag.startswith('J'):
        return wordnet.ADJ
    elif tag.startswith('V'):
        return wordnet.VERB
    elif tag.startswith('N'):
        return wordnet.NOUN
    elif tag.startswith('R'):
        return wordnet.ADV
    else:
        return None

def lemma_text(tokenized_doc:list[str]) -> list[str]:
    """
    Lemmatizes tokens. Removes tokens if not adjective, adverb, noun, or verb. Removes any
    remaining tokens if they are in STOPWORDS or not two characters or longer.

    Parameters:
    ----------
    tokenized_doc: list[str]
        Tokenized document.

    Returns:
    -------
        Tokenized document.
    """
    # Initializes Lemmatizer.
    lmr = WordNetLemmatizer()
    # Tags tokens with part of speech (POS)
    tag_tokens = pos_tag(tokenized_doc)
    # Converts POS into wordnet adjective, verb, noun, adverb, or None.
    tag_tokens = [(token, get_word_net_pos(pos)) for token, pos in tag_tokens]
    # Lemmatizes tokens if POS is not None.
    tag_tokens = [lmr.lemmatize(token, pos=tag) for token, tag in tag_tokens if tag]
    # Removes tokens if token size is less than 2 or if they are in STOPWORDS.
    tag_tokens = [token for token in tag_tokens if len(token) > 1 and token not in STOPWORDS]
    return tag_tokens

def get_lemma(tokenized_docs:list[list[str]]) -> list[list[str]]:
    """
    Tags tokens in each document with part of speech (POS) and removes if not adjective, adverb,
    noun, or verb. Removes remaining tokens if they are in STOPWORDS or not greater than 2
    characters in length.

    Parameters
    ----------
    tokenized_docs: list[list[str]]
        Tokenized list of documents.

    Returns:
    -------
        Tokenized documents
    """
    tokenized_docs = [lemma_text(doc) for doc in tqdm(tokenized_docs, desc='Lemmatizing Tokens')]
    return tokenized_docs

class PreProcess:
    """
    Class to preprocess data for topic modeling. Takes a the name of a json file for text data and
    generates processed set of documents, id2word gensim.corpora.dictionary.Dictionary mapping from
    word IDs to words, a tokenized list of documents, and a corpus derived from the tokenized
    documents and id2word. These files are all required for LDA topic model generation, coherence
    model generation, and/or for use with the other topic model generation algorithms.

    Parameters:
    ----------
    name: str
        Name of subreddit or json file of text data.

    data_path: Path, str (Optional, default None)
        Path to data file where json is located.

    model_path: Path, str (Optional, default None)
        Path to model data where files will be written to or loaded from.
    
    documents: list[str] (Optional, default None)
        Can pass a list of document strings directly instead of reading from file.

    no_above: float (Optional, default 1.0)
        Keep tokens (words) that are contained in no more than no_above documents, which is the
        fraction of total corpus size.

    no_below: int (Optional, default 10)
        Keep tokens (words) that are contained in at least no_below documents.

    keep_n: int (Optional, default 100000)
        Keep only the first keep_n most frequent tokens.


    Returns, when called:
    ----------
    documents
    tokenized_docs
    id2word
    corpus
    """
    def __init__(self, name:str,
                 datafile_path:Optional[Union[Path,str]]=None,
                 data_folder:Optional[Union[Path,str]]=None,
                 model_path:Optional[Union[Path,str]]=None,
                 documents:list[str]=None,
                 no_above:Optional[float] = 1.0,
                 no_below:Optional[int] = 10,
                 keep_n: Optional[int] = 100000):

        # Initialize parameters.
        self.name = name
        self.no_above = no_above
        self.no_below = no_below
        self.keep_n = keep_n
        self.data_folder = data_folder
        self.documents = documents
        self.tokenized_docs = None
        self.data_path = None
        
        # Checks if datafile_path is given. If it exists, it loads the data,
        # strips junk, and finds the unique items to create the list of documents.
        if datafile_path:
            self.data_path = datafile_path
            data = utils.load_json(Path(self.data_path))
            documents = [strip_junk(doc) for doc in documents]
            self.documents = get_unique(data)
        # Checks if text documents are passed instead of a file path or subreddit name.
        elif documents:
            documents = [strip_junk(doc) for doc in documents]
            self.documents = get_unique(data)
        # If text documents are not passed and no datafile is passed, defaults to subreddit.
        else:
            if self.data_folder:
                comments = utils.get_data_path(self.data_folder)
            else:
                comments = utils.get_data_path('comments')
            self.data_path = Path(comments, f'{name}_comments.json')

        # Checks if model_path exists. If it is given, then it checks if the path exists and
        # creates the directory if it does not.
        if model_path:
            utils.check_folder(model_path)
            self.model_path = model_path
        # If model_path is not given, then it uses default model directory. It checks if the path
        # exits, then creates directory if it does not.
        else:
            model_path = Path(f'{Path.cwd()}/data/models/{name}')
            utils.check_folder(model_path)
            self.model_path = model_path

        if Path(self.model_path,f'{self.name}_documents.json').is_file():
            self.documents = utils.load_json(Path(self.model_path,
                                       f'{self.name}_documents.json'))
        if Path(self.model_path,f'{self.name}_tokenized_docs.json').is_file():
            self.tokenized_docs = utils.load_json(Path(self.model_path,
                                       f'{self.name}_tokenized_docs.json'))

    def __call__(self):
        """
        Returns
        -------
            documents, tokenized documents, id2word, and corpus objects.
        """
        # If data is not already present in self.documents, then it defaults to Reddit data
        # extraction and filtering loading the .json from data_path.
        if self.documents is None:
            data = utils.load_json(Path(self.data_path))
            documents = get_docs(data)
            documents = [doc for doc in documents]
            self.documents = get_unique(documents)

        # Dumps the documents data to a file for retrieval and use later to preserve order of
        # documents, which is essential for reproducibility of results and analysis.
        utils.dump_json(self.documents, self.model_path,f'{self.name}_documents')

        # Once document data is retrieved, then the tokenized documents, id2word, and corpus
        # are generated from the data.
        if self.tokenized_docs is None:
            tokenized_docs = tokenize_docs(self.documents)
            # Lemmatizes Tokens.
            tokenized_docs = get_lemma(tokenized_docs)
            # Creates bigrams and trigrams.
            self.tokenized_docs = get_phrases(tokenized_docs)
        # Saves the tokenized documents so that tokenization and ngram creation does not need
        # to be redone each time.
        utils.dump_json(tokenized_docs,self.model_path,f'{self.name}_tokenized_docs')
        # Creating id2word and corpus from tokenized documents is trivial and takes almost no
        # time and thus is not saved to a file. They are also static in relation to tokenized
        # documents.
        id2word = get_id2word(tokenized_docs,
                            no_above = self.no_above,
                            no_below = self.no_below,
                            keep_n=self.keep_n)
        corpus = create_corpus(id2word, tokenized_docs)

        return self.documents, tokenized_docs, id2word, corpus
