__author__ = 'austin'

state_urls_to_crawl = {
    'AL': 'http://www.alabamagasprices.com',
    'AK': 'http://www.alaskagasprices.com',
    'AZ': 'http://www.arizonagasprices.com',
    'AR': 'http://www.arkansasgasprices.com',
    'CA': 'http://www.californiagasprices.com',
    'CO': 'http://www.coloradogasprices.com',
    'CT': 'http://www.connecticutgasprices.com',
    'DC': 'http://www.washingtondcgasprices.com',
    'DE': 'http://www.delawaregasprices.com',
    'FL': 'http://www.floridastategasprices.com',
    'GA': 'http://www.georgiagasprices.com',
    'HI': 'http://www.hawaiigasprices.com',
    'ID': 'http://www.idahogasprices.com',
    'IL': 'http://www.illinoisgasprices.com',
    'IN': 'http://www.indianagasprices.com',
    'IA': 'http://www.iowastategasprices.com',
    'KS': 'http://www.kansasgasprices.com',
    'KY': 'http://www.kentuckygasprices.com',
    'LA': 'http://www.louisianagasprices.com',
    'ME': 'http://www.mainegasprices.com',
    'MD': 'http://www.marylandgasprices.com',
    'MA': 'http://www.massachusettsgasprices.com',
    'MI': 'http://www.michigangasprices.com',
    'MN': 'http://www.michigangasprices.com',
    'MS': 'http://www.michigangasprices.com',
    'MO': 'http://www.missourigasprices.com',
    'MT': 'http://www.montanagasprices.com',
    'NE': 'http://www.nebraskagasprices.com',
    'NV': 'http://www.nevadagasprices.com',
    'NH': 'http://www.newhampshiregasprices.com',
    'NJ': 'http://www.newjerseygasprices.com',
    'NM': 'http://www.newmexicogasprices.com',
    'NY': 'http://www.newyorkstategasprices.com',
    'NYC': 'http://www.newyorkgasprices.com',
    'NC': 'http://www.northcarolinagasprices.com',
    'ND': 'http://www.northdakotagasprices.com',
    'OH': 'http://www.ohiogasprices.com',
    'OK': 'http://www.oklahomagasprices.com',
    'OR': 'http://www.oregongasprices.com',
    'PA': 'http://www.pennsylvaniagasprices.com',
    'RI': 'http://www.rhodeislandgasprices.com',
    'SC': 'http://www.southcarolinagasprices.com',
    'SD': 'http://www.southdakotagasprices.com',
    'TN': 'http://www.tennesseegasprices.com',
    'TX': 'http://www.texasgasprices.com',
    'UT': 'http://www.utahgasprices.com',
    'VT': 'http://www.vermontgasprices.com',
    'VA': 'http://www.virginiagasprices.com',
    'WA': 'http://www.washingtongasprices.com',
    'WV': 'http://www.westvirginiagasprices.com',
    'WI': 'http://www.wisconsingasprices.com',
    'WY': 'http://www.wyominggasprices.com'
}

lowest_search_frequency = 1 * 60 * 60  # Pull every hour on the hour
avg_search_frequency = 24 * 60 * 60  # Pull once a day, who cares

database_name = 'fuel'
