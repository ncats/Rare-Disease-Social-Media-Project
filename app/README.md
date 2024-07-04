This will host the FastAPI app used to explore the topic models. Written with Python, PHP, Javascript and containerized with Docker.

This is supposed to be an app based on this:
https://github.com/ddangelov/RESTful-Top2Vec/blob/master/restful-top2vec/app/main.py
with this as the base of the front end:
https://huggingface.co/spaces/SpacesExamples/fastapi_t5
with some drop down menus from:
https://www.w3schools.com/howto/howto_js_dropdown.asp

First time doing real javascript!

### Notes: 
I deleted 
```
ENV model_name="Top2Vec API"
ENV model_path=/app/top2vec_model
```
from dockerfile, need to update the main.py file to download the models using request first then load them in the app.