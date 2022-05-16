import platform
import json
import os
from datetime import datetime
from pathlib import Path
from abc import ABC
from variables import *
import spacy
from spacy.matcher import PhraseMatcher
from spacy.tokens import Doc
from spacy.tokenizer import Tokenizer
from spacy.lang.char_classes import ALPHA, ALPHA_LOWER, ALPHA_UPPER, CONCAT_QUOTES, LIST_ELLIPSES, LIST_ICONS
from spacy.util import compile_infix_regex
import threading
import pandas as pd
import csv
import re
from variables import false_positives

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

        self.t0 = datetime.now()
        self.root = os.getcwd()
        self.system = platform.system()
        self.isWindows = False
        
        self.gardObj = None
        self.dataObj = list()
        self.batchsize = 1000

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
        self.gard = self._create_path('neo4j_rare_disease_list.json')
        self.data = self._create_path('preprocessed_subreddit_list.json')

        print('Default GARD Data file path set to {}'.format(self.gard))
        print('Default Input Data file path set to {}'.format(self.data))

        print('Map Object Initialized')

    # creates a file path to the data folder with the filename variable
    def _create_path (self,filename):
        if self.isWindows == True:
            path = (self.root
            + self.path_char 
            + 'mapper'
            + self.path_char 
            + 'data' 
            + self.path_char 
            + filename)
        else:
            path = (self.root
            + self.path_char 
            + 'data' 
            + self.path_char 
            + filename)

        return path

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
                if syn in false_positives_acronyms:
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
        self.gard = self._create_path(datafile_name)
        print('GARD Data file path set to {}'.format(self.gard))

    # Sets Input file path
    def _loadData(self,datafile_name):
        self.data = self._create_path(datafile_name)
        print('Input Data file path set to {}'.format(self.data))

    def _gardData(self):
        print(self.gardObj)

    def _inputData(self):
        print(self.dataObj)
    

# Mapper for Reddit type input
class RedditMap(Map):
# Start of result displaying methods
    # Displays match results after matching, relative to GARD data
    def _display_results(self):
        self.false_positives = false_positives
        self.matches = self._get_matches()
        self.true_positives = self._get_true_positives()
        self.rare_disease_dict = dict()

        if self.gardObj == None or len(self.dataObj) == 0:
            self._clean()

        self._find_matches()
        print(len(self.rare_disease_dict))

        with open(self._create_path('subreddit_GARD_matches.json'), mode= 'w+', encoding='utf-8') as file:
            json.dump(self.rare_disease_dict, file)
            self.rare_disease_dict = None

    # Loads subreddit matches file
    def _get_matches(self):
        with open(self._create_path('new_normalized_subreddit_matches.json'),'r',encoding='utf-8') as f:
                norm = json.load(f)
                return norm

    # Returns only matches that are NOT false positives
    def _get_true_positives(self):
        return {key:value for key, value in self.matches.items()
                if key not in self.false_positives}

    # Matches the results to their respective GARD rare disease
    def _find_match(self,hit_list):
        hit_type = hit_list[0]
        hit_text = hit_list[1].lower()
        match_dict = dict()

        if hit_type == 'Names':
            for index in self.gardObj.keys():
                if hit_text == index.lower():
                    match_dict[self.gardObj[index][0]] = index

        if hit_type == 'Synonyms':
            for index in self.gardObj:
                for synonym in self.gardObj[index][1]:
                    if hit_text in synonym.lower():
                        match_dict[self.gardObj[index][0]] = index
                    
        return match_dict

    # Converts match results to a dictionary
    def _find_matches(self):
        for subreddit, hits in self.true_positives.items():
            search_term_list = [(hit[0], hit[1]) for hit in hits]
            search_term_list = list(set(search_term_list))
            gard_id_list = list()
            gard_name_list = list()

            for search_term in search_term_list:
                match_dict = self._find_match(search_term)
                gard_id_list.extend(list(match_dict.keys()))
                gard_name_list.extend(list(match_dict.values()))

            text, title, subscribers, created_utc = self._get_subreddit_data(subreddit)
            self.rare_disease_dict[subreddit] = {'GARD Names': list(set(gard_name_list)),
                                                'GARD ids': list(set(gard_id_list)),
                                                'title': title,
                                                'subscribers': subscribers,
                                                'created_utc': created_utc,
                                                'text': text
                                                }

    # Gets subreddit metadata
    def _get_subreddit_data(self,subreddit):
        data = [(text, context) for text, context in self.dataObj
                if context['name'] == subreddit]
        data = data[0]
        text = data[0]
        title = data[1]['title']
        subscribers = data[1]['subscribers']
        created_utc = data[1]['created_utc']
        return text, title, subscribers, created_utc

# Start of mapping methods
    # Cleans up both GARD and Input data for processing
    def _clean(self):
        try:
            with open(self.gard,'r',encoding='utf-8') as f:
                g = json.load(f)
            self._clean_gard(g)

            with open(self.data,'r',encoding='utf-8') as f:
                d = json.load(f)
            self._clean_input(d)
            
        except FileNotFoundError:
            print('[ERROR] No data and/or input file found in \'mapper/data/\' folder\n[TIP] Use Map objects \'_loadGard()\' or \'_loadData()\' method')
    
    # Converts data to a tuple then appends to a list
    def _convert_data(self,chunk):
        for text, context in chunk:
            chunk_tuple = (self._normalize(text),context)
            self.dataObj.append(chunk_tuple)
    
    # Converts data to a list of tuples, uses batching and threading to speed up the process
    def _clean_input(self,data):
        print('Cleaning Input Data, Please wait...')
        threads = list()

        for i in range(0,len(data),100):
            batch_str = json.dumps(data[i:i+100])
            batch_json = json.loads(batch_str)

            thread = threading.Thread(target=self._convert_data, args=[batch_json])
            thread.daemon = True
            threads.append(thread)
            
        for i in range(len(threads)):
            threads[i].start()

        print('Input Data Cleaned and Stored in Map Object')

   
    # Gathers information on each match during phrase matching
    def append_match_dict(self,doc):
        for match_id, start, end in self.matcher(doc):
            self.counter += 1
            pattern_type = self.nlp.vocab.strings[match_id]
            self.matches[doc._.name] = self.matches.get(doc._.name, []) + [(pattern_type, str(doc[start:end]))]
            
            print(f'Subreddit: {doc._.name} Match: {pattern_type, doc[start:end]}')
            
    # gets metadata of the subreddit document
    def _process_doc(self,batch):
        for doc, context in self.nlp.pipe(batch, as_tuples=True):
            doc._.name = context['name']
            doc._.title = context['title']
            doc._.subscribers = context['subscribers']
            doc._.created_utc = context['created_utc']
            
            self.append_match_dict(doc)

    # Starts phrase matching between the input and gard file, uses batching and threading to speed up the process
    def _match(self, inputFile, gardFile):
        self._loadGard(gardFile)
        self._loadData(inputFile)
        self._clean()

        try:
            if self.gardObj == None or self.dataObj == None:
                raise Exception

            self.nlp = spacy.load('en_core_web_lg')
            self.nlp.tokenizer = self._custom_tokenizer(self.nlp)
            self.attr = 'LOWER'
            self.matcher = PhraseMatcher(self.nlp.vocab, attr=self.attr)

            print('Making Doc Objects...')
            name_patterns,syn_patterns = self.make_patterns()

            self.matcher.add('Names', name_patterns)
            self.matcher.add('Synonyms', syn_patterns)

            Doc.set_extension('name', default = None)
            Doc.set_extension('title', default = None)
            Doc.set_extension('subscribers', default = None)
            Doc.set_extension('created_utc', default = None)

            print('Matching Doc Objects...')

            threads = list()
            
            for i in range(0,len(self.dataObj),10000):
                batch_json = self.dataObj[i:i+10000]
                thread = threading.Thread(target=self._process_doc, args=[batch_json])
                thread.daemon = True
                threads.append(thread)

            for i in range(len(threads)):
                threads[i].start()

            for i in range(len(threads)):
                threads[i].join()
            
            with open(self._create_path('new_normalized_subreddit_matches.json'), mode= 'w+', encoding='utf-8') as file:
                json.dump(self.matches, file)
                self.dataObj = None

        except FileNotFoundError:
            print('[ERROR] Missing 1 or 2 loaded files')

    def __del__(self):
        self.gardObj = None
        self.dataObj = None


# Mapper for Article Abstract type input
class AbstractMap(Map):
    # Normalizes Abstract strings and stores dataframe as a list of tuples
    def _clean(self):
        file_path = self.data.split(self.path_char)
        file_split = file_path[len(file_path)-1].split('.')
        file_type = file_split[1]
        file_name = file_split[0]

        if file_type == 'xlsx':
            temp_xlsx = pd.read_excel(self.data)
            temp_xlsx.to_csv(file_name.join('.csv'), encoding='latin-1', index=False) #does not work in utf-8 encoding
            self.data = file_name.join('.csv')
        try:
            with open(self.gard,'r',encoding='utf-8') as f:
                g = json.load(f)
            self._clean_gard(g)

            with open(self._create_path('cleaned_abstracts.csv'), 'w', newline='') as cleanfile:
                with open(self.data, 'r', encoding='utf-8', errors='ignore') as csvfile:
                    reader = csv.reader(csvfile, quotechar='\"')
                    writer = csv.writer(cleanfile)

                    # Normalizes the Abstract column data
                    for row in reader:
                        if row[1].lower() == 'no abstract provided': # Removes empty abstracts from final product
                            continue

                        cleaned_abstract = row[1]
                        cleaned_abstract = self._normalize(cleaned_abstract)
        
                        writer.writerow([row[0],cleaned_abstract])

            self.dataObj = pd.read_csv(self._create_path('cleaned_abstracts.csv'),dtype=str)
            self.dataObj = self.dataObj.reindex(sorted(self.dataObj.columns, reverse=True), axis='columns')
            self.dataObj = [tuple(row) for row in self.dataObj.to_numpy()]
            
        except FileNotFoundError:
            print('[ERROR] No data and/or input file found in \'mapper/data/\' folder\n[TIP] Use Map objects \'_loadGard()\' or \'_loadData()\' method')
        except UnicodeDecodeError as e:
            print(row[0])
            print(e)

    # Gathers information on each match during phrase matching
    def append_match_dict(self,doc):
        for match_id, start, end in self.matcher(doc):
            pattern_type = self.nlp.vocab.strings[match_id]
            self.matches[doc._.id] = list(set(self.matches.get(doc._.id, []) + [(pattern_type, str(doc[start:end]))]))

            self.id_list.append(str(doc._.id))
            self.name_list.append(str(doc[start:end]))

            if end + 10 > len(doc):
                self.context_list.append(str(doc[len(doc)-10:len(doc)]))
            elif start - 10 < 0:
                self.context_list.append(str(doc[0:start+10]))
            else:
                self.context_list.append(str(doc[start-10:end+10]))

            
    # gets metadata of the subreddit document
    def _process_doc(self,batch):
        for ABSTRACT,ID in self.nlp.pipe(batch, as_tuples=True):
            self.counter += 1
            ABSTRACT._.id = ID

            if self.counter % 1000 == 0:
                percentage = round((self.counter/len(self.dataObj))*100)
                print(f'{percentage}%')

            self.append_match_dict(ABSTRACT)

    def _clean_csv(self, df):
        # Creates new columns #DISEASE and #OCCUR
        d = df.value_counts(subset=['APPLICATION_ID','Matched_Word']).to_frame()
        n = df.drop_duplicates(['APPLICATION_ID', 'Matched_Word']).value_counts(subset=['APPLICATION_ID']).to_frame()
        t1 = pd.merge(df,n,on=['APPLICATION_ID'])
        t2 = pd.merge(t1,d,on=['APPLICATION_ID','Matched_Word'])

        # Adds names for new columns
        t2.columns = ['APPLICATION_ID', 'Abstract', 'Matched_Word', 'CONTEXT', 'GARD_id', '#DISEASE', '#OCCUR']
        t2 = t2[['APPLICATION_ID', 'Abstract', 'Matched_Word', 'CONTEXT', 'GARD_id', '#OCCUR', '#DISEASE']]

        # Saves a version of the file with repeating rows
        t2.to_csv('mapper\\data\\abstract_matches_w_dupes.csv', index=False)

        # Drops duplicate rows
        t3 = t2.drop_duplicates(['APPLICATION_ID','Matched_Word'])
        t3['Matched_Word'] = t3['Matched_Word'].str.lower()
        t4 = t3.drop_duplicates(subset=['APPLICATION_ID','Matched_Word'], keep='first')

        # Saves CSV file
        t4.to_csv('mapper\\data\\abstract_matches.csv', index=False)
        
        # Below lines are just for testing purposes
        df = pd.read_csv('mapper\\data\\abstract_matches.csv',index_col=False)
        print(df)

    # Starts phrase matching between the input and gard file, uses batching and threading to speed up the process
    def _match(self, inputFile, gardFile):
        self._loadGard(gardFile)
        self._loadData(inputFile)
        self._clean()

        try:
            if self.gardObj == None or self.dataObj == None:
                raise Exception

            # Loads SpaCy package with the custom tokenizer
            self.nlp = spacy.load('en_core_web_lg')
            self.nlp.tokenizer = self._custom_tokenizer(self.nlp)
            self.attr = 'LOWER'
            self.matcher = PhraseMatcher(self.nlp.vocab, attr=self.attr)
            Doc.set_extension('id', default = None)

            print('Making Doc Objects...')
            name_patterns,syn_patterns = self.make_patterns()
            
            # Adds normalized GARD data to PhraseMatcher object
            self.matcher.add('name', name_patterns)
            self.matcher.add('synonyms', syn_patterns)

            print('Matching Doc Objects')

            threads = list()
            for i in range(0,len(self.dataObj),1000):
                batch_json = self.dataObj[i:i+1000]
                thread = threading.Thread(target=self._process_doc, args=[batch_json])
                thread.daemon = True
                threads.append(thread)

            for i in range(len(threads)):
                threads[i].start()

            for i in range(len(threads)):
                threads[i].join()
            
            with open(self._create_path('new_normalized_abstract_matches.json'), mode= 'w+', encoding='utf-8') as file:
                print(len(self.matches))
                json.dump(self.matches, file)

            with open(self._create_path('abstract_matches.csv'), 'w', newline='') as mfile:
                match_writer = csv.writer(mfile)
                match_writer.writerow(['APPLICATION_ID', 'Abstract', 'Matched_Word','CONTEXT','GARD_id'])
                c = 0
                
                for entry in self.id_list:
                    for abs in self.dataObj:
                        if abs[1] == entry:
                            match_writer.writerow([entry, abs[0], self.name_list[c], self.context_list[c], self.word_to_gard[self.name_list[c].lower()]])
                    
            df = pd.read_csv(self._create_path('abstract_matches.csv'),index_col=False)
            df.groupby(['APPLICATION_ID', 'Matched_Word']).agg('count')
            self._clean_csv(df)

        except FileNotFoundError:
            print('empty data objects')

    def __del__(self):
        self.dataObj = None