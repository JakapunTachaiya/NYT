# !/usr/bin/python
import urllib2
import json
import datetime
import time
import sys, os
import logging
from urllib2 import HTTPError
from ConfigParser import SafeConfigParser
import requests
from bs4 import BeautifulSoup



# helper function to iterate through dates
def daterange( start_date, end_date ):
    if start_date <= end_date:
        for n in range( ( end_date - start_date ).days + 1 ):
            yield start_date + datetime.timedelta( n )
    else:
        for n in range( ( start_date - end_date ).days + 1 ):
            yield start_date - datetime.timedelta( n )

# helper function to get json into a form I can work with       
def convert(input):
    if isinstance(input, dict):
        return {convert(key): convert(value) for key, value in input.iteritems()}
    elif isinstance(input, list):
        return [convert(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input

# helpful function to figure out what to name individual JSON files        
def getJsonFileName(date, page, json_file_path):
    json_file_name = ".".join([date,str(page),'json'])
    json_file_name = "".join([json_file_path,json_file_name])
    return json_file_name

def getJsonFileName2(date, page, json_file_path,count):
    json_file_name = ".".join([date,str(page),str(count),'json'])
    json_file_name = "".join([json_file_path,json_file_name])
    return json_file_name


# helpful function for processing keywords, mostly    
def getMultiples(items, key):
    values_list = []
    if len(items) > 0:
        num_keys = 0
        for item in items:
            values_list.append(item[key])
            num_keys += 1

    return values_list

def getMultiplePerson(items,key):
    values_list = []

    if len(items) > 0:
        num_keys = 0
        for item in items[key]:
            if 'firstname' in item:
                first = item["firstname"]

            else:
                first = ""

            if 'lastname' in item:
                last = item["lastname"]
            else:
                last = ""

            tempDict = {'firstname': first, 'lastname': last}
            values_list.append(tempDict)
            # print(values_list)
    return  values_list


    
# get the articles from the NYTimes Article API    
def getArticles(date, query, api_key, json_file_path):
    # LOOP THROUGH THE 101 PAGES NYTIMES ALLOWS FOR THAT DATE
    for page in range(101):
        try:
            request_string = "http://api.nytimes.com/svc/search/v2/articlesearch.json?q=" + query + "&begin_date=" + date + "&end_date=" + date + "&page=" + str(page) + "&api-key=" + api_key
            # request_string = "http://api.nytimes.com/svc/search/v2/articlesearch.json?begin_date=" + date + "&end_date=" + date + "&page=" + str(page) + "&api-key=" + api_key
            response = urllib2.urlopen(request_string)
            content = response.read()
            if content:
                articles = convert(json.loads(content))
                # if there are articles here
                if len(articles["response"]["docs"]) >= 1:
                    json_file_name = getJsonFileName(date, page, json_file_path)
                    json_file = open(json_file_name, 'w')
                    json_file.write(content)
                    json_file.close()
                # if no more articles, go to next date
                else:
                    return
            # else:
            #     break
            time.sleep(3)
        except HTTPError as e:
            logging.error("HTTPError on page %s on %s (err no. %s: %s) Here's the URL of the call: %s", page, date, e.code, e.reason, request_string)
            if e.code == 403:
              logging.info("Quitting. You've probably reached your API limit for the day.")
              sys.exit()
        except: 
            logging.error("Error on %s page %s: %s", date, file_number, sys.exc_info()[0])
            continue

def getFullArticle(web_url):
    print(web_url)

    r = requests.get(web_url, allow_redirects=True)

    if r.url != web_url:
        web_url = r.url
        print("rediect", web_url)
        r = requests.get(web_url, allow_redirects=True)

    soup = BeautifulSoup(r.content, "html.parser")
    # textdata = soup.find_all("p", {"class": "story-content"})

    textdata = soup.find_all("p", {"itemprop": "articleBody"})
    if not textdata:
        textdata = soup.find_all("p", {"class": "story-body-text"})

    fullText = ""
    for item in textdata:
        fullText = fullText+ item.text.strip()

    # print(fullText)



    return fullText


def selectParseArticles(date, output_file_path, json_file_path):

    for file_number in range(101):
        # get the articles and put them into a dictionary
        try:
            file_name = getJsonFileName(date,file_number, json_file_path)
            if os.path.isfile(file_name):
                in_file = open(file_name, 'r')
                articles = convert(json.loads(in_file.read()))
                in_file.close()
            else:
                break
        except IOError as e:
			logging.error("IOError in %s page %s: %s %s", date, file_number, e.errno, e.strerror)
			continue

        # if there are articles in that document, parse them
        if len(articles["response"]["docs"]) >= 1:


            count = 1
            try:
                for article in articles["response"]["docs"]:
                    # print("test")
                    file_name = getJsonFileName2(date,file_number, output_file_path,count)
                    # print(file_name)
                    out_file = open(file_name, 'w')

                    count+=1
                    tmpDict ={}

                    # if (article["source"] == "The New York Times" and article["document_type"] == "article"):
                    keywords = ""
                    keywords = getMultiples(article["keywords"],"value")

                    tmpDict["pub_date"] = article["pub_date"]
                    tmpDict["headline"] =  str(article["headline"]["main"]).decode("utf8").replace("\n","") if "main" in article["headline"].keys() else ""
                    tmpDict['keywords'] = keywords

                    tmpDict["document_type"] =  str(article["document_type"]).decode("utf8") if "document_type" in article.keys() else ""
                    tmpDict["source"] = str(article["source"]).decode("utf8") if "source" in article.keys() else ""

                    if article["byline"] is not None:
                        author = getMultiplePerson(article["byline"],"person")

                        tmpDict["author"] = author
                    else:
                        tmpDict["author"] = None

                    # print(tmpDict)


                    tmpDict["snippet"] = str(article["snippet"]).decode("utf8").replace("\n","") if "snippet" in article.keys() else "",
                    tmpDict["lead_paragraph"] = str(article["lead_paragraph"]).decode("utf8").replace("\n","") if "lead_paragraph" in article.keys() else "",

                    web_url = article["web_url"] if "web_url" in article.keys() else ""
                    tmpDict["web_url"] =web_url


                    # print(web_url)
                    full_article = getFullArticle(web_url)
                    # print(full_article.encode('utf8'))
                    tmpDict['full_article'] = full_article


                    if tmpDict['full_article'] != "":
                        tmpDict = json.dumps(tmpDict,indent=4,ensure_ascii=False).encode('utf8')
                        out_file.write(tmpDict)

                    out_file.close()
                    # print("a")

                    # out_file.write(line.encode("utf8")+"\n")


            except KeyError as e:
                logging.error("KeyError in %s page %s: %s %s", date, file_number, e.errno, e.strerror)
                continue
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                logging.error("Error on %s page %s: %s", date, file_number, sys.exc_info()[0])
                continue


        else:
            break

    return


# parse the JSON files you stored into a tab-delimited file
def parseArticles(date, tsv_file_name, json_file_path):

    for file_number in range(101):
        # get the articles and put them into a dictionary
        try:
            file_name = getJsonFileName(date,file_number, json_file_path)
            if os.path.isfile(file_name):
                in_file = open(file_name, 'r')
                articles = convert(json.loads(in_file.read()))
                in_file.close()
            else:
                break
        except IOError as e:
			logging.error("IOError in %s page %s: %s %s", date, file_number, e.errno, e.strerror)
			continue
        
        # if there are articles in that document, parse them
        if len(articles["response"]["docs"]) >= 1:  

            # open the tsv for appending
            try:
                out_file = open(tsv_file_name, 'ab')

            except IOError as e:
    			logging.error("IOError: %s %s %s %s", date, file_number, e.errno, e.strerror)
    			continue
        
            # loop through the articles putting what we need in a tsv   
            try:
                for article in articles["response"]["docs"]:
                    # if (article["source"] == "The New York Times" and article["document_type"] == "article"):
                    keywords = ""
                    keywords = getMultiples(article["keywords"],"value")
    
                    # should probably pull these if/else checks into a module
                    variables = [
                        article["pub_date"], 
                        keywords, 
                        str(article["headline"]["main"]).decode("utf8").replace("\n","") if "main" in article["headline"].keys() else "", 
                        str(article["source"]).decode("utf8") if "source" in article.keys() else "", 
                        str(article["document_type"]).decode("utf8") if "document_type" in article.keys() else "", 
                        article["web_url"] if "web_url" in article.keys() else "",
                        str(article["news_desk"]).decode("utf8") if "news_desk" in article.keys() else "",
                        str(article["section_name"]).decode("utf8") if "section_name" in article.keys() else "",
                        str(article["snippet"]).decode("utf8").replace("\n","") if "snippet" in article.keys() else "",
                        str(article["lead_paragraph"]).decode("utf8").replace("\n","") if "lead_paragraph" in article.keys() else "",
                        ]
                    line = "\t".join(variables)
                    print(line)
                    out_file.write(line.encode("utf8")+"\n")
            except KeyError as e:
                logging.error("KeyError in %s page %s: %s %s", date, file_number, e.errno, e.strerror)
                continue
            except (KeyboardInterrupt, SystemExit):
                raise
            except: 
                logging.error("Error on %s page %s: %s", date, file_number, sys.exc_info()[0])
                continue
        
            out_file.close()
        else:
            break
        
# Main function where stuff gets done

def main():
    
    config = SafeConfigParser()
    script_dir = os.path.dirname(__file__)
    config_file = os.path.join(script_dir, 'config/settings.cfg')
    config.read(config_file)
    
    json_file_path = config.get('files','api_json_folder')
    output_file_path = config.get('files','full_json_folder')
    tsv_file_name = config.get('files','tsv_file')
    log_file = config.get('files','logfile')
    
    api_key = config.get('nytimes','api_key')    
    start = datetime.date( year = int(config.get('nytimes','start_year')), month = int(config.get('nytimes','start_month')), day = int(config.get('nytimes','start_day')) )
    end = datetime.date( year = int(config.get('nytimes','end_year')), month = int(config.get('nytimes','end_month')), day = int(config.get('nytimes','end_day')) )
    query = config.get('nytimes','query')
        
    logging.basicConfig(filename=log_file, level=logging.INFO)
    
    logging.info("Getting started.") 
    try:
        # LOOP THROUGH THE SPECIFIED DATES
        for date in daterange( start, end ):
            date = date.strftime("%Y%m%d")
            logging.info("Working on %s." % date)
            # print("request ",query," at ",date)
            try:
                getArticles(date, query, api_key, json_file_path)
                # parseArticles(date, tsv_file_name, json_file_path)
                selectParseArticles(date, output_file_path, json_file_path)
            except:
                logging.error("Unexpected error: %s", str(sys.exc_info()[0]))
                pass
    except:
        logging.error("Unexpected error: %s", str(sys.exc_info()[0]))
    finally:
        logging.info("Finished.")

if __name__ == '__main__' :
    main()
    
