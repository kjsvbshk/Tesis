# Release Notes — v2.1.0 / v2.1.1 / v2.1.2

## Estado actual

| Versión | Estado |
|---|---|
| v1.6.0 | **Activo en producción** |
| v2.1.0 | Entrenado contra Neon — **NO promovido**: falla Log Loss (0.6857) y ECE (0.0839) |
| v2.1.1 | **Descartado** sin entrenar — solo era ajuste de constantes (parche, no causa raíz) |
| v2.1.2 | Reformulación arquitectónica del meta-learner — **pendiente entrenar contra Neon** |

## Lección aprendida (registro para la tesis)

El error de v2.1.0 no fue numérico (λ₃ inflado), fue **conceptual**: introducir `poisson_proba` como meta-feature trata al Bivariate Poisson como un clasificador rival al RF. Esto es incorrecto:

| Componente | Tipo de salida | Régimen de calibración |
|---|---|---|
| `NBARandomForest` | Probabilidad discriminativa | Calibrada (CalibratedClassifierCV isotonic) |
| `NBAXGBoost` | Score regresivo (puntos) | N/A (no es probabilidad) |
| `NBABivariatePoisson` (v2.1.0) | Probabilidad estructural derivada de E[D]/σ | **No optimizada para log-loss** — tiende a extremos |

El meta-learner `LogReg` sin StandardScaler aprendía a confiar en la señal más extrema (poisson_proba) y la isotónica 1D no compensaba el sesgo. Resultado: overconfidence en bins [0.7, 0.9) y ECE 0.084 en NBA real.

> **Regla práctica documentada para la tesis**: si un componente del modelo no fue entrenado para clasificación pero produce algo que parece probabilidad, trátalo como **feature**, no como **predictor**.

## Resultados de v2.1.0 contra Neon (3 765 partidos, split 80/20)

| Métrica | v1.6.0 (activo) | v2.1.0 | Umbral | Pasa? |
|---|---:|---:|---:|---|
| Log Loss | 0.6553 | 0.6857 | < 0.68 | ❌ |
| Brier | 0.2312 | 0.2420 | < 0.25 | ✅ |
| ROC-AUC | 0.6542 | 0.6511 | > 0.55 | ✅ |
| ECE | 0.0363 | 0.0839 | < 0.05 | ❌ |
| MAE-margin | — | 12.21 | < 10 | ❌ |
| MAE-total | — | 16.45 | < 15 | ❌ |

## Cambios estructurales v2.1.0 → v2.1.2

| Componente | v2.1.0 | v2.1.2 |
|---|---|---|
| Meta-features | 3D `[rf_proba, score_diff, poisson_proba]` | **4D** `[rf_proba, score_diff, poisson_mu_diff, poisson_sigma_diff]` |
| Meta-learner | `LogReg(C=0.5)` | `Pipeline(StandardScaler → LogReg(C=0.1))` |
| Rol del Poisson | Predictor probabilístico | Feature estructural (magnitud + incertidumbre) |
| `predict_full` | expone `poisson_probability` | expone `poisson_probability` (solo diagnóstico, no entra al meta) |

`mu_diff = λ₁ - λ₂` (ventaja esperada en puntos). `sigma_diff = √(λ₁+λ₂)` (incertidumbre del margen). El StandardScaler garantiza que ninguna columna domine por escala absoluta.

## Ablation study sintético (sandbox local)

`tests/ablation_study.py` corre 4 variantes contra dataset sintético NBA-realista:

| Variante | Log Loss | Brier | AUC | ECE | Pasa criterios |
|---|---:|---:|---:|---:|---|
| RF solo | 0.4618 | 0.150 | 0.865 | 0.0420 | ✓ |
| **RF + XGBoost** (≈ v1.6.0) | **0.4333** | 0.141 | 0.881 | **0.0295** | **✓** |
| v2.1.0 (Poisson como prob) | 0.4259 | 0.138 | 0.887 | 0.0513 | ✗ |
| v2.1.2 (Poisson como features) | 0.4493 | 0.138 | 0.887 | 0.0417 | ✓ |

**Conclusión empírica del sintético**:
1. v2.1.2 corrige el ECE roto de v2.1.0 (0.051 → 0.042). La reformulación funciona.
2. Pero `RF + XGBoost` sin Poisson tiene el mejor ECE absoluto y un Log Loss mejor que v2.1.2.
3. En sintético, el Poisson **no aporta valor neto** al ensemble. Solo confirmación final viene del ablation contra Neon.

## Plan de decisión — qué entrenar y promover

### Paso 1 — Re-correr el ablation contra Neon (REQUERIDO antes de promover nada)

```bash
cd Tesis/ML
python -m tests.ablation_study --neon
```

Salida esperada: tabla idéntica a la del sintético pero con métricas reales NBA.

### Paso 2 — Decisión según el ablation real

```
                    ┌─ v2.1.2 ECE < 0.05 Y mejora Log Loss vs v1.6.0 ?
                    │
                    ├── SÍ ─────► Entrenar v2.1.2 oficial:
                    │              python -m src.training.train --version v2.1.2 --model ensemble
                    │              python scripts/deploy_model.py --version v2.1.2 --activate
                    │
                    └── NO ─────► RF+XGB (variante 2) ¿supera a v1.6.0 en ECE?
                                   │
                                   ├── SÍ ─────► Reentrenar v1.6.x con código actual
                                   │              (mismo ensemble pero limpio)
                                   │
                                   └── NO ─────► Mantener v1.6.0 activo.
                                                  Documentar el experimento Poisson
                                                  como sección crítica del Capítulo IV
                                                  (qué se intentó, por qué no funcionó,
                                                  qué se aprendió).
```

### Paso 3 — Si v2.1.2 NO se promueve

El código del Bivariate Poisson permanece en el repositorio porque:
- `predict_full` lo expone como diagnóstico (μ_h, μ_a, σ_diff útiles para análisis post-partido).
- Sirve como base para v2.2.0 (Bivariate Negative Binomial / Zero-Inflated, sobre-dispersión real de NBA).
- La discusión completa enriquece el Capítulo IV (resultados) y Capítulo V (limitaciones / trabajo futuro) de la tesis.

## Qué hacer con el código v2.1.0 actual

Si decides quitarte el costo de `NBABivariatePoisson` del ensemble, una vez decidido tras el ablation, considera:

```python
# src/models/ensemble.py — variante "RF + XGB only"
META_FEATURE_DIM = 2
def _build_meta_features(self, X):
    return np.hstack([
        self.rf.predict_home_win_proba(X).reshape(-1, 1),
        self.xgb.predict_score_diff(X).reshape(-1, 1),
    ])
```

Es esencialmente el código v1.6.0 con StandardScaler añadido al meta-learner.

## Tests automatizados

- `tests/test_poisson_model.py` — 16 tests del modelo Poisson aislado (siguen pasando)
- `tests/test_ensemble_v2_1_2.py` — 5 smoke tests del ensemble v2.1.2 (`META_FEATURE_DIM=4`, Pipeline con StandardScaler, σ_diff > 0, joblib roundtrip)
- `tests/ablation_study.py` — 4 variantes del ensemble en una sola corrida
- `tests/benchmark_v2_1_0.py` — benchmark histórico (mantenido para regression checking)

```bash
python -m unittest tests.test_poisson_model -v
python -m unittest tests.test_ensemble_v2_1_2 -v
python -m tests.ablation_study           # sintético
python -m tests.ablation_study --neon    # contra Neon
```
