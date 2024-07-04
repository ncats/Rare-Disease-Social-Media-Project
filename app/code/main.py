from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, BaseSettings
from typing import List
from top2vec import Top2Vec
import numpy as np
import requests

#Make a dictionary of all subreddits : urls
repository = "ncats/Rare-Disease-Social-Media-Project"
url = "https://api.github.com/repos/{repository}/git/trees/main?recursive=1".format(repository=repository)
response = requests.get(url,timeout=5).json()
for entry in response['tree']:
  if entry['path'] == 'project_data/models':
    models_url = entry['url']
response = requests.get(models_url,timeout=5).json()
subreddits_urls = {entry['path'] : entry['url'] for entry in response['tree']}

subreddit_choice = "scleroderma"
response = requests.get(subreddits_urls[subreddit_choice],timeout=5).json()
subreddits_models = {entry['path'] : entry['url'] for entry in response['tree'] if "." not in entry['path']}
model_choice = "scleroderma_paraphrase-multilingual-MiniLM-L12-v2"

raw = "https://github.com/ncats/Rare-Disease-Social-Media-Project/raw/main/project_data/models/{subreddit_choice}/{model_choice}".format(subreddit_choice,model_choice)
response = requests.get(raw,timeout=30)
with open(model_choice, 'wb') as f:
    f.write(response.content)

topic_model = Top2Vec.load(model_choice)

class Settings(BaseSettings):
    model_name: str = "Top2Vec API"
    
settings = Settings()

app = FastAPI(title="Rare Disease Social Media Topic Models",
              description="RESTful Top2Vec API",
              version="1.0.0", )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=404,
        content={"message": str(exc)},
    )

# determine top2vec index type
if top2vec.doc_id_type is np.str_:
    doc_id_type = str
else:
    doc_id_type = int

# determine if model has documents
if top2vec.documents is None:
    has_documents = False
else:
    has_documents = True


class Document(BaseModel):
    if has_documents:
        content: str
    score: float
    doc_id: doc_id_type


class DocumentSearch(BaseModel):
    doc_ids: List[doc_id_type]
    doc_ids_neg: List[doc_id_type]
    num_docs: int


class NumTopics(BaseModel):
    num_topics: int


class TopicSizes(BaseModel):
    topic_nums: List[int]
    topic_sizes: List[int]


class Topic(BaseModel):
    topic_num: int
    topic_words: List[str]
    word_scores: List[float]


class TopicResult(Topic):
    topic_score: float


class KeywordSearch(BaseModel):
    keywords: List[str]
    keywords_neg: List[str]


class KeywordSearchDocument(KeywordSearch):
    num_docs: int


class KeywordSearchTopic(KeywordSearch):
    num_topics: int


class KeywordSearchWord(KeywordSearch):
    num_words: int


class WordResult(BaseModel):
    word: str
    score: float


@app.get("/topics/number", response_model=NumTopics, description="Returns number of topics in the model.",
         tags=["Topics"])
async def get_number_of_topics():
    return NumTopics(num_topics=top2vec.get_num_topics())


@app.get("/topics/sizes", response_model=TopicSizes, description="Returns the number of documents in each topic.",
         tags=["Topics"])
async def get_topic_sizes():
    topic_sizes, topic_nums = top2vec.get_topic_sizes()
    return TopicSizes(topic_nums=list(topic_nums), topic_sizes=list(topic_sizes))


@app.get("/topics/get-topics", response_model=List[Topic], description="Get number of topics.", tags=["Topics"])
async def get_topics(num_topics: int):
    topic_words, word_scores, topic_nums = top2vec.get_topics(num_topics)

    topics = []
    for words, scores, num in zip(topic_words, word_scores, topic_nums):
        topics.append(Topic(topic_num=num, topic_words=list(words), word_scores=list(scores)))

    return topics


@app.post("/topics/search", response_model=List[TopicResult], description="Semantic search of topics using keywords.",
          tags=["Topics"])
async def search_topics_by_keywords(keyword_search: KeywordSearchTopic):
    topic_words, word_scores, topic_scores, topic_nums = top2vec.search_topics(keyword_search.keywords,
                                                                               keyword_search.num_topics,
                                                                               keyword_search.keywords_neg)

    topic_results = []
    for words, word_scores, topic_score, topic_num in zip(topic_words, word_scores, topic_scores, topic_nums):
        topic_results.append(TopicResult(topic_num=topic_num, topic_words=list(words),
                                         word_scores=list(word_scores), topic_score=topic_score))

    return topic_results


@app.get("/documents/search-by-topic", response_model=List[Document],
         description="Semantic search of documents using keywords.", tags=["Documents"])
async def search_documents_by_topic(topic_num: int, num_docs: int):
    documents = []

    if has_documents:
        docs, doc_scores, doc_ids = top2vec.search_documents_by_topic(topic_num, num_docs)
        for doc, score, num in zip(docs, doc_scores, doc_ids):
            documents.append(Document(content=doc, score=score, doc_id=num))

    else:
        doc_scores, doc_ids = top2vec.search_documents_by_topic(topic_num, num_docs)
        for score, num in zip(doc_scores, doc_ids):
            documents.append(Document(score=score, doc_id=num))

    return documents


@app.post("/documents/search-by-keywords", response_model=List[Document], description="Search documents by keywords.",
          tags=["Documents"])
async def search_documents_by_keywords(keyword_search: KeywordSearchDocument):
    documents = []

    if has_documents:
        docs, doc_scores, doc_ids = top2vec.search_documents_by_keywords(keyword_search.keywords,
                                                                         keyword_search.num_docs,
                                                                         keyword_search.keywords_neg)
        for doc, score, num in zip(docs, doc_scores, doc_ids):
            documents.append(Document(content=doc, score=score, doc_id=num))
    else:
        doc_scores, doc_ids = top2vec.search_documents_by_keywords(keyword_search.keywords,
                                                                   keyword_search.num_docs,
                                                                   keyword_search.keywords_neg)
        for score, num in zip(doc_scores, doc_ids):
            documents.append(Document(score=score, doc_id=num))

    return documents


@app.post("/documents/search-by-documents", response_model=List[Document], description="Find similar documents.",
          tags=["Documents"])
async def search_documents_by_documents(document_search: DocumentSearch):
    documents = []

    if has_documents:
        docs, doc_scores, doc_ids = top2vec.search_documents_by_documents(document_search.doc_ids,
                                                                          document_search.num_docs,
                                                                          document_search.doc_ids_neg)
        for doc, score, num in zip(docs, doc_scores, doc_ids):
            documents.append(Document(content=doc, score=score, doc_id=num))
    else:
        doc_scores, doc_ids = top2vec.search_documents_by_documents(document_search.doc_ids,
                                                                    document_search.num_docs,
                                                                    document_search.doc_ids_neg)
        for score, num in zip(doc_scores, doc_ids):
            documents.append(Document(score=score, doc_id=num))

    return documents


@app.post("/words/find-similar", response_model=List[WordResult], description="Search documents by keywords.",
          tags=["Words"])
async def find_similar_words(keyword_search: KeywordSearchWord):
    words, word_scores = top2vec.similar_words(keyword_search.keywords, keyword_search.num_words,
                                               keyword_search.keywords_neg)

    word_results = []
    for word, score in zip(words, word_scores):
        word_results.append(WordResult(word=word, score=score))

    return word_results