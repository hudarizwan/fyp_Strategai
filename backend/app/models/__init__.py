"""
__init__.py for models package
"""

from app.models.price_lstm import PricePredictorNN

try:
    from app.models.price_lstm import PriceLSTM
    __all__ = ['PricePredictorNN', 'PriceLSTM']
except:
    __all__ = ['PricePredictorNN']
