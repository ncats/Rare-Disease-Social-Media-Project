from AbstractMap import AbstractMap

if __name__ == '__main__':
    map = AbstractMap()
    map._match('trials_sample_large.csv','neo4j_rare_disease_list.json', IDcol='NCTId', TEXTcols=['Condition','OfficialTitle','BriefTitle','BriefSummary','Keyword','ArmGroupDescription','DetailedDescription'])
    # 'Condition','OfficialTitle','BriefTitle','BriefSummary','Keyword','ArmGroupDescription','DetailedDescription'
    # Order of list dictates weight