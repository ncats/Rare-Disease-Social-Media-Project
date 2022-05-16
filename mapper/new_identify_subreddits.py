from distutils.log import info
from pyparsing import col
from Map import *
import csv
import pandas as pd

if __name__ == '__main__':
    #SPEED WITH BRADLEY'S ALGORITHM: 47 mins [REDDIT]
    #SPEED WITH NEW ALGORITHM: APROX 27 mins [REDDIT]
    # ^ just matching part, not displaying results

    #map = RedditMap()
    #map._match('preprocessed_subreddit_list.json','neo4j_rare_disease_list.json')
    #map._display_results()

    #SPEED WITH GRANT'S ALGORITHM: 2.5 HOUR [ABSTRACTS]
    #SPEED WITH NEW ALGORITHM: APROX 4 mins [ABSTRACTS]
    # ^ just matching part, not displaying results

    map = AbstractMap()
    map._match('10000_grantAbstracts.xlsx','neo4j_rare_disease_list.json')
    
    
    
    '''
    df = pd.read_csv('mapper\\data\\abstract_matches.csv',index_col=False)
    print(df)      
    dfdf = df['Matched_Word'].unique()
    dfdf2 = df['APPLICATION_ID'].unique()
    print(len(dfdf))
    print(len(dfdf2))
    d = df.value_counts(subset=['APPLICATION_ID','Matched_Word']).to_frame()
    n = df.drop_duplicates(['APPLICATION_ID', 'Matched_Word']).value_counts(subset=['APPLICATION_ID']).to_frame()

    t1 = pd.merge(df,n,on=['APPLICATION_ID'])
    t2 = pd.merge(t1,d,on=['APPLICATION_ID','Matched_Word'])
    print(t2)
    t2.columns = ['APPLICATION_ID', 'Abstract', 'Matched_Word', '#DISEASE', '#OCCUR']
    t2 = t2[['APPLICATION_ID', 'Abstract', 'Matched_Word', '#OCCUR', '#DISEASE']]
    t3 = t2.drop_duplicates(['APPLICATION_ID','Matched_Word'])
    #df = pd.read_csv('mapper\\data\\abstract_matches.csv',index_col=False)
    print(t3)'''
    '''
    df = pd.read_csv('mapper\\data\\match_weights.csv',index_col=False)
    t1 = df.loc[df['#DISEASE'] > 1]
    un = t1['APPLICATION_ID'].unique()
    print(len(un))
    print(t1)
    t1.to_csv('mapper\\data\\match_weights_multiple.csv', index=False)
    '''
    '''
    df = pd.read_csv('mapper\\data\\cleaned_abstracts.csv', index_col=False)
    df['APPLICATION_ID'] = df['APPLICATION_ID'].astype('string')
    t = df.to_json(orient='values')
    list = json.loads(t)
    dic = {entry[0] : entry[1] for entry in list}

    with open('10000_grantAbstracts.json', 'w') as outfile:
        json.dump(dic, outfile)'''
    
    '''df = pd.read_csv('mapper\\data\\abstract_matches.csv',index_col=False)
    df['Matched_Word'] = df['Matched_Word'].str.lower()
    df = df.drop_duplicates(subset=['APPLICATION_ID','Matched_Word'], keep='first')
    print(len(df))
    un = df['APPLICATION_ID'].unique()
    print(len(un))'''