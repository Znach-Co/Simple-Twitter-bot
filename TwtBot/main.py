import os
import twitter
from twitter import TwitterError
import random
import time
import json
import pickle
import hashlib
from datetime import datetime, timedelta
from copy import deepcopy
import traceback


random.seed(datetime.now())

BOT_FOLDER = os.path.dirname(__file__)
BOT_CONFIGS = os.path.join(BOT_FOLDER, 'config.json')


def sleeper():
    """
    Make sleeper keep right intervals
    :return:
    """
    time.sleep(random.randint(15, 30))


def get_configs(path):
    """
    Read config file

    :param path:
    :return:
    """
    with open(path) as f:
        data = json.load(f)
    return data


def if_exists(folder):
    """
    Create folder for cookies

    :param folder:
    :return:
    """
    if os.path.exists(os.path.join(BOT_FOLDER, folder)):
        return os.path.join(BOT_FOLDER, folder)
    else:
        os.mkdir(os.path.join(BOT_FOLDER, folder))
        return os.path.join(BOT_FOLDER, folder)


class LimitChecker:
    _limits = {}

    def handle_request(self, req, *args, **kwargs):
        rate_limit = kwargs.pop('rate_limit', 15)

        if req.__name__ not in self._limits and rate_limit:
            self._limits[req.__name__] = {'left': rate_limit, 'start': round(time.time())}

        self._limits[req.__name__]['left'] -= 1

        if self._limits[req.__name__]['left'] < 0:
            time.sleep(abs(905 - (round(time.time()) - round(self._limits[req.__name__]['start']))))
            self._limits[req.__name__] = {'left': rate_limit - 1, 'start': round(time.time())}

        try:
            return req(*args, **kwargs)
        except TwitterError as e:
            for err in e.message:
                print(err)
                print(traceback.format_exc())
                if err.get('code') == 88:
                    time.sleep(15 * 60 + 5)
                    return req(*args, **kwargs)
                elif err.get('code') in [144, 139]:
                    return
            time.sleep(30)

            try:
                return req(*args, **kwargs)
            except Exception as e:
                print(e)
                print(traceback.format_exc())


class TWBot:
    """Main class for all actions and processes"""

    hash_name = ""

    last_ts = 0.0
    monitored_users = []
    media_to_like = 0
    media_to_retweet = 0
    users_to_follow = 0

    self_followings = []
    self_followers = []

    LC = LimitChecker()

    def __init__(self):
        """Reading configs"""
        self.__configs = get_configs(BOT_CONFIGS)

        """credentials"""
        __creds = self.__configs.pop('credentials', {})
        if __creds:
            __ck = __creds.get('consumer_key', '')
            __cs = __creds.get('consumer_secret', '')
            __atk = __creds.get('access_token_key', '')
            __ats = __creds.get('access_token_secret', '')
            if not __ck or not __cs or not __atk or not __ats:
                raise Exception('Please, provide your credentials(consumer_key, consumer_secret, access_token_key '
                                'and access_token_secret) in config.json - [https://developer.twitter.com/en/apps]')
        else:
            raise Exception('Please, provide your credentials(consumer_key, consumer_secret, access_token_key '
                            'and access_token_secret) in config.json - [https://developer.twitter.com/en/apps]')

        self.hash_name = hashlib.sha256(str(__ck[:4] + __cs[-4:]).encode()).hexdigest()[:8]

        self.api = twitter.Api(__ck,
                               __cs,
                               __atk,
                               __ats)

        """other settings"""
        self.limits_per_hour = self.__configs.pop('limitsPerHour', {})
        self.search_hashtags = self.__configs.pop('hashtags', [])
        self.process = self.__configs.pop('process', None)
        self.duration = self.__configs.pop('duration', {})
        self.white_list = self.__configs.pop('whiteList', [])

        if not self.limits_per_hour or not self.search_hashtags or \
            not self.process or not self.duration:
            raise Exception('Please, provide all necessary parameters(limitsPerHour, hashtags, process, duration)'
                            ' in config.json')

        self.check_parameters()
        self.white_list = [i.replace('@', '') for i in self.white_list]

        """Reading followers and pickle with monitoring data"""

        if self.process:
            _monitored_data_path = if_exists("additional_data")
            _monitored_current_data = os.path.join(_monitored_data_path, f"{self.hash_name}_monitoring.pickle")

            if os.path.exists(_monitored_current_data):
                with open(_monitored_current_data, 'rb') as f:
                    data = pickle.load(f)
                    self.monitored_users = data['monitored_users']
                    self.last_ts = float(data['last_ts'])

    def check_parameters(self):
        """
        Check parameters from configs
        :return:
        """

        if self.process not in ["Like", "Like-and-retweet", "Like-and-follow", "Like-follow-retweet"]:
            raiser('process')

        if "type" not in self.duration or "value" not in self.duration:
            raiser('duration(type or value)')
        else:
            typ = self.duration['type']
            val = self.duration['value']
            if self.process in ["Like", "Like-and-retweet"]:
                if typ not in ['by_time', 'by_likes']:
                    raiser('type')

                if "like" not in self.limits_per_hour:
                    raiser('limitsPerHour(like)')
                else:
                    try:
                        self.limits_per_hour['like'] = float(self.limits_per_hour['like'])
                    except ValueError:
                        raiser('like')
            elif self.process in ["Like-and-follow", "Like-follow-retweet"]:
                if typ not in ['by_time', 'by_users']:
                    raiser('type')

                if "like" not in self.limits_per_hour or "follow" not in self.limits_per_hour \
                        or "unfollow" not in self.limits_per_hour:
                    raiser('limitsPerHour(like or follow or unfollow)')
                else:
                    for i in ["like", "follow", "unfollow"]:
                        try:
                            self.limits_per_hour[i] = float(self.limits_per_hour[i])
                        except ValueError:
                            raiser(i)
            try:
                self.duration['value'] = float(val)
            except ValueError:
                raiser('value')

        if not isinstance(self.search_hashtags, list):
            raiser('hashtags')

        if not isinstance(self.white_list, list):
            raiser('whiteList')

    def dump_all(self):
        """
        Finish bot process, dump settings and users
        :return:
        """
        _monitored_data_path = if_exists("additional_data")
        _monitored_current_data = os.path.join(_monitored_data_path, f"{self.hash_name}_monitoring.pickle")
        data = {'monitored_users': self.monitored_users, 'last_ts': datetime.now().timestamp()}
        with open(_monitored_current_data, 'wb') as f:
            pickle.dump(data, f)


    """Active processes"""

    def run(self):
        """
        Run the main process
        :return:
        """
        print('A simple bot started the process.')
        try:
            self.calculate_before_process()

            if self.process == "Like":
                self.process_like()
            elif self.process == "Like-and-retweet":
                self.process_like_retweet()
            elif self.process == "Like-and-follow":
                self.process_like_and_follow()
            elif self.process == "Like-follow-retweet":
                self.process_like_follow_retweet()
        except Exception as e:
            print(e)
            print(traceback.format_exc())
        finally:
            self.dump_all()
        print('A simple bot finished the process.')

    def calculate_before_process(self):
        """
        Prepare main value for process
        :return:
        """
        typ = self.duration.get('type')
        val = self.duration.get('value')

        if self.process in ["Like", "Like-and-retweet"]:
            if typ == "by_time":
                self.media_to_like = round(val*self.limits_per_hour.get('like'))
            elif typ == "by_likes":
                self.media_to_like = round(val)

            if self.process == "Like-and-retweet":
                self.media_to_retweet = round(self.media_to_like/self.limits_per_hour.get('like')
                                              *self.limits_per_hour.get('retweet'))

        elif self.process in ["Like-and-follow", "Like-follow-retweet"]:
            if typ == "by_time":
                self.users_to_follow = round(val*self.limits_per_hour.get('follow'))
            elif typ == "by_users":
                self.users_to_follow = round(val)

            if self.process == "Like-follow-retweet":
                self.media_to_retweet = round(self.users_to_follow/self.limits_per_hour.get('follow')
                                              *self.limits_per_hour.get('retweet'))

    """Four main processes"""

    def process_like(self):
        medias = self.prepare_process_like()
        wait_time = 3600 // (self.limits_per_hour.get('like') + 1)
        for m in medias:
            time.sleep(abs(wait_time + trunc_gauss(0, 5, -10, 10)))
            self.liking(m)

    def process_like_retweet(self):
        medias = self.prepare_process_like(retweet_flag=True)
        likes, retweet = len(medias) - self.media_to_retweet, self.media_to_retweet
        all_acts = round(self.limits_per_hour.get('like') + self.limits_per_hour.get('retweet'))
        wait_time = 3600 // (all_acts + 1)

        while likes or retweet:
            time.sleep(abs(wait_time + trunc_gauss(0, 5, -10, 10)))
            rc = random.choices(['l', 'r'], [likes, retweet])[0]
            m = medias.pop(0)

            if rc == 'l':
                self.liking(m)
                likes -= 1
            elif rc == 'r':
                self.retweeting(m)
                retweet -= 1

    def process_like_follow_retweet(self):
        follow, media, unfollow = self.prepare_process_like_and_follow(retweet_flag=True)
        follow_acts, media_acts, unfollow_acts = len(follow), len(media) - self.media_to_retweet, len(unfollow)
        retweet = self.media_to_retweet
        all_acts = round(self.limits_per_hour.get('follow') + self.limits_per_hour.get('like') +
                         self.limits_per_hour.get('unfollow') + self.limits_per_hour.get('retweet'))
        wait_time = 3600 // all_acts + 1

        while follow_acts or media_acts or unfollow_acts or retweet:
            time.sleep(abs(wait_time + trunc_gauss(0, 5, -10, 10)))
            rc = random.choices(['f', 'l', 'u', 'r'], [follow_acts, media_acts, unfollow_acts, retweet])[0]

            if rc == 'f':
                fo = follow.pop(0)
                self.following_and_storing(fo)
                follow_acts -= 1
            elif rc == 'l':
                mo = media.pop(0)
                self.liking(mo)
                media_acts -= 1
            elif rc == 'u':
                uo = unfollow.pop(0)
                self.unfollowing_and_removing(uo)
                unfollow_acts -= 1
            elif rc == 'r':
                mo = media.pop(0)
                self.retweeting(mo)
                retweet -= 1

    def process_like_and_follow(self):
        follow, media, unfollow = self.prepare_process_like_and_follow()
        follow_acts, media_acts, unfollow_acts = len(follow), len(media), len(unfollow)
        all_acts = round(self.limits_per_hour.get('follow') + self.limits_per_hour.get('like') +
                         self.limits_per_hour.get('unfollow'))
        wait_time = 3600 // all_acts + 1
        while follow_acts or media_acts or unfollow_acts:
            time.sleep(abs(wait_time + trunc_gauss(0, 5, -10, 10)))
            rc = random.choices(['f', 'l', 'u'], [follow_acts, media_acts, unfollow_acts])[0]

            if rc == 'f':
                fo = follow.pop(0)
                self.following_and_storing(fo)
                follow_acts -= 1
            elif rc == 'l':
                mo = media.pop(0)
                self.liking(mo)
                media_acts -= 1
            elif rc == 'u':
                uo = unfollow.pop(0)
                self.unfollowing_and_removing(uo)
                unfollow_acts -= 1

    """Sub processes"""

    def liking(self, media_id):
        self.LC.handle_request(self.api.CreateFavorite, status_id=media_id, rate_limit=999)

    def retweeting(self, media_id):
        self.LC.handle_request(self.api.PostRetweet, status_id=media_id, rate_limit=299)

    def following_and_storing(self, user_object):
        self.LC.handle_request(self.api.CreateFriendship, user_object['user'], rate_limit=399)
        self.monitored_users.append({'user': user_object['user'], 'username': user_object['username'],
                                    'followDate': datetime.now().timestamp()})

    def unfollowing_and_removing(self, user_id):
        self.LC.handle_request(self.api.DestroyFriendship, user_id, rate_limit=399)
        ind = [i for i, j in enumerate(self.monitored_users) if j.get('user', '') == user_id]
        if ind:
            self.monitored_users.remove(self.monitored_users[ind[0]])

    def hashtag_feed_list(self, hashtags, maxnec):

        if 15*len(hashtags)/maxnec > 3:
            count = 30
        else:
            count = 3*maxnec//len(hashtags)
            if count > 100:
                count = 100

        statuses = []
        for hashtag in hashtags:
            cursts = []
            max_id = 0
            while len(cursts) < maxnec:
                if not max_id:
                    curst = self.LC.handle_request(self.api.GetSearch, term=hashtag, count=count, return_json=True,
                                                   rate_limit=179)
                    curst = curst.get('statuses', [])
                    curst = [i['id'] for i in curst]
                    curst = self.LC.handle_request(self.api.GetStatuses, curst, rate_limit=299)
                    curst = [i._json for i in curst]
                else:
                    curst = self.LC.handle_request(self.api.GetSearch, term=hashtag, count=count, max_id=max_id,
                                                   return_json=True, rate_limit=179)
                    curst = curst.get('statuses', [])
                    curst = [i['id'] for i in curst]
                    curst = self.LC.handle_request(self.api.GetStatuses, curst, rate_limit=299)
                    curst = [i._json for i in curst]

                curst = [i for i in curst if not i['favorited'] and not i['retweeted']]
                cursts.extend(curst)
                max_id = min([i['id'] for i in curst])

            statuses.extend(cursts)

        return statuses

    # preparation before process

    def prepare_process_like(self, retweet_flag=False):
        """
        Prepare media for liking process
        :return:
        """
        media = []

        if not retweet_flag:
            feed_likes = self.media_to_like//2
            following_likes = round((self.media_to_like//2)*3/4)
            followers_likes = self.media_to_like - feed_likes - following_likes
        else:
            feed_likes = (self.media_to_like + self.media_to_retweet)//2
            following_likes = round(((self.media_to_like + self.media_to_retweet)//2)*3/4)
            followers_likes = (self.media_to_like + self.media_to_retweet) - feed_likes - following_likes

        ids = []
        posts = self.hashtag_feed_list(self.search_hashtags, self.media_to_like)

        if len(posts) > feed_likes:
            _ = [ids.append(i['id']) for i in (random.choice(posts) for _ in range(feed_likes)) if i['id'] not in ids]
            if len(ids) < feed_likes:
                rest_to_add = feed_likes - len(ids)
                for p in posts:
                    if p['id'] not in ids:
                        ids.append(p['id'])
                        rest_to_add -= 1
                        if rest_to_add <= 0:
                            break
        else:
            ids.extend([i['id'] for i in posts[:feed_likes] if i['id'] not in ids])

        media.extend(ids)
        followings = []
        media.extend([i for i in self.get_following_likes(followings, following_likes) if i and i not in media])

        media.extend([i for i in self.get_followers_likes(followers_likes) if i and i not in media])

        return media

    def prepare_process_like_and_follow(self, retweet_flag=False):
        """
        Prepare data for liking and following process
        :return:
        """
        follow = []
        media = []
        unfollow = []

        coef = self.users_to_follow / self.limits_per_hour.get('follow', 1)
        num_to_unfollow = round(coef * self.limits_per_hour.get('unfollow'))

        if not retweet_flag:
            media_to_like = round(coef*self.limits_per_hour.get('like'))
        else:
            media_to_like = round(coef * self.limits_per_hour.get('like')) + self.media_to_retweet

        feed_likes = media_to_like // 2
        feed_likes_list = []
        following_likes = round((media_to_like // 2) * 3 / 4)
        following_likes_list = []
        followers_likes = media_to_like - feed_likes - following_likes

        monitored_ids = [i["user"] for i in self.monitored_users]
        posts = self.hashtag_feed_list(self.search_hashtags, self.users_to_follow)

        #follow
        n_post = 0
        while len(follow) < self.users_to_follow and n_post <= len(posts):
            m = posts[n_post]
            if self.check_if_suit(m):
                user_id, username = self.get_user_from_post(m)
                if user_id and user_id not in [i["user"] for i in follow] \
                        and user_id not in monitored_ids:
                    follow.append({'user': user_id, 'username': username})
                    if m not in following_likes_list:
                        following_likes_list.append(m)
            n_post += 1

        for p in following_likes_list:
            if p in posts:
                posts.remove(p)

        # likes
        if len(posts) > feed_likes:
            feed_likes_list.extend([i['id'] for i in (random.choice(posts) for _ in range(feed_likes))
                                    if i['id'] not in feed_likes_list])
        else:
            feed_likes_list.extend([i['id'] for i in posts if i['id'] not in feed_likes_list])

        media.extend(feed_likes_list)

        if len(following_likes_list) < following_likes:
            followings = []
            get_n_followings = following_likes - len(following_likes_list)
            if following_likes_list:
                following_likes_list = [i['id'] for i in following_likes_list]
            following_likes_list.extend([i for i in self.get_following_likes(followings, get_n_followings)
                                         if i and i not in media])
            media.extend(following_likes_list)
        else:
            media.extend([i['id'] for i in following_likes_list[:following_likes]])
        media.extend([i for i in self.get_followers_likes(followers_likes) if i and i not in media])

        #unfollow
        unfollow = self.get_to_unfollow(num_to_unfollow)

        return follow, media, unfollow

    # Sub helpers/decision makers

    def check_if_suit(self, media):

        media_fr_st = media.get('user', {})
        user_id = media_fr_st.get('id', None)

        if media_fr_st:
            if media_fr_st.get('following', None):
                return False
            if media_fr_st.get('follow_request_sent', None):
                return False

        if user_id:
            m_users = [u['user'] for u in self.monitored_users]
            if user_id in m_users:
                return False

            friendship = self.LC.handle_request(self.api.LookupFriendship, user_id, rate_limit=299)
            friendship = friendship[0]._json
            if friendship['connections']:
                if friendship['connections'][0] != 'none':
                    return False
        return True

    def get_user_from_post(self, media):
        if media:
            return media.get('user', {}).get('id'), media.get('user', {}).get('screen_name')

    def get_to_unfollow(self, num_users):
        to_unfollow = []

        if self.monitored_users:
            current_monitored = \
                list(filter(lambda x: datetime.fromtimestamp(float(x['followDate'])) + timedelta(days=14)
                                      < datetime.now() and x['username'] not in self.white_list, self.monitored_users))
            to_unfollow.extend([u['user'] for u in current_monitored])

        if len(to_unfollow) < num_users:
            if not self.self_followings:
                self.self_followings = self.get_followings()
            add_followings = [f['id'] for f in self.self_followings if f['screen_name'] not in self.white_list]

            if add_followings:
                if len(add_followings) > num_users - len(to_unfollow):
                    to_unfollow.extend([random.choice(add_followings) for _ in range(num_users - len(to_unfollow))])
                else:
                    to_unfollow.extend(add_followings)
        else:
            to_unfollow = [random.choice(to_unfollow) for _ in range(num_users)]

        return to_unfollow

    def get_following_likes(self, followings_list, following_likes):
        """

        :param followings_list:
        :param following_likes:
        :return:
        """

        user_followings = []
        if self.monitored_users:
            followings_list.extend([u['user'] for u in self.monitored_users])

        if len(followings_list) < following_likes:
            user_followings = self.get_followings()
            self.self_followings = deepcopy(user_followings)
            user_followings = [i['id'] for i in user_followings if i['id'] not in followings_list]

            if user_followings:
                if len(user_followings) > following_likes - len(followings_list):
                    followings_list.extend(
                        [random.choice(user_followings) for _ in range(following_likes - len(followings_list))])
                else:
                    followings_list.extend(user_followings)
        else:
            followings_list = [random.choice(followings_list) for _ in range(following_likes)]

        followings_media_ids = [self.random_user_media(i) for i in followings_list]

        if len(followings_media_ids) < following_likes and user_followings:
            while len(followings_media_ids) < following_likes:
                u = random.choice(user_followings)
                rm = self.random_user_media(u)
                if rm and rm not in followings_media_ids:
                    followings_media_ids.append(rm)

        return followings_media_ids

    def get_followings(self):
        followings = self.LC.handle_request(self.api.GetFriends)
        return [i._json for i in followings]

    def get_followers(self):
        followers = self.LC.handle_request(self.api.GetFollowers)
        return [i._json for i in followers]

    def get_followers_likes(self, followers_likes):
        """
        Prepare followers media to like
        :param followers_likes:
        :return:
        """
        followers = []

        user_followers = self.get_followers()
        self.self_followers = deepcopy(user_followers)
        user_followers = [i['id'] for i in user_followers]

        if user_followers:
            if len(user_followers) > followers_likes - len(followers):
                followers.extend([random.choice(user_followers) for _ in range(followers_likes - len(followers))])
            else:
                followers.extend(user_followers)

        followers_media_ids = [self.random_user_media(i) for i in followers]

        if len(followers_media_ids) < followers_likes and user_followers:
            while len(followers_media_ids) < followers_likes:
                u = random.choice(user_followers)
                rm = self.random_user_media(u)
                if rm and rm not in followers_media_ids:
                    followers_media_ids.append(rm)

        return followers_media_ids

    def random_user_media(self, user_id):
        """
        Get random media from user's feed
        :param user_id:
        :return:
        """
        try:
            feed = self.get_user_media(user_id)
            feed = self.LC.handle_request(self.api.GetStatuses, [i['id'] for i in feed], rate_limit=299)
            feed = [i._json for i in feed]

            items = [i for i in feed if not i['favorited'] and not i['retweeted']]
            items = sorted(items[:6], key=lambda x: x['favorite_count'], reverse=True)
            if items:
                return items[0].get('id')
            else:
                return None
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            return None

    def get_user_media(self, user_id):
        media = self.LC.handle_request(self.api.GetUserTimeline, user_id, rate_limit=899)
        return [i._json for i in media]


def raiser(string):
    """
    Raise error if parameter missed
    :param string:
    :return:
    """
    raise Exception(f'Please check your config.json file, {string} is missed or wrong.')


def trunc_gauss(mu, sigma, bottom, top):
    """
    Generate number from normal distribution

    :param mu: mean
    :param sigma: step
    :param bottom: min
    :param top: max
    :return: int number
    """
    a = random.gauss(mu, sigma)
    while (bottom <= a <= top) is False:
        a = random.gauss(mu, sigma)
    return int(a)


if __name__ == "__main__":
    TW = TWBot()
    TW.run()
