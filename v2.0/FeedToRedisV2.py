from redis import Redis
import os
import pandas as pd
import json
import ConfigParser
import datetime

# read the config for redis connection
config = ConfigParser.ConfigParser()
config.read('related-news-engine.conf')
host = config.get('REDIS','HOST')
port = config.get('REDIS','PORT')
password = config.get('REDIS','PASSWORD')
r = Redis(host=host,port=port,db=0,password=password)

DF_CACHE = dict()
def get_facets(r_id,df):
    """
    goal: get the data of r_id in dataframe df
    parameters:
        1. df: target dataframe
        2. r_id: target id
    """
    r_dict = dict()
    if not r_id in DF_CACHE:
        DF_CACHE[r_id] = df[df.id==r_id]
    that_df = DF_CACHE[r_id]
    if len(that_df)!=0:
        r_dict['_id'] = r_id
        r_dict['categories'] = (that_df.category).tolist()[0]
        r_dict['title'] = (that_df.title).tolist()[0]
        r_dict['features'] = (that_df.tags_text).tolist()[0]
        r_dict['slug'] = (that_df.slug).tolist()[0]
        r_dict['heroImage'] = (that_df.heroImage).tolist()[0]
        r_dict['sections'] = (that_df.sections).tolist()[0]
        r_dict['style'] = (that_df['style']).tolist()[0]
        r_dict['href'] = "posts/"+r_id
    else:
        print("bad:",r_id)
    
    return r_dict

def FeedToRedis(r=r,source_dir = "intermediate-results/", input_prefix="related-news-pysparnn",mode="batch"):
    if not mode in ["batch","recent"]:
        print "[Error] the mode is not correct!"
        exit()

    t=time.time() 
    today_stamp=datetime.date.today().strftime("%Y%d%m")
    result_filename = input_prefix+"-"+today_stamp+".result"
    print(result_filename)
    msg_filename = "news-id-tfidf50-topic-category.msg"
    if mode == "recent":
        result_filename = "recent-"+result_filename
        msg_filename = "recent-"+msg_filename

    if os.path.exists(source_dir+result_filename)==True:
        f = open(source_dir+result_filename,'r')
    else:
        print("[Error] Cannot find the latest list of related news. Please run daily_operation.py to get the latest related news")
        exit()

    if os.path.exists(source_dir+msg_filename)==True:
        df = pd.read_msgpack(source_dir+msg_filename)
    else:
        print("[Error] Cannot find the latest metadata of related news. Please run daily_batch.sh to get the latest metadata")
        exit()

    print("Loading the KNN list...")
   
   
    c = 0
    news_dict = dict()
    for line in f:
        news_id,knn_json = line.replace("\n","").split("\t")
        knn_list = json.loads(knn_json)
       
        c+=1
        if c%500==0:
            print(c)
        
        r_news = []
        for (_,r_id) in knn_list:
            r_dict = get_facets(r_id,df)
            r_news.append(r_dict)

        n_dict = get_facets(news_id,df)
        n_dict['knn_list']=knn_list
        n_dict['related_news']=r_news

        news_dict["related-news-v2-"+news_id]= json.dumps(n_dict)

    """
    if you find error msg: MISCONF Redis is configured to save RDB snapshots, 
    try this on redis-cli: config set stop-writes-on-bgsave-error no
    """
    print "Total: "+str(len(news_dict))
    print "Feed all to Redis..."
    r.mset(news_dict)
    print "Done!"
    print(time.time()-t)

if __name__=="__main__":
    import time
    t = time.time()
    FeedToRedis(mode="batch")
    print("spent:"+str(time.time()-t)+"(s)")

