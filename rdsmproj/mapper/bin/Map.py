import nltk
nltk.download('wordnet')
nltk.download('omw-1.4')
from nltk.stem import WordNetLemmatizer
import platform
import os
from datetime import datetime
from abc import ABC
import spacy
from spacy.matcher import PhraseMatcher
#from spacy.tokens import Doc
from spacy.tokenizer import Tokenizer
from spacy.lang.char_classes import ALPHA, ALPHA_LOWER, ALPHA_UPPER, CONCAT_QUOTES, LIST_ELLIPSES, LIST_ICONS
from spacy.util import compile_infix_regex
#from collections import OrderedDict
import threading
import re
from rdsmproj.mapper.bin.Blacklist import Blacklist

# Base mapper class, common properties in all child classes will be inherited
class Map(ABC):
    def __init__(self, bl=None):
        self.counter = 0
        self.id_list = list()
        self.col_match_list = list()
        self.name_list = list()
        self.context_list = list()
        self.matches_list = list()
        self.word_to_gard = dict()
        self.normalize_dict = dict()
        self.IDcol = str()
        self.TEXTcols = list()
        self.cols = list()

        self.nlp = None
        self.matcher = None
        self.attr = None
        self.matches = dict()

        if bl and isinstance(bl,Blacklist):
            self.blacklist = bl
            
        else:
            self.blacklist = Blacklist()
            self.blacklist._clear()
            self.blacklist._clear(acronyms=True)

            # Adds common false positives to a list to ignore when matching
            self.blacklist._add('type ii')
            self.blacklist._add('type II')
            self.blacklist._add('type 2')
            self.blacklist._add('former')
            self.blacklist._add('formerly')
            self.blacklist._add('subtype')
            self.blacklist._add('type')
            self.blacklist._add('ML 2')

        self.t0 = datetime.now()
        self.root = os.getcwd()
        self.system = platform.system()
        self.isWindows = False
        
        self.gardObj = None
        self.dataObj = list()
        self.batchsize = self.calc_batch()

        if self.system == 'Windows':
            self.path_char = '\\'
            self.isWindows = True
        elif self.system == 'Linux':
            self.path_char = '/'
        elif self.system == 'Darwin':
            self.path_char = '/'
        else:
            self.path_char = '/'

        # Default input file paths
        self.gard = self._create_path('neo4j_rare_disease_list.json', input_file=True)
        self.data = self._create_path('preprocessed_subreddit_list.json', input_file=True)

        print('Default GARD Data file path set to {}'.format(self.gard))
        print('Default Input Data file path set to {}'.format(self.data))

        print('Map Object Initialized')

    # Calculates a systems maximum allowed batch size, currently is set to a static number until it is implemented
    def calc_batch(self):
        return 100000

    # creates a file path to the data folder with the filename variable
    def _create_path (self,filename,input_file):
        if input_file:
            if self.isWindows == True:
                path = (self.root
                + self.path_char 
                + 'mapper'
                + self.path_char 
                + 'bin' 
                + self.path_char
                + 'data' 
                + self.path_char
                + 'input'
                + self.path_char 
                + filename)
            else:
                path = (self.root
                + self.path_char 
                + 'data' 
                + self.path_char 
                + 'input'
                + self.path_char 
                + filename)
        else:
            if self.isWindows == True:
                path = (self.root
                + self.path_char 
                + 'mapper'
                + self.path_char 
                + 'bin' 
                + self.path_char 
                + 'data' 
                + self.path_char 
                + 'output'
                + self.path_char 
                + filename)
            else:
                path = (self.root
                + self.path_char 
                + 'data' 
                + self.path_char 
                + 'output'
                + self.path_char 
                + filename)

        return path

    # batches data and multi-threads a function, for parallel processing
    def batch_thread(self, obj, funct, size):
        threads = list()
        for i in range(0,len(obj),size):
                batch_json = obj[i:i + size]
                #print(batch_json)
                thread = threading.Thread(target=funct, args=(batch_json,))

                thread.daemon = True
                threads.append(thread)

        for i in range(len(threads)):
            threads[i].start()

        for i in range(len(threads)):
            threads[i].join()

    # Converts GARD JSON object to a python dictionary
    def _clean_gard(self,data):
        try:  
            gard_entries = list()
            disease = dict()
            syn_list = list()
            
            for entry in data:
                gard_entries.append(entry)

            for group in gard_entries:
                entry_name = self._normalize(group['Name'])
                entry_id = group['GARD id']
                syn_list = group['Synonyms']
                disease[entry_id] = dict()
                
                if syn_list != None:
                    norm_syn_list = list()
                    for syn in syn_list:
                        norm_syn = self._normalize(syn)
                        if len(norm_syn) > 0:
                            norm_syn_list.append(norm_syn)

                    syn_list = norm_syn_list

                disease[entry_id]['name'] = entry_name
                disease[entry_id]['synonyms'] = syn_list
                
            self.gardObj = disease
            print('Gard Data Cleaned and Stored in Map Object')

        except FileNotFoundError as e:
            print(e)
    
    # initializes SpaCy NLP package with custom tokenizer and language model
    def setup_nlp(self):
        self.nlp = spacy.load('en_core_web_lg')
        self.nlp.tokenizer = self._custom_tokenizer(self.nlp)
        self.attr = 'LOWER'
        self.matcher = PhraseMatcher(self.nlp.vocab, attr=self.attr)

    # returns a list of rare disease names and synonyms SpaCy Doc objects for use in matching
    def make_patterns(self):
        name_patterns = list()
        syn_patterns = list()

        for id in self.gardObj:
            text = self.gardObj[id]['name']
            self.word_to_gard[text.lower()] = id

            name_doc = self.nlp.make_doc(text)
            name_patterns.append(name_doc)

            if self.gardObj[id]['synonyms'] == None:
                continue

            for syn in self.gardObj[id]['synonyms']:
                if self.is_acronym(syn):
                    continue
                elif syn in self.blacklist._getall() or syn in self.blacklist._getall(acronyms=True):
                    continue
                else:
                    self.word_to_gard[syn.lower()] = id
                    syn_doc = self.nlp.make_doc(syn)
                    syn_patterns.append(syn_doc)

        return [name_patterns,syn_patterns]

    # Identifies text as an acronym or not
    def is_acronym(self, text, mix=True):
        res = True
        tokens = re.split('[-/]', text)
        for token in tokens:
            if mix:
                tmp = (re.search('[A-Z]', token[1:]) or re.search('[A-Z][^A-Za-z]*$', token))\
                    and not re.search('\W', re.sub('[\.]', '', token))
            else:
                tmp = token.isupper() and not re.search('\W', re.sub('[\.]', '', token))
            if not tmp:
                return False

        return res

    # Removes parenthesis and the words inside of them of text if certain criteria are met
    def remove_parenthesis(self, text, delete=False):
        edit = text

        # if the standardized genome format is found, dont delete the parenthesis
        ms = list(re.finditer(r'(?:Del|I|Dup)\w*\([\w\.]+\)\([\w\.]+\)', text, flags=re.I))
        
        if not ms:
            matches = list(re.finditer(r"(\((.*?)\))", text))

            for match in matches:
                x,y = match.span()
                selected_phrase = text[x+1:y-1]
                fp_list = self.blacklist._getall()
                
                for fp in fp_list:
                    for word in selected_phrase.split():
                        if word == fp:
                            delete = True

                # if the text inside a parenthesis is an acronym or contains a false positive, delete it
                if self.is_acronym(selected_phrase) or delete:
                    edit = text[:x] + text[y:]
                    
                if len(edit) == 0:
                    edit = text
                    
        text = re.sub(r'^\s+|\s+$', '', edit)

        return text

    # Removes leftover HTML tags from text "ex. <h1>"
    def remove_tags(self, text):
        text = re.sub(r"(\<(.*?)\>)", " ", text)
        return text

    # Simplifies words in text to its singular form from plural
    def lemmatization(self, text):
        tokens = text.split()
        lemma = WordNetLemmatizer()
        lemma_tokens = []

        for x in tokens:
            if self.is_acronym(x):
                lemma_tokens.append(x)
                continue

            if '.' in x:
                loc = x.index('.')
                x = x.replace('.','')
                x = lemma.lemmatize(x.lower())
                x = x[:loc] + '.' + x[loc:]
                lemma_tokens.append(x)
            else:
                lemma_tokens.append(lemma.lemmatize(x.lower()))

        return ' '.join(lemma_tokens)

    # Combines all the normalization functions into one function
    def _normalize(self,text):
        text = re.sub(r'^\s+|\s+$', '', text)
        text = re.sub(r'[\s\t]+', ' ', text)
        text = self.remove_tags(text)
        text = re.sub(r'–', '\-', text)
        text = re.sub(r"’", '\'', text)
        text = re.sub(r"(?i)(and/or)", "and", text)
        text = re.sub(r"[^-\w./'\(\) ]", "", text)
        text = re.sub(r"(?i)(non )|(non- )", "non", text)
        text = re.sub(r"(?i)'s", "", text)
        text = self.lemmatization(text)
        text = self.remove_parenthesis(text)
        text = re.sub(r'[\s\t]+', ' ', text)
        text = re.sub(r'^\s+|\s+$', '', text)
        return text

    # Original SpaCy tokenizer but with one small edit to leave hyphenated words combined
    def _custom_tokenizer(self,nlp):
        infixes = (
            LIST_ELLIPSES
            + LIST_ICONS
            + [
                r"(?<=[0-9])[+\-\*^](?=[0-9-])",
                r"(?<=[{al}{q}])\.(?=[{au}{q}])".format(
                    al=ALPHA_LOWER, au=ALPHA_UPPER, q=CONCAT_QUOTES
                ),
                r"(?<=[{a}]),(?=[{a}])".format(a=ALPHA),
                #r"(?<=[{a}])(?:{h})(?=[{a}])".format(a=ALPHA, h=HYPHENS), #Commented out to keep hyphenated words together ex. "non-small"
                r"(?<=[{a}0-9])[:<>=/](?=[{a}])".format(a=ALPHA),
            ]
        )
        infix_re = compile_infix_regex(infixes)

        return Tokenizer(nlp.vocab, prefix_search=nlp.tokenizer.prefix_search,
                                    suffix_search=nlp.tokenizer.suffix_search,
                                    infix_finditer=infix_re.finditer,
                                    token_match=nlp.tokenizer.token_match,
                                    rules=nlp.Defaults.tokenizer_exceptions)
    # Sets GARD file path    
    def _loadGard(self,datafile_name):
        self.gard = self._create_path(datafile_name, input_file=True)
        print('GARD Data file path set to {}'.format(self.gard))

    # Sets Input file path
    def _loadData(self,datafile_name):
        self.data = self._create_path(datafile_name, input_file=True)
        print('Input Data file path set to {}'.format(self.data))

    # prints out GARD data (TESTING PURPOSES)
    def _gardData(self):
        print(self.gardObj)
        print(len(self.gardObj))

    # prints out Input data (TESTING PURPOSES)
    def _inputData(self):
        print(self.dataObj)