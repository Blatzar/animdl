import re
import lxml.html as htmlparser

ANIME_RE = re.compile(r"(?:https?://)?(?:\S+\.)?gogoanime\.ai/([^&?/]+)-episode-\d+")

EPISODE_LOAD_AJAX = "https://ajax.gogo-load.com/ajax/load-list-episode"
SITE_URL = "https://www1.gogoanime.ai"

ajax_parse = lambda dt: (
    dt.get('source', [{}])[0].get('file'), dt.get('source', [{}])[0].get('label'), dt.get('source', [{}])[0].get('type'), 
    dt.get('source_bk', [{}])[0].get('file'), dt.get('source_bk', [{}])[0].get('label'), dt.get('source_bk', [{}])[0].get('type'))

def get_episode_list(session, anime_id):
    """
    Fetch all the episodes' url from GogoAnime using.
    """
    with session.get(EPISODE_LOAD_AJAX, params={'ep_start': '0', 'ep_end': '2000', 'id': anime_id,}) as episode_page:
        content = htmlparser.fromstring(episode_page.text)
        
    for episode in content.xpath('//ul[@id="episode_related"]/li/a'):
        yield SITE_URL + episode.get('href', '').strip()
        
def get_anime_id(html_content):
    assert (content := html_content.xpath('//input[@id="movie_id"]')), "No GGA Anime ID found."
    return int(content[0].get('value', 0))

def convert_to_anime_page(url):
    
    if match := ANIME_RE.search(url):
        return SITE_URL + "/category/%s" % match.group(1)
    return url

def get_stream_url(session, episode_page_url):
    
    with session.get(episode_page_url) as response:
        content_parsed = htmlparser.fromstring(response.text)
        
    streaming = content_parsed.xpath('//div[@class="play-video"]/iframe')[0].get('src')
    
    with session.get('https:%s' % streaming.replace('streaming', 'ajax')) as response:
        content = response.json()

    s1, l1, t1, s2, l2, t2 =  ajax_parse(content)
    
    return [{'quality': "%s [%s]" % (l1, t1), 'stream_url': s1}] + ([{'quality': "%s [%s]" % (l2, t2), 'stream_url': s2}] if s2 else [])
    

def fetcher(session, url, check):
    """
    Fetching algorithm from [here.](https://github.com/justfoolingaround/anime-radar/blob/master/radar/datacaller/gogoanime.py)
    """
    url = convert_to_anime_page(url)
    
    with session.get(url) as anime_page:
        content_id = get_anime_id(htmlparser.fromstring(anime_page.text))
        
    episodes = reversed([*get_episode_list(session, content_id)])
    
    for index, episode in enumerate(episodes, 1):
        if check(index):
            yield get_stream_url(session, episode)