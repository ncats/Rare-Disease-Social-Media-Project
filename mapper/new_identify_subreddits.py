from Map import *

if __name__ == '__main__':
    #SPEED WITH BRADLEY'S ALGORITHM: 47 mins [REDDIT]
    #SPEED WITH NEW ALGORITHM: APROX 27 mins [REDDIT]
    # ^ just matching part, not displaying results

    #map = RedditMap()
    #map._match('preprocessed_subreddit_list.json','neo4j_rare_disease_list.json')
    #map._display_results()

    #SPEED WITH GRANT'S ALGORITHM: ? mins [ABSTRACTS]
    #SPEED WITH NEW ALGORITHM: APROX 4 mins [ABSTRACTS]
    # ^ just matching part, not displaying results

    map = AbstractMap()
    map._match('10000_grantAbstracts.xlsx','neo4j_rare_disease_list.json')
    
    



