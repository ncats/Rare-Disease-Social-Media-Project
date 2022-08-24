from AbstractMap import AbstractMap
#from FalsePositives import FalsePositives

if __name__ == '__main__':
    map = AbstractMap()
    map._match('filtered_abs.txt','neo4j_rare_disease_list.json', IDcol='Application_ID', TEXTcols=['Abstract'])
    # 'Condition','OfficialTitle','BriefTitle','BriefSummary','Keyword','ArmGroupDescription','DetailedDescription'
    # Order of list dictates weight