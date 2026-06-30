import logging
import os

from dotenv import load_dotenv

load_dotenv()

LAND_API_BASE = os.environ.get('LAND_TAXONOMY_API_URL', 'http://land-taxonomy-api:8000')
GBIF_CONFIDENCE_RESOLVED = 80
API_RETRIES = 10
REQUEST_DELAY = 0.3
BATCH_SIZE = 10

OPENAI_API_KEY  = os.getenv('OPENAI_API_KEY')
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434/v1')
OPENAI_MODEL    = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
OLLAMA_MODEL    = os.getenv('OLLAMA_MODEL', 'llama3.2')
TAXONOMY_PATH   = os.getenv('TAXONOMY_PATH', '/app/taxonomy.csv')
 
DATA_PATH = '../data/'
CACHE_PATH = 'cache'
CACHE_GBIF = CACHE_PATH + '/cache_gbif.json'
CACHE_LAND = CACHE_PATH + '/cache_land.json'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)

logging.getLogger('httpx').setLevel(logging.WARNING)

log = logging.getLogger(__name__)