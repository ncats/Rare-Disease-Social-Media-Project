import Map
import pandas as pd
import json
import csv
from spacy.tokens import Doc

class AbstractMap(Map.Map):
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

           
            df = pd.read_csv(self.data, sep='\t', encoding = 'latin1')
            df = df.drop('Year', axis=1)
            df[['Application_ID', 'Abstract']] = df[['Application_ID', 'Abstract']].astype(str)
            print(df)
            
            # Normalizes the Abstract column data
            r,c = df.shape
            temp = df
            for i in range(r):
                row = df.iloc[i]
                ABSTRACT = row["Abstract"]
                
                if ABSTRACT.lower() == 'no abstract provided': # Removes empty abstracts from final product
                    continue

            
                cleaned_abstract = self._normalize(ABSTRACT)
                temp.at[i,'Abstract'] = cleaned_abstract
                
            print(temp)   
            #self.dataObj = temp.reindex(sorted(temp.columns, reverse=True), axis='columns')
            self.dataObj = temp[['Abstract','Application_ID']]
            print(self.dataObj)
            self.dataObj = [tuple(row) for row in self.dataObj.to_numpy()]
            
        except AttributeError as e:
            print(e)
            print(row['Abstract'])

        except FileNotFoundError:
            print('[ERROR] No data and/or input file found in \'mapper/bin/data/\' folder')
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
        for ABSTRACT, ID in self.nlp.pipe(batch, as_tuples=True):
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
        t2.columns = ['APPLICATION_ID', 'Matched_Word', 'CONTEXT', 'GARD_id', '#DISEASE', '#OCCUR']
        t2 = t2[['APPLICATION_ID', 'Matched_Word', 'CONTEXT', 'GARD_id', '#OCCUR', '#DISEASE']]

        # Saves a version of the file with repeating rows
        t2.to_csv(self._create_path('abstract_matches_w_dupes.csv', input_file=False), index=False)

        # Drops duplicate rows
        t3 = t2.drop_duplicates(['APPLICATION_ID','Matched_Word'])
        t3['Matched_Word'] = t3['Matched_Word'].str.lower()
        t4 = t3.drop_duplicates(subset=['APPLICATION_ID','Matched_Word'], keep='first')

        # Saves CSV file
        t4.to_csv(self._create_path('abstract_matches.csv', input_file=False), index=False)
        
        # Below lines are just for testing purposes
        df = pd.read_csv(self._create_path('abstract_matches.csv', input_file=False),index_col=False)
        print(df)

    # Starts phrase matching between the input and gard file, uses batching and threading to speed up the process
    def _match(self, inputFile, gardFile):
        self._loadGard(gardFile)
        self._loadData(inputFile)

        self.false_positives._clear()
        self.false_positives._clear(acronyms=True)

        self.false_positives._add('type ii')
        self.false_positives._add('type II')
        self.false_positives._add('type 2')
        self.false_positives._add('former')
        self.false_positives._add('formerly')
        self.false_positives._add('subtype')
        self.false_positives._add('type')
        self.false_positives._add('ML 2')

        self._clean()

        #print(self.gardObj)

        try:
            if self.gardObj == None or self.dataObj == None:
                raise Exception

            # Loads SpaCy package with the custom tokenizer
            self.setup_nlp()
            Doc.set_extension('id', default = None)

            print('Making Doc Objects...')

            name_patterns,syn_patterns = self.make_patterns()
            
            # Adds normalized GARD data to PhraseMatcher object
            self.matcher.add('name', name_patterns)
            self.matcher.add('synonyms', syn_patterns)

            print('Matching Doc Objects')
            self.batch_thread(self.dataObj, self._process_doc, self.batchsize)
            
            with open(self._create_path('new_normalized_abstract_matches.json', input_file=False), mode= 'w+', encoding='utf-8') as file:
                print(len(self.matches))
                json.dump(self.matches, file)

            with open(self._create_path('abstract_matches.csv', input_file=False), 'w', newline='') as mfile:
                match_writer = csv.writer(mfile)
                match_writer.writerow(['APPLICATION_ID', 'Matched_Word','CONTEXT','GARD_id'])
                c = 0
                
                for entry in self.id_list:
                #for abs in self.dataObj:
                    #if abs[1] == entry:
                    try:
                        match_writer.writerow([entry, self.name_list[c], self.context_list[c], self.word_to_gard[self.name_list[c].lower()]])
                        c += 1
                    except KeyError as e:
                        print(e)
                        match_writer.writerow([entry, self.name_list[c], self.context_list[c]])
                        c += 1
                        continue

            df = pd.read_csv(self._create_path('abstract_matches.csv', input_file=False),index_col=False)
            df.groupby(['APPLICATION_ID', 'Matched_Word']).agg('count')
            self._clean_csv(df)
	
        except KeyError as e:
            print(e)
            match_writer.writerow([entry, self.name_list[c], self.context_list[c]])

        except FileNotFoundError:
            print('empty data objects')

    def __del__(self):
        self.dataObj = None
