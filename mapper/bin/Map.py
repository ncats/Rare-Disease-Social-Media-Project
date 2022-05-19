import platform
import os
from datetime import datetime
from pathlib import Path
from abc import ABC
import spacy
from spacy.matcher import PhraseMatcher
from spacy.tokens import Doc
from spacy.tokenizer import Tokenizer
from spacy.lang.char_classes import ALPHA, ALPHA_LOWER, ALPHA_UPPER, CONCAT_QUOTES, LIST_ELLIPSES, LIST_ICONS
from spacy.util import compile_infix_regex
import threading
import re
from FalsePositives import FalsePositives

# Base mapper class, common properties in all child classes will be inherited
class Map(ABC):
    def __init__(self):
        self.counter = 0
        self.id_list = list()
        self.name_list = list()
        self.context_list = list()
        self.matches_list = list()
        self.word_to_gard = dict()

        self.nlp = None
        self.matcher = None
        self.attr = None
        self.matches = dict()
        self.false_positives = FalsePositives()

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

    def calc_batch(self):
        return 1000

    # creates a file path to the data folder with the filename variable
    def _create_path (self,filename,input_file):
        if input_file:
            if self.isWindows == True:
                path = (self.root
                + self.path_char 
                + 'mapper'
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

    def batch_thread(self, obj, funct, size):
        threads = list()
        for i in range(0,len(obj),size):
                batch_json = self.dataObj[i:i + size]
                thread = threading.Thread(target=funct, args=[batch_json])
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
                        norm_syn_list.append(self._normalize(syn))
                    syn_list = norm_syn_list

                disease[entry_id]['name'] = entry_name
                disease[entry_id]['synonyms'] = syn_list
                
            self.gardObj = disease
            print('Gard Data Cleaned and Stored in Map Object')

        except Exception:
            print('[ERROR] Invalid Input Data Type:\n[TIP] Change path with \'_load()\' method')
    
    def setup_nlp(self):
        self.nlp = spacy.load('en_core_web_lg')
        self.nlp.tokenizer = self._custom_tokenizer(self.nlp)
        self.attr = 'LOWER'
        self.matcher = PhraseMatcher(self.nlp.vocab, attr=self.attr)

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
                if syn in self.false_positives._getall(acronyms=True):
                    continue

                if not syn.isupper() or len(syn) > 7:
                    self.word_to_gard[syn.lower()] = id
                    syn_doc = self.nlp.make_doc(syn)
                    syn_patterns.append(syn_doc)

        return [name_patterns,syn_patterns]

    def _normalize(self,text):
        text = re.sub('^\s+|\s+$', '', text)
        text = re.sub('–', '\-', text)
        text = re.sub("'", '\'', text)
        text = re.sub("(and/or)", "and", text)
        text = re.sub(' +', ' ', text) # Remove extra spaces
        text = re.sub("[^-\w./' ]", "", text)
        text = re.sub("(non )", "non", text)
        
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

    def _gardData(self):
        print(self.gardObj)

    def _inputData(self):
        print(self.dataObj)