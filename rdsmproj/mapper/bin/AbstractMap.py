from rdsmproj.mapper.bin import Map
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

        if file_type == 'json':
            temp_xlsx = pd.read_json(self.data)
            print(temp_xlsx)
            temp_xlsx.to_csv(file_name.join('.csv'), encoding='latin-1', index=False)
            self.data = file_name.join('.csv')

        if file_type == 'xlsx':
            temp_xlsx = pd.read_excel(self.data)
            temp_xlsx.to_csv(file_name.join('.csv'), encoding='latin-1', index=False) #does not work in utf-8 encoding
            self.data = file_name.join('.csv')
        try:
            with open(self.gard,'r',encoding='utf-8') as f:
                g = json.load(f)
            self._clean_gard(g)

            if file_type == 'txt':
                df = pd.read_csv(self.data, sep='\t', encoding = 'latin-1')
            else:
                df = pd.read_csv(self.data, encoding = 'latin-1')

            if 'Year' in df.columns:
                df = df.drop('Year', axis=1)

            df[self.cols] = df[self.cols].astype(str)
            df = df[self.cols]

            print(df)
            
            # Normalizes the text column data
            r,c = df.shape
            tempObj = list()

            for i in range(r):
                row = df.iloc[i]
                #text_list = list()

                for col in self.TEXTcols:
                    ABSTRACT = row[col]
                    cleaned_abstract = self._normalize(ABSTRACT)
                    #text_list.append(cleaned_abstract)
                    tempObj.append((cleaned_abstract, [col, row[self.IDcol]]))
                
            self.dataObj = tempObj

            #self.dataObj = [tuple(txt,ID) for row in self.dataObj.to_numpy()]
            

        except AttributeError as e:
            print(e)
            print(row[col])

        except FileNotFoundError:
            print('[ERROR] No data and/or input file found in \'mapper/bin/data/\' folder')
        except UnicodeDecodeError as e:
            print(row[0])
            print(e)

    # Gathers information on each match during phrase matching
    def append_match_dict(self,doc):
        for match_id, start, end in self.matcher(doc):
            pattern_type = self.nlp.vocab.strings[match_id]
            matched_word = list(set(self.matches.get(doc._.id, []) + [(pattern_type, str(doc[start:end]))]))
            
            if matched_word in self.false_positives._getall() or matched_word in self.false_positives._getall(acronyms=True):
                continue

            self.matches[doc._.id] = matched_word
            self.id_list.append(str(doc._.id))
            self.col_match_list.append(str(doc._.col))
            self.name_list.append(str(doc[start:end]))

            if end + 10 > len(doc):
                self.context_list.append(str(doc[len(doc)-10:len(doc)]))
            elif start - 10 < 0:
                self.context_list.append(str(doc[0:start+10]))
            else:
                self.context_list.append(str(doc[start-10:end+10]))

            
    # gets metadata of the subreddit document
    def _process_doc(self,batch):
        for TEXT, DATA in self.nlp.pipe(batch, as_tuples=True):
            self.counter += 1
            TEXT._.id = DATA[1]
            TEXT._.col = DATA[0]

            if self.counter % 1000 == 0:
                percentage = round((self.counter/len(self.dataObj))*100)
                print(f'{percentage}%')

            self.append_match_dict(TEXT)

    def _clean_csv(self, df):
        # Creates new columns #DISEASE and #OCCUR
        d = df.value_counts(subset=['ID','Matched_Word']).to_frame()
        n = df.drop_duplicates(['ID', 'Matched_Word']).value_counts(subset=['ID']).to_frame()
        t1 = pd.merge(df,n,on=['ID'])
        t2 = pd.merge(t1,d,on=['ID','Matched_Word'])

        # Adds names for new columns
        t2.columns = ['ID', 'COLUMN', 'Matched_Word', 'CONTEXT', 'GARD_id', '#DISEASE', '#OCCUR']
        t2 = t2[['ID', 'COLUMN', 'Matched_Word', 'CONTEXT', 'GARD_id', '#OCCUR', '#DISEASE']]

        # Saves a version of the file with repeating rows
        t2.to_csv(self._create_path('abstract_matches_w_dupes.csv', input_file=False), index=False)

        # Drops duplicate rows
        t3 = t2.drop_duplicates(['ID','GARD_id','COLUMN'])
        t3['Matched_Word'] = t3['Matched_Word'].str.lower()
        t4 = t3.drop_duplicates(subset=['ID','GARD_id','COLUMN'], keep='first')

        # Calculates weights of matches
        t4['WEIGHT'] = pd.Series()
        t4 = t4.reset_index(drop=True)
        print(t4)

        seen = list()
        r,c = t4.shape
        for num in range(r):
            row = t4.iloc[num]
            ID = row['ID']
            
            COLUMN = row['COLUMN']
            OCCUR = row['#OCCUR']
            DISEASE = row['#DISEASE']
            COL_ORDER = self.cols.index(COLUMN)
            
            WEIGHT = (((100 - int(DISEASE)) - (COL_ORDER*COL_ORDER)) + int(OCCUR))

            row['WEIGHT'] = WEIGHT
            t4.iloc[num] = row

        for idx in range(r):
            row = t4.iloc[idx]
            ID = row['ID']
            if ID in seen:
                continue
            rows = t4.loc[t4['ID'] == ID]
            MAX = int(rows[['WEIGHT']].max())
            MIN = int(rows[['WEIGHT']].min())
        
            for i,entry2 in rows.iterrows():
                
                WEIGHT = entry2['WEIGHT']
                try:
                    Norm_WEIGHT = ((WEIGHT - MIN)/(MAX - MIN))
                except ZeroDivisionError:
                    Norm_WEIGHT = 1

                entry2['WEIGHT'] = Norm_WEIGHT
                t4.iloc[i] = entry2

            seen.append(ID)
        print(t4)    

        # Saves CSV file
        t4.to_csv(self._create_path('abstract_matches.csv', input_file=False), index=False)
        
        # Below lines are just for testing purposes
        df = pd.read_csv(self._create_path('abstract_matches.csv', input_file=False),index_col=False)
        print(df)

    # Starts phrase matching between the input and gard file, uses batching and threading to speed up the process
    def _match(self, inputFile, gardFile, IDcol=False, TEXTcols=False):
        if IDcol:
            self.IDcol = IDcol
        else:
            self.IDcol = 'Application_ID'
        if TEXTcols:
            self.TEXTcols = TEXTcols
        else:
            self.TEXTcols = ['Abstract']
        
        self.cols.extend(self.TEXTcols)
        self.cols.append(self.IDcol)

        self._loadGard(gardFile)
        self._loadData(inputFile)
        self._clean()

        try:
            if self.gardObj == None or self.dataObj == None:
                raise Exception

            # Loads SpaCy package with the custom tokenizer
            self.setup_nlp()
            Doc.set_extension('id', default = None)
            Doc.set_extension('col', default = None)

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
                match_writer.writerow(['ID','COLUMN','Matched_Word','CONTEXT','GARD_id'])
                c = 0
                
                for entry in self.id_list:
                    try:
                        match_writer.writerow([entry, self.col_match_list[c], self.name_list[c], self.context_list[c], self.word_to_gard[self.name_list[c].lower()]])
                        c += 1
                    except KeyError as e:
                        print(e)
                        match_writer.writerow([entry, self.col_match_list[c], self.name_list[c], self.context_list[c]])
                        c += 1
                        continue

            df = pd.read_csv(self._create_path('abstract_matches.csv', input_file=False),index_col=False, encoding='latin-1', error_bad_lines=False)
            df.groupby(['ID', 'Matched_Word']).agg('count')
            self._clean_csv(df)
	
        except KeyError as e:
            print(e)
            match_writer.writerow([entry, self.name_list[c], self.context_list[c]])

        except FileNotFoundError as e:
            print(e)
            print('empty data objects')

    def __del__(self):
        self.dataObj = None
