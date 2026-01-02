# Procedure
## Hypergraph Construction
### chunk division
```bash
python chunking.py --input "data/raw corpus/locomo10mini.json" --out_dir data/chunks --chunk_size 1000 --overlap 200
```
### 抽取entity relation
```bash
python extract_entities_relations.py --overwrite
```