"""
News Embedding Module (V6 Phase 1)
===================================
Generates semantic embedding vectors from news headlines using Gemini API.
These embeddings capture market sentiment, themes, and catalysts that
pure price-based features cannot detect.

Usage:
    from modules.news_embedding import get_news_embedding, get_batch_news_embeddings
"""
import os
import time
import numpy as np
import feedparser
from urllib.parse import quote

# Cache to avoid redundant API calls
_embedding_cache = {}
_genai = None
_genai_configured = False


def _ensure_genai():
    """Lazy-load and configure genai"""
    global _genai, _genai_configured
    if _genai_configured:
        return _genai is not None
    
    try:
        import google.generativeai as genai
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv('GEMINI_API_KEY', '')
        if not api_key:
            _genai_configured = True
            return False
        genai.configure(api_key=api_key)
        _genai = genai
        _genai_configured = True
        return True
    except Exception:
        _genai_configured = True
        return False


def _fetch_headlines(query, max_items=10):
    """Fetch headlines from Google RSS"""
    try:
        url = f"https://news.google.com/rss/search?q={quote(query)}+stock&hl=en&gl=US"
        feed = feedparser.parse(url)
        headlines = [e.title for e in feed.entries[:max_items] if hasattr(e, 'title')]
        return headlines
    except Exception:
        return []


def get_news_embedding(ticker, stock_name=None, dim=3072):
    """
    Get news embedding vector for a ticker.
    
    Args:
        ticker: Stock ticker (e.g., 'AAPL', '005930.KS')
        stock_name: Optional stock name for search
        dim: Expected embedding dimension
    
    Returns:
        numpy array of shape (dim,) or zeros if unavailable
    """
    # Check cache
    cache_key = f"{ticker}_{time.strftime('%Y%m%d_%H')}"
    if cache_key in _embedding_cache:
        return _embedding_cache[cache_key]
    
    zeros = np.zeros(dim)
    
    if not _ensure_genai():
        return zeros
    
    # Build search query
    clean_ticker = ticker.replace('.KS', '').replace('.KQ', '')
    query = stock_name if stock_name else clean_ticker
    
    headlines = _fetch_headlines(query, max_items=8)
    if not headlines:
        _embedding_cache[cache_key] = zeros
        return zeros
    
    # Combine headlines into single text
    combined = " | ".join(headlines[:8])
    if len(combined) > 2000:
        combined = combined[:2000]
    
    try:
        result = _genai.embed_content(
            model='models/gemini-embedding-001',
            content=combined
        )
        embedding = np.array(result['embedding'], dtype=np.float32)
        _embedding_cache[cache_key] = embedding
        return embedding
    except Exception as e:
        _embedding_cache[cache_key] = zeros
        return zeros


def get_batch_news_embeddings(tickers, pca_model=None, n_components=10):
    """
    Get news embeddings for multiple tickers with optional PCA reduction.
    
    Args:
        tickers: List of ticker symbols
        pca_model: Fitted PCA model (if None, returns raw embeddings)
        n_components: Number of PCA components
    
    Returns:
        dict of {ticker: numpy array of shape (n_components,)}
    """
    embeddings = {}
    for i, ticker in enumerate(tickers):
        emb = get_news_embedding(ticker)
        embeddings[ticker] = emb
        
        # Rate limiting (Gemini free tier: 60 RPM)
        if (i + 1) % 10 == 0:
            time.sleep(1)
    
    if pca_model is not None:
        for ticker, emb in embeddings.items():
            try:
                reduced = pca_model.transform(emb.reshape(1, -1))[0]
                embeddings[ticker] = reduced
            except Exception:
                embeddings[ticker] = np.zeros(n_components)
    
    return embeddings


def create_news_features_for_training(tickers, n_components=10):
    """
    Create news embedding features for training data.
    Fetches embeddings for all tickers and fits PCA.
    
    Args:
        tickers: List of ticker symbols
        n_components: Number of PCA components
    
    Returns:
        (embeddings_dict, pca_model)
        - embeddings_dict: {ticker: numpy array of shape (n_components,)}
        - pca_model: fitted PCA model to save
    """
    from sklearn.decomposition import PCA
    
    print(f"  📰 Fetching news embeddings for {len(tickers)} tickers...")
    
    raw_embeddings = {}
    valid_embeddings = []
    
    for i, ticker in enumerate(tickers):
        emb = get_news_embedding(ticker)
        raw_embeddings[ticker] = emb
        
        if np.any(emb != 0):
            valid_embeddings.append(emb)
        
        if (i + 1) % 15 == 0:
            print(f"    [{i+1}/{len(tickers)}] embeddings fetched...")
            time.sleep(1)  # Rate limiting
    
    print(f"  ✅ {len(valid_embeddings)}/{len(tickers)} valid embeddings")
    
    if len(valid_embeddings) < 5:
        print("  ⚠️ Too few valid embeddings, using zero features")
        pca = None
        reduced = {t: np.zeros(n_components) for t in tickers}
        return reduced, pca
    
    # Fit PCA
    emb_matrix = np.array(valid_embeddings)
    n_comp = min(n_components, len(valid_embeddings), emb_matrix.shape[1])
    pca = PCA(n_components=n_comp, random_state=42)
    pca.fit(emb_matrix)
    
    explained = sum(pca.explained_variance_ratio_) * 100
    print(f"  📊 PCA: {n_comp} components, {explained:.1f}% variance explained")
    
    # Transform all
    reduced = {}
    for ticker, emb in raw_embeddings.items():
        if np.any(emb != 0):
            try:
                reduced[ticker] = pca.transform(emb.reshape(1, -1))[0]
            except Exception:
                reduced[ticker] = np.zeros(n_comp)
        else:
            reduced[ticker] = np.zeros(n_comp)
    
    return reduced, pca
