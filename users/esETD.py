from elasticsearch import Elasticsearch
import requests
import pprint
import copy


def indexfun():

    indextypedict = {
        "contributor_author": "<class 'str'>",
        "contributor_committeechair": "<class 'str'>",
        "contributor_committeemember": "<class 'list'>",
        "contributor_department": "<class 'str'>",
        "date_accessioned": "<class 'str'>",
        "date_adate": "<class 'str'>",
        "date_available": "<class 'str'>",
        "date_issued": "<class 'str'>",
        "date_rdate": "<class 'str'>",
        "date_sdate": "<class 'str'>",
        "degree_grantor": "<class 'str'>",
        "degree_level": "<class 'str'>",
        "degree_name": "<class 'str'>",
        "description_abstract": "<class 'str'>",
        "description_provenance": "<class 'list'>",
        "description_degree": "<class 'str'>",
        "format_medium": "<class 'str'>",
        "handle": "<class 'str'>",
        "identifier_other": "<class 'str'>",
        "identifier_sourceurl": "<class 'str'>",
        "identifier_uri": "<class 'str'>",
        "publisher": "<class 'str'>",
        "relation_haspart": "<class 'list'>",
        "rights": "<class 'str'>",
        "subject": "<class 'list'>",
        "title": "<class 'str'>",
        "type": "<class 'str'>",
        "Authoremail": "<class 'list'>",
        "Advisoremail": "<class 'list'>"}

    return indextypedict


class elasticsearchETD:
    def __init__(self):
        try:
            res = requests.get('http://localhost:9200')
            es = Elasticsearch(HOST="http://localhost", PORT=9200)
            self.es = Elasticsearch()
            self.connection = "Successful"
        except:
            self.connection = "Notsuccessful"

    def singlequery(self, whattosearch):

        body = {
            "from": 0,
            "size": 5000,
            "query": {
                "match": {
                    "title": whattosearch["title"]}
            }}

        res = self.es.search(index="etd", body=body)

        totalquerycount = len(res["hits"]["hits"])
        if totalquerycount == 0:
            msg = 0
            output = ["None found"]
        else:
            msg = 1
            output = []
            for arg in res["hits"]["hits"]:
                dum = arg['_source']

                emails = dum["description_provenance"]
                Authoremail = ["mailto:"+element.split()[-1]
                               for idx, element in enumerate(emails) if "Author" in element]
                Advisoremail = ["mailto:"+element.split()[-1]
                                for idx, element in enumerate(emails) if "Advisor" in element]

                del dum["description_provenance"]
                dum["Authoremail"] = Authoremail
                dum["Advisoremail"] = Advisoremail

                emails = dum["description_provenance"]
                output.append(dum)
        return output, msg

    def multiquery(self, whattosearch, date1, date2):

        body = {
            "from": 0,
            "size": 5000,
            "query": {
                "bool": {
                    "must": []
                }
            }
        }

        datesquery = {
            "range": {
                "date_adate": {
                    "gte": date1,
                    "lte": date2
                }
            }
        }

        # body["query"]["bool"]["must"].append(datesquery)

        for arg in whattosearch.keys():
            whatquery = {arg: whattosearch[arg]}
            match = {"match": whatquery}
            body["query"]["bool"]["must"].append(match)

        whatquery = {"description_abstract": whattosearch["title"]}
        match = {"match": whatquery}
        body["query"]["bool"]["should"] = [match]

        # whatquery = {"subject": whattosearch["title"]}
        # match = {"match": whatquery}
        # body["query"]["bool"]["should"].append(match)

        res = self.es.search(index="etd", body=body)

        totalquerycount = len(res["hits"]["hits"])
        if totalquerycount == 0:
            msg = 0
            output = ["None found"]
        else:
            msg = 1
            output = []
            for arg in res["hits"]["hits"]:
                dum = arg['_source']

                emails = dum["description_provenance"]
                Authoremail = ["mailto:"+element.split()[-1]
                               for idx, element in enumerate(emails) if "Author" in element]
                Advisoremail = ["mailto:"+element.split()[-1]
                                for idx, element in enumerate(emails) if "Advisor" in element]

                del dum["description_provenance"]
                dum["Authoremail"] = Authoremail
                dum["Advisoremail"] = Advisoremail

                output.append(dum)
        return output, msg

    def handlequery(self, whattosearch):

        body = {
            "from": 0,
            "size": 1,
            "query": {
                "match": {
                    "handle": whattosearch["handle"]}
            }}

        res = self.es.search(index="etd", body=body)

        totalquerycount = len(res["hits"]["hits"])
        if totalquerycount == 0:
            msg = 0
            output = ["None found"]
        else:
            msg = 1
            output = []
            for arg in res["hits"]["hits"]:
                dum = arg['_source']

                emails = dum["description_provenance"]
                Authoremail = ["mailto:"+element.split()[-1]
                               for idx, element in enumerate(emails) if "Author" in element]
                Advisoremail = ["mailto:"+element.split()[-1]
                                for idx, element in enumerate(emails) if "Advisor" in element]
                del dum["description_provenance"]
                dum["Authoremail"] = Authoremail
                dum["Advisoremail"] = Advisoremail

                output.append(dum)

        return output, msg

    def elasticsearchindex(self, whattoindex):

        storeindex = {}
        indextypedict = indexfun()
        for arg in indextypedict.keys():
            if arg in whattoindex.keys():
                storeindex[arg] = whattoindex[arg]
            else:
                if indextypedict[arg] == "<class 'str'>":
                    storeindex[arg] = "N/A"
                else:
                    storeindex[arg] = []

        storeindex["date_accessioned"] = storeindex['date_issued']+"T18:35:35Z"
        storeindex["date_available"] = storeindex['date_issued']+"T18:35:35Z"
        storeindex["date_adate"] = storeindex['date_issued']
        storeindex["date_issued"] = storeindex['date_issued']
        storeindex["date_rdate"] = storeindex['date_issued']
        storeindex["date_sdate"] = storeindex['date_issued']

        body = {"aggs":
                {"max_id": {
                    "max": {"field": "id"}}
                 }, "size": 1}
        res = self.es.search(index="etd", body=body)

        max_id = res["hits"]["total"]["value"]+1

        self.es.index(index='etd', doc_type='documents',
                      id=max_id, body=storeindex)

        output = ["Uploaded Successful"]
        msg = 1

        return output, msg


def elasticsearchfun(whattosearch, type="allquery"):

    whattosearch = copy.deepcopy(whattosearch)

    esobject = elasticsearchETD()

    if esobject.connection == "Notsuccessful":
        msg = 0
        output = ["Cannot reach ElasticSearch on http://localhost:9200"]
    else:
        msg = 1
        if type == "allquery":
            date1 = whattosearch["date1"]
            date2 = whattosearch["date2"]
            del whattosearch["date1"]
            del whattosearch["date2"]
            output, msg = esobject.multiquery(whattosearch, date1, date2)
        elif type == "handlequery":
            output, msg = esobject.handlequery(whattosearch)
        elif type == "index":
            output, msg = esobject.elasticsearchindex(whattosearch)
        else:
            msg = 0
            output = ["Wrong input type in elasticsearchfun"]

    return output, msg
