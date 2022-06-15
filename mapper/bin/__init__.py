from AbstractMap import AbstractMap
from RedditMap import RedditMap

if __name__ == '__main__':
    map = AbstractMap()
    map._match('filtered_abs.txt','neo4j_rare_disease_list.json')
    
    