"""
News Embedding Module (V6 Phase 1)
===================================
Gemini embedding calls were retired on 2026-10-29 (operator directive).
The public API is kept so legacy training (train_global_brain.py) still runs,
but every embedding is now a zero vector and no external API is called.

Usage:
    from modules.news_embedding import get_news_embedding, get_batch_news_embeddings
"""
import numpy as np


def get_news_embedding(ticker, stock_name=None, dim=3072):
    """
    Get news embedding vector for a ticker.
    
    Args:
        ticker: Stock ticker (e.g., 'AAPL', '005930.KS')
        stock_name: Optional stock name for search
        dim: Expected embedding dimension
    
    Returns:
        numpy zeros of shape (dim,) — the embedding source is retired
    """
    return np.zeros(dim)


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
    for ticker in tickers:
        emb = get_news_embedding(ticker)
        embeddings[ticker] = emb
    
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
