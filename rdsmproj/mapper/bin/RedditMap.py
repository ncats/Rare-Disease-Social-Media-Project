from rdsmproj.mapper.bin import Map
import json
import threading
import spacy
from spacy.matcher import PhraseMatcher
from spacy.tokens import Doc

class RedditMap(Map.Map):
# Start of result displaying methods
    # Displays match results after matching, relative to GARD data
    def _display_results(self):
        self.matches = self._get_matches()
        self.true_positives = self._get_true_positives()
        self.rare_disease_dict = dict()

        if self.gardObj == None or len(self.dataObj) == 0:
            self._clean()

        self._find_matches()
        print(len(self.rare_disease_dict))

        with open(self._create_path('subreddit_GARD_matches.json', input_file=False), mode= 'w+', encoding='utf-8') as file:
            json.dump(self.rare_disease_dict, file)
            self.rare_disease_dict = None

    # Loads subreddit matches file
    def _get_matches(self):
        with open(self._create_path('new_normalized_subreddit_matches.json', input_file=False),'r',encoding='utf-8') as f:
                norm = json.load(f)
                return norm

    # Returns only matches that are NOT false positives
    def _get_true_positives(self):
        return {key:value for key, value in self.matches.items()
                if key not in self.false_positives._getall()}

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
        self.batch_thread(data, self._convert_data, 100)
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

            self.batch_thread(self.dataObj, self._process_doc, 10000)
            
            with open(self._create_path('new_normalized_subreddit_matches.json', input_file=False), mode= 'w+', encoding='utf-8') as file:
                json.dump(self.matches, file)
                self.dataObj = None

        except FileNotFoundError:
            print('[ERROR] Missing 1 or 2 loaded files')

    def __del__(self):
        self.gardObj = None
        self.dataObj = None