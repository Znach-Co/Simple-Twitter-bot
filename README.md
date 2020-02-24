# Simple-Twitter-bot
A simple Twitter bot for daily use, to like, follow, unfollow, retweet and automate your Twitter actions. Ready to use!

Twitter credentials (go to https://developer.twitter.com/).

Feel free to maintain and help good tools grow. :point_down:

<a href="https://www.buymeacoffee.com/2gcAduieV" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>


How to use:
-
- Install Python from https://www.python.org/downloads/ (download exe file version 3.6 or 3.7)
- Install pip (https://www.liquidweb.com/kb/install-pip-windows/)
- Unzip archive 
- open cmd
- cd path_to_unzip_folder/TwtBot
- pip install -r requirements.txt
- check config.json file (open it with Notepad or other text editor), save and close

To run bot:
- open cmd
- cd path_to_unzip_folder/TwtBot
- python main.py 


For pro users:
-
- update config.json
- python main.py



___________________________

Config.json

Example:
        
        {
          "credentials": {
            "consumer_key":"consumer_key",
            "consumer_secret":"consumer_secret",
            "access_token_key":"access_token_key",
            "access_token_secret":"access_token_secret"
          },
          "limitsPerHour": {
            "follow": 15,
            "unfollow": 15,
            "like": 30,
            "retweet": 10
          },
          "hashtags": ["digitalmarketing", "socialmediamarketing", "seo", "socialmedia", "marketing", "branding"], /*any kind of texts, even "a b c" or "#a b" and etc., max = 180*/
          "process": "Like-and-follow", /*Like-follow-retweet, Like-and-follow, Like-and-retweet, Like*/
          "duration": {
            "type": "by_time", /*by_users, by_time*/
            "value": 1
          },
          "whiteList": ["@freddy_johnson", "johnlock"]
        }
        
        Explanation:
        If "process":"Like-and-follow"/"Like-follow-retweet", 
            "duration": "by_users" or "by_time"
            "value": "X" users or "X" hrs
                                      
        If "process":"Like"/"Like-and-retweet", 
            "duration": "by_likes" or "by_time"
            "value": "X" likes or "X" hrs                                
_________
