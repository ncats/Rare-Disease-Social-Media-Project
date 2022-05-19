from AbstractMap import AbstractMap
from RedditMap import RedditMap
from FalsePositives import FalsePositives

if __name__ == '__main__':
    map = AbstractMap()
    map._match('10000_grantAbstracts.xlsx','neo4j_rare_disease_list.json')
    
    