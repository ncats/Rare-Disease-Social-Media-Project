## Section: GARD SEARCH
# can identify rare diseases in text using the GARD dictionary from neo4j
# and map a GARD ID, name, or synonym to all of the related synonyms for searching APIs
from typing import List, Dict, Union, Optional, Set, Tuple
import requests, string, random
from nltk import tokenize as nltk_tokenize
class GARD_Search:
    def __init__(self):
        import json, codecs
        #These are opened locally so that garbage collection removes them from memory
        try:
            with codecs.open('gard-id-name-synonyms.json', 'r', 'utf-8-sig') as f:
                diseases = json.load(f)
        except:
            r = requests.get('https://raw.githubusercontent.com/ncats/epi4GARD/master/EpiExtract4GARD/gard-id-name-synonyms.json')
            diseases = json.loads(r.content)
        
        from nltk.corpus import stopwords
        try:
            STOPWORDS = set(stopwords.words('english'))
            r = requests.get('https://raw.githubusercontent.com/powerlanguage/word-lists/master/1000-most-common-words.txt')
            five_and_less = {word for word in r.text.split('\n') if len(word)<=5}
            STOPWORDS.update(five_and_less)
        except:
            import nltk
            nltk.download('stopwords')
            STOPWORDS = set(stopwords.words('english'))
            
            #'https://raw.githubusercontent.com/sindresorhus/word-list/main/words.txt'
            r = requests.get('https://raw.githubusercontent.com/powerlanguage/word-lists/master/1000-most-common-words.txt')
            five_and_less = {word for word in r.text.split('\n') if len(word)<=5}
            STOPWORDS.update(five_and_less)
        
        #This should be a list of all GARD IDs for purposes like random choice for testing
        GARD_id_list = [entry['gard_id'] for entry in diseases]
        #keys are going to be disease names, values are going to be the GARD ID, set up this way bc dictionaries are faster lookup than lists
        GARD_dict = {}
        #Find out what the length of the longest disease name sequence is, of all names and synonyms. This is used by get_diseases
        max_length = -1
        for entry in diseases:
            if entry['name'] not in GARD_dict.keys():
                s = entry['name'].lower().strip()
                if s not in STOPWORDS and len(s)>1:
                    GARD_dict[s] = entry['gard_id']
                    #compare length
                    max_length = max(max_length,len(s.split()))

            if entry['synonyms']:
                for synonym in entry['synonyms']:
                    if synonym not in GARD_dict.keys():
                        s = synonym.lower().strip()
                        if s not in STOPWORDS and len(s)>3:
                            GARD_dict[s] = entry['gard_id']
                            max_length = max(max_length,len(s.split()))
        
        GARD_dict['cf'] = 'GARD:0006233'
        GARD_dict['als'] = 'GARD:0005786'
        GARD_dict.pop('dyspraxia')
        GARD_dict.pop('fava')
        GARD_dict.pop('arms')
        
        # For some reason this one-liner doesn't work: (I think it is because of the sort function)
        #self.id_dict = {gard_id:[k for k,v in GARD_dict.items() if v==gard_id].sort(reverse=True, key=lambda x:len(x)) for gard_id in self.id_list}
        id_dict = dict()
        for gard_id in GARD_id_list:
            l = [k for k,v in GARD_dict.items() if v==gard_id]
            l.sort(reverse=True, key=lambda x:len(x)) 
            id_dict[gard_id] = l
        
        self.id_list = GARD_id_list
        # Returns a dictionary in form of 
        self.name_dict = GARD_dict
        # Returns a dictionary in form of {"GARD_ID":["Longest Disease Name/Synonym","2nd Longest Name/Synonym","Synonym",...]}
        self.id_dict = id_dict
        self.max_length = max_length
    
    def __str__(self) -> str:
        return str(
'''
Instantiation: rd_identify = GARD_Search() \n
Calling: diseases, ids = rd_identify(text) \n
Search GARD ID or any name and get a list of all disease names: \ndz_name_list = rd_identify.autosearch(searchterm) \n
GARD ID List: rd_identify.id_list \n ["GARD:0000001", "GARD:0000002"] \n
Name Dictionary: rd_identify.name_dict \n {"Name":"GARD_ID"} \n
GARD ID Dictionary: rd_identify.id_dict \n {"GARD_ID":["Longest Disease Name/Synonym", "2nd Longest Name/Synonym", ...]}
''')
    
    def __call__(self, sentence:str) -> Tuple[List[str], List[str]]:
        return self.get_diseases(sentence)
    
    #Works much faster if broken down into sentences.
    #compares every phrase in a sentence to see if it matches anything in the GARD dictionary of diseases.
    def get_diseases(self, sentence:str) -> Tuple[List[str], List[str]]:   
        tokens = [s.lower().strip() for s in nltk_tokenize.word_tokenize(sentence) if s not in string.punctuation]
        #print("raw tokens",tokens)
        
        #Combine 's with the previous word
        while "'s" in tokens:
            pop_index = tokens.index("'s")
            #print(pop_index)
            if pop_index>0:
                tokens[pop_index-1]=tokens[pop_index-1]+"'s"
            tokens.pop(pop_index)

        #print("processed tokens",tokens)
        
        diseases = []
        ids = []
        i=0
        #Iterates through every word, builds string that is max_length or less to compare.
        while i <len(tokens):
            #print("i",i)
            #Find out the length of the comparison string, either max_length or less. This brings algorithm from O(n^2) to O(n) time
            compare_length = min(len(tokens)-i, self.max_length)

            #print("compare_length",compare_length)

            #Compares longest sequences first and goes down until there is a match
            while compare_length>0:
                s = ' '.join(tokens[i:i+compare_length]).lower()

                #print("Comparator:",s)

                if s in self.name_dict.keys():
                   # print("s in self.GARD_dict.keys()",s in self.GARD_dict.keys())

                    diseases.append(s)
                    ids.append(self.name_dict[s])
                    #Need to skip over the next few indexes
                    i+=compare_length-1
                    #print('found',self.name_dict[s],"new i is",i)
                    break
                else:
                    compare_length-=1
            i+=1
        return diseases,ids
    
    #Can search by 7-digit GARD_ID, 12-digit "GARD:{GARD_ID}", matched search term, or arbitrary search term
    #Returns list of terms to search by
    # search_term_list = autosearch(search_term, GARD_dict)
    def autosearch(self, searchterm:Union[str,int], matching=2) -> List[str]:
        #comparisons below only handly strings, allows int input
        if type(searchterm) is not str:
            searchterm = str(searchterm)
        
        #for the disease names to match
        searchterm = searchterm.lower()
        
        while matching>=1:
            #search in form of 'GARD:0000001'
            if 'gard:' in searchterm and len(searchterm)==12:
                searchterm = searchterm.replace('gard:','GARD:')
                l = self.id_dict[searchterm]
                l.sort(reverse=True, key=lambda x:len(x))
                if len(l)>0:
                    print("SEARCH TERM MATCHED TO GARD DICTIONARY. SEARCHING FOR: ",l)
                    return l

            #can take int or str of digits of variable input
            #search in form of 777 or '777' or '00777' or '0000777'
            elif searchterm[0].isdigit() and searchterm[-1].isdigit():
                if len(searchterm)>7:
                    raise ValueError('GARD ID IS NOT VALID. RE-ENTER SEARCH TERM')
                searchterm = 'GARD:'+'0'*(7-len(str(searchterm)))+str(searchterm)
                l = self.id_dict[searchterm]
                l.sort(reverse=True, key=lambda x:len(x))
                if len(l)>0:
                    print("SEARCH TERM MATCHED TO GARD DICTIONARY. SEARCHING FOR: ",l)
                    return l

            #search in form of 'mackay shek carr syndrome' and returns all synonyms ('retinal degeneration with nanophthalmos, cystic macular degeneration, and angle closure glaucoma', 'retinal degeneration, nanophthalmos, glaucoma', 'mackay shek carr syndrome')
            #considers the GARD ID as the lemma, and the search term as one form. maps the form to the lemma and then uses that lemma to find all related forms in the GARD dict. 
            elif searchterm in self.name_dict.keys():
                print("currently in form search")
                print("searchterm in self.GARD_dict.keys()",searchterm in self.name_dict.keys())
                #must convert the term back to a GARD ID
                l = self.id_dict[self.name_dict[searchterm]]
                print("self.get_names_from_id(searchterm)",l)
                
                l.sort(reverse=True, key=lambda x:len(x))
                print("l.sort(reverse=True, key=lambda x:len(x))", l)
                

                print("SEARCH TERM MATCHED TO GARD DICTIONARY. SEARCHING FOR: ",l)
                return l

            else:
                #This can be replaced with some other common error in user input that is easily fixed
                searchterm = searchterm.replace('-',' ')
                searchterm = searchterm.replace("'s","")
                return self.autosearch(searchterm, matching-1)
        print("SEARCH TERM DID NOT MATCH TO GARD DICTIONARY. SEARCHING BY USER INPUT")
        return [searchterm]

    # Useful for testing
    # Return a random GARD_ID Search Term list
    def random_disease_list(self) -> List[str]:
        return random.choice(list(self.id_dict.values()))
    
    # Return a random disease term
    def random_disease(self) -> str:
        return random.choice(self.random_disease_list())

    # Return a random GARD_ID
    def random_id(self) -> str:
        return random.choice(self.id_list)