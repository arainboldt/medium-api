"""
It's the interface module of the package. Developers will start
interacting with the API/package using `Medium` Class object via 
different functions provided in it.
"""

import time
import re
from urllib.parse import urlparse
from http.client import HTTPSConnection
from ujson import loads
from concurrent.futures import ThreadPoolExecutor, as_completed

from medium_api._topfeeds import TopFeeds
from medium_api._user import User
from medium_api._article import Article
from medium_api._publication import Publication
from medium_api._top_writers import TopWriters
from medium_api._latestposts import LatestPosts
from async_mixin.mixin import AsyncHttpMixin
from typing import Union, List
import asyncio

class MediumClient(AsyncHttpMixin):
    """Main Medium API Class to access everything

        Typical usage example:

        ``from medium_api import Medium``

        ``medium = Medium('YOUR_RAPIDAPI_KEY')``

    Args:
        rapidapi_key (str): A secret alphanumeric string value. To get your 
            RapidAPI key, please go to the following URL, register an account 
            and subscribe to Medium API (by Nishu Jain).

            https://rapidapi.com/nishujain199719-vgIfuFHZxVZ/api/medium2

        base_url (str, optional): It's the base URL of the API that is used by
            all the other endpoints. Currently, it is set to the RapidAPI's 
            domain (medium2.p.rapidapi.com). May change in the future according
            to where it's listed.

        calls (int, optional): It's an integer value for keeping track of all the
            API calls made by the Medium Class Object. Initially, it is set to 0.
            At the end of program, you can see the number of calls like this:

            ``print(medium.calls)``

    Returns:
        Medium: A `Medium` Class Object for the given *RAPIDAPI_KEY*. It can be
        used to access all the other functions such as: `user`, `article`, 
        `publication`, `topfeeds`, `top_writers`, etc ... 

    Note:
        See https://docs.rapidapi.com/docs/keys to learn more about RapidAPI keys.

    """
    base_url = 'medium2.p.rapidapi.com'
    def __init__(self, 
                 rapidapi_key:str, 
                 calls:int=0,
                 n: int = 100,
                 p: int = 60,
                 ):
        super(MediumClient, self).__init__()
        self.headers = {
            'X-RapidAPI-Key': rapidapi_key,
            "X-RapidAPI-Host": "medium2.p.rapidapi.com",
            'User-Agent': f"medium-api-python-sdk"
        }
        self.set_rate_limit(n=n, p=p)
        self.call_count_key = 'x-amzn-requestid'
        self.call_count_limit_key = 'X-RateLimit-All-endpoints-Limit'
        self.call_limit_remaining_key = 'X-RateLimit-All-endpoints-Remaining'
        self.call_counts = None
        self.call_count_limit = None
        self.remaining_calls = None

    def __get_resp(self, endpoint:str, retries:int=0):
        conn = HTTPSConnection(self.base_url)
        conn.request('GET', endpoint, headers=self.headers)
        resp = conn.getresponse()

        data = resp.read()
        status = resp.status
        
        if status == 200:
            self.calls += 1
            json_data = loads(data)

            if not 'error' in json_data.keys():
                return json_data, status
            else:
                if retries < 3:
                    time.sleep(5)
                    return self.__get_resp(endpoint=endpoint, retries=retries+1)
                else:
                    print(f'[ERROR]: Response: {json_data}')
                    return {}, status
        else:
            print(f'[ERROR]: Status Code: {status}')
            print(f'[ERROR]: Response: {data}')
            return {}, status

    def user(self, username:str = None, user_id:str = None, save_info:bool = True):
        """For getting the Medium User Object

            Typical usage example:

            ``nishu = medium.user(username="nishu-jain")``

        Args:
            username (str, optional): It's your unique Medium username that
                you can find in the subdomain or at the end of the profile page
                URL as shown below.

                - ``username``.medium.com
                - medium.com/@ ``username``

                It's optional only if you've already provided the `user_id`.

            user_id (str, optional): It's your unique alphanumeric Medium ID that 
                cannot be changed. The User object is initialized using this only. 
                It's optional only if you've already provided the `username`.

            save_info (bool, optional): If `False`, creates an empty `User` object which
                needs to be filled using ``user.save_info()`` method later. (Default is 
                `True`)

        Returns:
            User: Medium API's User Object (medium_api.user.User) that can be used 
            to access all the properties and methods associated to the given Medium
            user.

        Note:
            You have to provide either `username` or `user_id` to get the User object. You
            cannot omit both. 
        """
        if user_id is not None:
            return User(user_id = user_id, 
                        get_resp = self.__get_resp, 
                        fetch_articles=self.fetch_articles,
                        fetch_users=self.fetch_users,
                        save_info = save_info)
        elif username is not None:
            resp, _ = self.__get_resp(f'/user/id_for/{str(username)}')
            user_id = resp['id']
            return User(user_id = user_id, 
                        get_resp = self.__get_resp, 
                        fetch_articles=self.fetch_articles,
                        fetch_users=self.fetch_users,
                        save_info = save_info)
        else:
            print('[ERROR]: Missing parameter: Please provide "user_id" or "username" to call the function')
            return None

    def users(self, username: Union[str,List[str]] = None, user_id: Union[str,List[str]] = None, save_info:bool = True):
        """For getting the Medium User Object(s): Async retrieval when list of usernames or user_ids are passed

            Typical usage example:

            ``nishu = medium.user(username="nishu-jain")``

        Args:
            username (str, optional): It's your unique Medium username that
                you can find in the subdomain or at the end of the profile page
                URL as shown below.

                - ``username``.medium.com
                - medium.com/@ ``username``

                It's optional only if you've already provided the `user_id`.

            user_id (str, optional): It's your unique alphanumeric Medium ID that 
                cannot be changed. The User object is initialized using this only. 
                It's optional only if you've already provided the `username`.

            save_info (bool, optional): If `False`, creates an empty `User` object which
                needs to be filled using ``user.save_info()`` method later. (Default is 
                `True`)

        Returns:
            User: Medium API's User Object (medium_api.user.User) that can be used 
            to access all the properties and methods associated to the given Medium
            user.

        Note:
            You have to provide either `username` or `user_id` to get the User object. You
            cannot omit both. 
        """
        assert (username is not None) or (user_id is not None), 'You have to provide either `username` or `user_id`' \
                                                                'to get the User object. You cannot omit both. '

        if user_id is not None:
            return User(user_id = user_id, 
                        get_resp = self.__get_resp, 
                        fetch_articles=self.fetch_articles,
                        fetch_users=self.fetch_users,
                        save_info = save_info)
        elif username is not None:
            resp, _ = self.__get_resp(f'/user/id_for/{str(username)}')
            user_id = resp['id']
            return User(user_id = user_id, 
                        get_resp = self.__get_resp, 
                        fetch_articles=self.fetch_articles,
                        fetch_users=self.fetch_users,
                        save_info = save_info)
        else:
            print('[ERROR]: Missing parameter: Please provide "user_id" or "username" to call the function')
            return None

    def article(self, article_id:str, save_info:bool = True):
        """For getting the Medium Article Object

            Typical usage example:

            ``article = medium.article(article_id = "562c5821b5f0")``

        Args:
            article_id (str): It's the unique hash at the end of every Medium Article.
                You can see it at the end of URL as shown below:

                - https://nishu-jain.medium.com/about-me-nishu-jain-562c5821b5f0

            save_info (bool, optional): If `False`, creates an empty `Article` object which
                needs to be filled using ``article.save_info()`` method later. (Default is 
                `True`)

        Returns:
            Article: Medium API `Article` Object (medium_api.article.Article) that can be
            used to access all the properties and methods related to a Medium Article.

        """
        return Article(article_id = article_id, 
                       get_resp = self.__get_resp, 
                       fetch_articles=self.fetch_articles,
                       fetch_users = self.fetch_users,
                       save_info = save_info)

    def publication(self, publication_slug:str = None, publication_id:str = None, save_info:bool = True):
        """For getting the Medium Publication Object

            Typical usage example:

            ``publication = medium.publication(publication_slug = "towards-artificial-intelligence")``
            ``publication = medium.publication(publication_id = "98111c9905da")``

        Args:
            publication_slug (str, optional): It's a lowercased hyphen-separated unique string 
                alloted to each Medium Publication. It's optional only if you've already provided 
                the `publication_id`.

            publication_id (str, optional): It's the unique hash id of a Medium Publication. 
                It's optional only if you've already provided the `publication_slug`.

            save_info (bool, optional): If `False`, creates an empty `Publication` object which
                needs to be filled using ``publication.save_info()`` method later. (Default is 
                `True`)

        Returns:
            Publication: Medium API `Publication` Object (medium_api.publication.Publication) 
            that can be used to access all the properties and methods related to a Medium 
            Publication.

        Note:
            You have to provide either `publication_slug` or `publication_id` to get the Publication object. 
            You cannot omit both. 

        """
        if publication_id is not None:
            return Publication(publication_id = publication_id, 
                        get_resp = self.__get_resp, 
                        fetch_articles=self.fetch_articles,
                        fetch_users=self.fetch_users,
                        save_info = save_info)

        elif publication_slug is not None:
            resp, _ = self.__get_resp(f'/publication/id_for/{str(publication_slug)}')
            publication_id = resp['publication_id']
            return Publication(publication_id = publication_id, 
                        get_resp = self.__get_resp, 
                        fetch_articles=self.fetch_articles,
                        fetch_users=self.fetch_users,
                        save_info = save_info)
        else:
            print('[ERROR]: Missing parameter: Please provide "publication_id" or "publication_slug" to call this function')
            return None

    def top_writers(self, topic_slug:str):
        """For getting the Medium's TopWriters Object

            Typical usage example:

            ``top_writers = medium.top_writers(topic_slug = "artificial-intelligence")``

        Args:
            topic_slug (str): It's a string (smallcase, hyphen-separated) which specifies
                a category/niche as classified by the Medium Platform.

        Returns:
            TopWriters: Medium API `TopWriters` Object (medium_api.top_writers.TopWriters) 
            that can be used to access all the properties and methods related to Medium's 
            Top Writers for the give `topic_slug`.

        """
        return TopWriters(topic_slug=topic_slug, 
                          get_resp=self.__get_resp, 
                          fetch_users=self.fetch_users,
                          fetch_articles=self.fetch_articles)

    def latestposts(self, topic_slug:str):
        """For getting the Medium's LatestPosts Object

            Typical usage example:

            ``latestposts = medium.latestposts(topic_slug = "artificial-intelligence")``

        Args:
            topic_slug (str): It's a string (smallcase, hyphen-separated) which specifies
                a category/niche as classified by the Medium Platform.

        Returns:
            LatestPosts: Medium API `LatestPosts` Object (medium_api.latestposts.LatestPosts) 
            that can be used to access all the properties and methods related to Medium's 
            LatestPosts within the given topic.

        """
        return LatestPosts(topic_slug=topic_slug, 
                           get_resp=self.__get_resp, 
                           fetch_articles=self.fetch_articles,
                           fetch_users=self.fetch_users,
                        )

    def topfeeds(self, tag:str, mode:str):
        """For getting the Medium's TopFeeds Object

            Typical usage example:

            ``topfeeds = medium.topfeeds(tag="blockchain", mode="new")``

        Args:
            tag (str): It's a string (smallcase, hyphen-separated) which specifies
                a category/niche as classified by the Medium Platform.

            mode (str): There are 6 modes as follows:

                    - ``hot``: For getting trending articles
                    - ``new``: For getting latest articles
                    - ``top_year``: For getting best articles of the year
                    - ``top_month``: For getting best articles of the month
                    - ``top_week``: For getting best articles of the week
                    - ``top_all_time``: For getting best article of all time


        Returns:
            TopFeeds: Medium API `TopFeeds` Object (medium_api.topfeeds.TopFeeds) 
            that can be used to access all the properties and methods, for given `tag` 
            and `mode`.

        """
        return TopFeeds(tag=tag, mode=mode, 
                        get_resp=self.__get_resp, 
                        fetch_articles=self.fetch_articles,
                        fetch_users=self.fetch_users)

    def related_tags(self, given_tag:str):
        """For getting the list of related tags

            Typical usage example:

            ``related_tags = medium.related_tag(given_tag="blockchain")``

        Args:
            given_tag (str): It's a string (smallcase, hyphen-separated) which specifies
                             a category/niche as classified by the Medium Platform.

        Returns:
            list[str]: List of Related Tags (strings).

        """
        resp, _ = self.__get_resp(f'/related_tags/{given_tag}')

        return resp['related_tags']

    def fetch_articles(self, articles:list, content:bool = False):
        """To quickly fetch articles (info and content) using multithreading

            Typical usage example:

            ``medium.fetch_articles(latestposts.articles)``
            ``medium.fetch_articles(user.articles)``
            ``medium.fetch_articles(list_of_articles_obj)``

        Args:

            articles (list[Article]): List of (empty) Article objects to fill information 
                (and content) into it.

            content(bool, optional): Set it to `True` if you want to fetch the content of 
                the article as well. Otherwise, default is `False`

        Returns:
            None: This method doesn't return anything since it fills the values in the passed
            list of Article(s) objects itself.

        """
        with ThreadPoolExecutor(max_workers=100) as executor:
            future_to_url = [executor.submit(article.save_info) for article in articles if article.title is None]
            if content:
                future_to_url += [executor.submit(article.save_content) for article in articles]

            for future in as_completed(future_to_url):
                future.result()

    def fetch_users(self, users:list):
        """To quickly fetch users info using multithreading

            Typical usage example:

            ``medium.fetch_users(top_writers.users)``
            ``medium.fetch_users(list_of_users_obj)``

        Args:

            users (list[User]): List of (empty) User objects to fill information into it.

        Returns:
            None: This method doesn't return anything since it fills the values into the 
            passed list of User(s) objects itself.

        """
        with ThreadPoolExecutor(max_workers=100) as executor:
            future_to_url = (executor.submit(user.save_info) for user in users if user.fullname is None)

            for future in as_completed(future_to_url):
                future.result()

    def extract_article_id(self, article_url:str):
        """To get `article_id` from the Article's URL

            Usage example:

            ``article_id = medium.get_article_id("https://nishu-jain.medium.com/about-me-nishu-jain-562c5821b5f0")``

        Args:

            article_url (str): URL as string type

        Returns:
            str: Returns `article_id` as string for valid URL, else returns `None`.

        """
        regex = r'(https?://[^\s]+)'
        urls = re.findall(regex, article_url)

        if urls:
            urlpath = urlparse(urls[0]).path
            if urlpath:
                last_location = urlpath.split('/')[-1]
                article_id = last_location.split('-')[-1]

                if article_id.isalnum():
                    return article_id

        return None

    # A Sink Below:

    def get_urls(self, endpoint, key, args):
        return list(map(lambda x: 'https://' + self.base_url + x[0].format(**{key:x[1]}), 
                        zip([endpoint]*len(args), args)))

    #user ids
    def users_id(self, username: Union[str,List[str]] = None):
        """For getting the Medium User Object(s): Async retrieval when list of usernames or user_ids are passed

        Args:
            username (str, optional): It's your unique Medium username that
                you can find in the subdomain or at the end of the profile page
                URL as shown below.

                - ``username``.medium.com
                - medium.com/@ ``username``


        Returns: List of User ids

        """
        if not isinstance(username, list):
            username = [username]

        user_id_urls = self.get_urls(endpoint='/user/id_for/{username}', 
                                 key='username', 
                                 args=username)    
        user_ids_res = self.pipeline(method=self.process_gets, 
                                 args=user_id_urls)
        if user_ids_res:
            return dict(zip(username, user_ids_res))


    # users' info
    def users_info(self, username: Union[str,List[str]] = None, user_id: Union[str,List[str]] = None,):
        assert (username is not None) or (user_id is not None), 'You have to provide either `username` or `user_id`'\
                                                                'to get the User object. You cannot omit both. '
        if user_id is None:
            if not isinstance(username, list):
                username = [username]
            user_id = self.users_id(username=username)
        else:
            if not isinstance(user_id, list):
                user_id = [user_id] 

        
        user_info_urls = self.get_urls(endpoint='/user/{user_id}', 
                                       key='user_id', 
                                       args=user_id)    
        user_info_res = self.pipeline(method=self.process_gets, 
                                 args=user_info_urls)
        if user_info_res:
            return dict(zip(user_id, user_info_res))

    # users' following
    # users' followers 
    # users' articles
    def user_articles(self, username: Union[str,List[str]] = None, user_id: Union[str,List[str]] = None,):
        assert (username is not None) or (user_id is not None), 'You have to provide either `username` or `user_id`'\
                                                                'to get the User object. You cannot omit both. '
        if user_id is None:
            if not isinstance(username, list):
                username = [username]
            user_id = self.users_id(username=username)
        else:
            if not isinstance(user_id, list):
                user_id = [user_id] 

        
        user_article_urls = self.get_urls(endpoint='/user/{user_id}/articles', 
                                       key='user_id', 
                                       args=user_id)    
        user_article_res = self.pipeline(method=self.process_gets, 
                                         args=user_article_urls)
        if user_article_res:
            return dict(zip(user_id, user_article_res))



    # users' top articles
    # users' interests
    # articles' info
    def article_info(self, article_id: Union[str,List[str]]):
        if not isinstance(article_id, list):
            article_id = [article_id]
        article_info_urls = self.get_urls(endpoint='/article/{article_id}', 
                                       key='article_id', 
                                       args=article_id)    
        article_info_res = self.pipeline(method=self.process_gets, 
                                 args=article_info_urls)
        if article_info_res:
            return dict(zip(article_id, article_info_res))

    # articles' content
    def article_content(self, article_id: Union[str,List[str]]):
        if not isinstance(article_id, list):
            article_id = [article_id]
        article_content_urls = self.get_urls(endpoint='/article/{article_id}/content', 
                                       key='article_id', 
                                       args=article_id)    
        article_content_res = self.pipeline(method=self.process_gets, 
                                 args=article_content_urls)
        if article_content_res:
            return dict(zip(article_id, article_content_res))
        
    # articles' markdown
    # articles' responses
    # publications' ids
    # publications' info
    # publications' articles
    # publications' newsletters
    # topfeeds for tags and mode
    def topfeeds(self, tag: Union[str,List[str]], mode: str = 'hot'):
        if not isinstance(tag, list):
            tag = [tag]
        topfeeds_urls = self.get_urls(endpoint='/topfeeds/{tag}/' + mode, 
                                       key='tag', 
                                       args=tag)    
        topfeeds_res = self.pipeline(method=self.process_gets, 
                                     args=topfeeds_urls)
        if topfeeds_res:
            return dict(zip(tag, topfeeds_res))

    # top writers for topic_slug
    def top_writers(self, topic_slug: Union[str,List[str]]):
        if not isinstance(topic_slug, list):
            topic_slug = [topic_slug]
        top_writers_urls = self.get_urls(endpoint='top_writers/{topic_slug}', 
                                         key='topic_slug', 
                                         args=topic_slug)    
        top_writers_res = self.pipeline(method=self.process_gets, 
                                        args=top_writers_urls)
        if top_writers_res:
            return dict(zip(topic_slug, top_writers_res))

    # latest posts
    # related tags
    def related_tags(self, tag: Union[str,List[str]]):
        if not isinstance(tag, list):
            tag = [tag]
        related_tags_urls = self.get_urls(endpoint='/related_tags/{tag}', 
                                          key='tag', 
                                          args=tag)    
        related_tags_res = self.pipeline(method=self.process_gets, 
                                         args=related_tags_urls)
        if related_tags_res:
            return dict(zip(tag, related_tags_res))

              