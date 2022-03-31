import platform
import json
import os
from datetime import datetime
from pathlib import Path
from abc import ABC
from types import NoneType
from variables import *
import spacy
from spacy.matcher import PhraseMatcher
from spacy.tokens import Doc
import threading
import pandas as pd
import csv
import re
from variables import false_positives

# Base mapper class, common properties in all child classes will be inherited
class Map(ABC):
    def __init__(self):
        self.counter = 0

        self.nlp = None
        self.matcher = None
        self.attr = None
        self.matches = dict()

        self.t0 = datetime.now()
        self.root = os.getcwd()
        self.system = platform.system()
        
        self.gardObj = None
        self.dataObj = list()
        self.batchsize = 1000

        if self.system == 'Windows':
            self.path_char = '\\'
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

    def _create_path (self,filename):
        path = (self.root 
            + self.path_char 
            + 'mapper'
            + self.path_char 
            + 'data' 
            + self.path_char 
            + filename)

        return path

    def _clean_gard(self,data):
        try:
            gard_entries = list()
            disease = dict()

            for entry in data:
                gard_entries.append(entry)

            for group in gard_entries:
                entry_name = group['Name']
                entry_id = group['GARD id']
                syn_list = group['Synonyms']
                
                if syn_list == None:
                    continue

                disease[entry_name] = [entry_id,syn_list]
                self.gardObj = disease

            print('Gard Data Cleaned and Stored in Map Object')

        except Exception:
            print('[ERROR] Invalid Input Data Type:\n[TIP] Change path with \'_load()\' method')
        
    def _loadGard(self,datafile_name):
        self.gard = self._create_path(datafile_name)
        print('GARD Data file path set to {}'.format(self.gard))

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

    def _get_matches(self):
        with open(self._create_path('new_normalized_subreddit_matches.json'),'r',encoding='utf-8') as f:
                norm = json.load(f)
                return norm

    def _get_true_positives(self):
        return {key:value for key, value in self.matches.items()
                if key not in self.false_positives}

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

    def _convert_data(self,chunk):
        for text, context in chunk:
            chunk_tuple = (text,context)
            self.dataObj.append(chunk_tuple)
    
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

   
    def append_match_dict(self,doc):
        for match_id, start, end in self.matcher(doc):
            self.counter += 1
            pattern_type = self.nlp.vocab.strings[match_id]
            self.matches[doc._.name] = self.matches.get(doc._.name, []) + [(pattern_type, str(doc[start:end]))]
            
            print(f'Subreddit: {doc._.name} Match: {pattern_type, doc[start:end]}')
            

    def _process_doc(self,batch):
        for doc, context in self.nlp.pipe(batch, as_tuples=True):
            doc._.name = context['name']
            doc._.title = context['title']
            doc._.subscribers = context['subscribers']
            doc._.created_utc = context['created_utc']
            
            self.append_match_dict(doc)


    def _match(self, inputFile, gardFile):
        self._loadGard(gardFile)
        self._loadData(inputFile)
        self._clean()

        try:
            if self.gardObj == None or self.dataObj == None:
                raise Exception

            self.nlp = spacy.load('en_core_web_lg')
            self.attr = 'LOWER'
            self.matcher = PhraseMatcher(self.nlp.vocab, attr=self.attr)

            print('Making Doc Objects...')
           
            names = list()
            syn_list = list()
            name_patterns = list()
            syn_patterns = list()

            for name in self.gardObj:
                names.append(name)

                for syn in self.gardObj[name][1]:
                    if syn in false_positives_acronyms:
                        continue

                    if not syn.isupper() or len(syn) > 7:
                        syn_list.append(syn)

            for name in names:
                name_patterns.append(self.nlp.make_doc(name))

            for syn in syn_list:
                syn_patterns.append(self.nlp.make_doc(syn))

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

# find what GARD ids show up in the abstracts, sensitivity, false positive, time
class AbstractMap(Map):
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

                    for row in reader:
                        cleaned_abstract = row[1].replace(',','').replace('\"','')
                        cleaned_abstract = re.sub(' +', ' ', cleaned_abstract) 

                        if row[1].lower() == 'no abstract provided':
                            continue

                        writer.writerow([row[0],cleaned_abstract])

            self.dataObj = pd.read_csv(self._create_path('cleaned_abstracts.csv'),dtype=str)
            self.dataObj = self.dataObj.reindex(sorted(self.dataObj.columns, reverse=True), axis='columns')
            self.dataObj = [tuple(row) for row in self.dataObj.to_numpy()]
            
        except FileNotFoundError:
            print('[ERROR] No data and/or input file found in \'mapper/data/\' folder\n[TIP] Use Map objects \'_loadGard()\' or \'_loadData()\' method')
        except UnicodeDecodeError as e:
            print(row[0])
            print(e)

    def append_match_dict(self,doc):
        for match_id, start, end in self.matcher(doc):
            self.counter += 1
            pattern_type = self.nlp.vocab.strings[match_id]
            self.matches[doc._.id] = list(set(self.matches.get(doc._.id, []) + [(pattern_type, str(doc[start:end]))]))
            
            print(f'Abstract: {doc._.id} Phrase: {doc[start-5:end+5]} Word: {doc[start:end]}')
            print('\n')
            

    def _process_doc(self,batch):
        for ABSTRACT,ID in self.nlp.pipe(batch, as_tuples=True):
            ABSTRACT._.id = ID
            self.append_match_dict(ABSTRACT)

    def _match(self, inputFile, gardFile):
        self._loadGard(gardFile)
        self._loadData(inputFile)
        self._clean()
        
        try:
            if self.gardObj == None or self.dataObj == None:
                raise Exception

            self.nlp = spacy.load('en_core_web_lg')
            self.attr = 'LOWER'
            self.matcher = PhraseMatcher(self.nlp.vocab, attr=self.attr)

            Doc.set_extension('id', default = None)

            print('Making Doc Objects...')
           
            names = list()
            syn_list = list()
            name_patterns = list()
            syn_patterns = list()

            for name in self.gardObj:
                names.append(name)

                for syn in self.gardObj[name][1]:
                    if syn in false_positives_acronyms:
                        continue

                    if not syn.isupper() or len(syn) > 7:
                        syn_list.append(syn)

            for name in names:
                name_patterns.append(self.nlp.make_doc(name))

            for syn in syn_list:
                syn_patterns.append(self.nlp.make_doc(syn))

            self.matcher.add('Names', name_patterns)
            self.matcher.add('Synonyms', syn_patterns)

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
                self.dataObj = None

        except FileNotFoundError:
            print('empty data objects')

    def __del__(self):
        self.dataObj = None
    

