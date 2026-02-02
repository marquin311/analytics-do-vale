import unittest
import pandas as pd
import numpy as np
from features.engine import prepare_data_for_ml, calculate_zscore_by_group

class TestFeatureEngineering(unittest.TestCase):
    
    def setUp(self):
        """Cria um DataFrame falso (Mock) para testes"""
        self.mock_data = pd.DataFrame({
            'puuid': ['p1', 'p1', 'p1', 'p2', 'p2'],
            'game_start_timestamp': [1000, 2000, 3000, 1000, 2000],
            'team_position': ['TOP', 'TOP', 'TOP', 'JUNGLE', 'JUNGLE'],
            'gold_velocity': [100, 120, 110, 50, 60], # Top ganha mais que JG neste exemplo
            'win': [1, 0, 1, 0, 1]
        })

    def test_shape_integrity(self):
        """Teste: O pipeline não deve deletar linhas"""
        processed = prepare_data_for_ml(self.mock_data)
        self.assertEqual(len(processed), 5)

    def test_zscore_logic(self):
        """Teste: Z-Score deve normalizar por Role"""
        # Adiciona colunas dummy para a função não reclamar
        df = self.mock_data.copy()
        df['cs_at_10'] = [10, 20, 15, 5, 5] # Média TOP=15, Média JG=5
        
        # Calcula na mão o Z-Score
        # Top: 10, 20, 15 -> Média 15. O valor 15 deve ter Z-Score ~0.
        
        col_rel = calculate_zscore_by_group(df, 'cs_at_10', 'team_position')
        
        # O terceiro elemento (15) é exatamente a média dos tops. Z-Score deve ser 0.
        self.assertAlmostEqual(col_rel.iloc[2], 0, places=1)

    def test_no_missing_values(self):
        """Teste: O modelo final não pode ter NaNs"""
        processed = prepare_data_for_ml(self.mock_data)
        # Verifica as colunas geradas
        self.assertFalse(processed['recent_form'].isna().any())
        self.assertFalse(processed['recent_volatility'].isna().any())

if __name__ == '__main__':
    print("🧪 Iniciando Bateria de Testes...")
    unittest.main()