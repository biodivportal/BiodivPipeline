import pandas as pd
import httpx
import asyncio

from config import REQUEST_DELAY, log
from land_classifier import classify_land
from taxonomy_lookup import match_gbif
from models import ClassifierResult, CLCMatch

def _get_text(row: pd.Series) -> tuple[str | None, str]:
    for field in ('FundortUNdOeko', 'Locality'):
        val = row.get(field)
        if pd.notna(val) and str(val).strip():
            return str(val).strip(), field
    return None, ''

async def process_row(row: pd.Series, client: httpx.AsyncClient, use_ollama: bool) -> ClassifierResult:
    await asyncio.sleep(REQUEST_DELAY)

    text, field = _get_text(row)
    
    if not text:
        log.warning('Row %s has no usable text field; skipping land classification',
                row.get('HerbariumID', '?'))

   
    clc = await classify_land(text or '', use_ollama)
    clc.field = field
 
    taxon = await match_gbif(row['FullNameCache'], row['Genus'], row['Family'], client)
 
    return ClassifierResult(
        id=row['HerbariumID'],
        taxon=taxon,
        clc=clc
    )