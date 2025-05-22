# Estrutura do Projeto

Arquivos incluídos:
- main.py          -> Código principal do bot (usa model.pkl)
- train_model.py   -> Script para gerar model.pkl a partir de features.npy e labels.npy
- features.npy     -> Seu dataset de features (não incluído, você deve gerá-lo)
- labels.npy       -> Seu dataset de labels (não incluído, você deve gerá-lo)
- model.pkl        -> Modelo treinado (será gerado pelo train_model.py)

Como usar:
1. Coloque 'features.npy' e 'labels.npy' na mesma pasta.
2. Rode: python train_model.py
3. Rode: python main.py
