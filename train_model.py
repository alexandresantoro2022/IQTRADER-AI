import os
import sys
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

# ========== CONFIGURAÇÕES ==========
N_SAMPLES_DEFAULT = 100
N_FEATURES_DEFAULT = 4  # defina seu número de features esperado

# ========== CARREGAR OU GERAR DADOS ==========
if os.path.exists('features.npy') and os.path.exists('labels.npy'):
    X = np.load('features.npy')
    y = np.load('labels.npy')
    print(f"✅ Carregados {len(X)} samples de 'features.npy' e 'labels.npy'.")
else:
    print("⚠️ Arquivos 'features.npy' ou 'labels.npy' não encontrados.")
    print(f"Gerando {N_SAMPLES_DEFAULT} samples e {N_FEATURES_DEFAULT} features de exemplo...")
    # Gera dados de exemplo aleatórios ('call' e 'put')
    X = np.random.rand(N_SAMPLES_DEFAULT, N_FEATURES_DEFAULT)
    y = np.random.choice(['call', 'put'], size=N_SAMPLES_DEFAULT)
    np.save('features.npy', X)
    np.save('labels.npy', y)
    print("✅ Arquivos de exemplo 'features.npy' e 'labels.npy' criados.")

# ========== TREINO DO MODELO ==========
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=None,
    min_samples_split=2,
    random_state=42
)
model.fit(X, y)
print(f"✅ Modelo treinado com {len(X)} samples.")

# ========== SALVAR MODELO ==========
joblib.dump(model, 'model.pkl')
print("✅ model.pkl salvo com sucesso.")
