from bs4 import BeautifulSoup
import urllib.request
import re
from multiprocessing.dummy import Pool as ThreadPool
from multiprocessing import Process, Lock
import json
import os


OUTPUT_DIRECTORY = "D:/CS221-Data/Readme/"
GITHUB_URL = "https://github.com/"

def writeNotFound(notFoundList):
    with open("notFound.txt", "w+", encoding="utf-8") as writeIn:
        for item in notFoundList:
            writeIn.write(item + "\n")


def getRepos():
    repos = []
    with open("common_stuff/project_to_score.txt") as repoNames:
        header = repoNames.readline()
        for line in repoNames.readlines():
            name, score = line.split('\t')
            repos.append(name)
    return repos

def readReadMe(url, fileHeader, r):
    with open (OUTPUT_DIRECTORY+fileHeader.replace('/','_') + ".txt", 'w') as output:
        html = urllib.request.urlopen(url)
        soup = BeautifulSoup(html, 'html.parser')
        contents = soup.find('div', class_='file')
        readme = contents.find('div', id='readme')
        if (readme == None): print (url)
        else:
            output.write(readme.get_text())
        output.close()

def getURLFrom(repoName, regex, lock, provenToNotExist):
    #GET /repos/:owner/:repo/readme
    #https://api.github.com/repos/+repoName
    url = GITHUB_URL +repoName#+'/readme'
    html = urllib.request.urlopen(url)
    #print (html)
    #input()
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find_all('table', class_ = "files js-navigation-container js-active-navigation-container")
    assert (len(table) == 1)
    items = table[0].find_all('tr', class_=r"js-navigation-item")
    foundReadme = False
    for item in items:
        content = item.find('td', class_="content")
        if re.search(regex, content.get_text()):
            foundReadme = True
            link = content.find('a')['href']
            lock.acquire()
            print (link)
            lock.release()
            readReadMe(GITHUB_URL + link, repoName, regex)
    if not foundReadme:
        lock.acquire()
        provenToNotExist.append(repoName)
        print (url + str( " has no Readme"))
        lock.release()

repos = getRepos()
computableRepos = []
finishedRepos = set(os.listdir(OUTPUT_DIRECTORY))

#Avoid rereading already read files
for repo in repos:
    if (repo.replace('/','_') + ".txt" in finishedRepos):
        continue
    computableRepos.append(repo)

#Contains items to retry
lock = Lock()
retryQueue = {}
provenToNotExist = []
count = {}
count["c"] = 0

def downloadFromRepo(repo):
    #Handles failures
    try:
        lock.acquire()
        count["c"] += 1
        if count["c"] % 80 == 0:
            writeNotFound(provenToNotExist)
        lock.release()
        getURLFrom(repo, r"README\..*", lock, provenToNotExist)
        
    except Exception as e:
        lock.acquire()
        print("Failed on" + repo)
        print(e)
        lock.release()
        retryQueue[repo] = 3

pool = ThreadPool(100)
results = pool.map(downloadFromRepo, computableRepos)
pool.close()
pool.join()


#Handles all items that were not succesfully queried
unavailable = []
#While the dictionary is not empty
while retryQueue:
    for repo, numRetries in retryQueue.items():
        try:
            getURLFrom(repo, r"README\..*", lock)
        except:
            retryQueue[repo] -=1

            # If the retries run out the project may have been removed
            if retryQueue[repo] <= 0:
                unavailable.append(retryQueue.pop(repo))

writeNotFound(provenToNotExist)
#Save the non working items
with open("failed-Readme-requests.txt", "w+", encoding="utf-8") as writeIn:
    for item in unavailable:
        writeIn.write(item + '\n')

def readNotFound(allReposList):
    with open("notFound.txt", "r", encoding="utf-8") as readIn:
        for readable in readIn:
            allReposList.remove(readable)