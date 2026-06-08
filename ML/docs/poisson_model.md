# Bivariate Poisson Model — `NBABivariatePoisson`

> **Versión:** 2.1.0
> **Implementación:** `ML/src/models/poisson_model.py`
> **Referencia:** Karlis, D. & Ntzoufras, I. (2003). *Analysis of sports data by using bivariate Poisson models.* Journal of the Royal Statistical Society: Series D, 52(3), 381–393.

## 1. Objetivo

Incorporar como tercer base-learner del ensemble un modelo probabilístico de conteo bivariante que capture explícitamente la correlación entre los marcadores del equipo local y visitante, complementando las señales del Random Forest calibrado y del XGBoost regresor.

## 2. Definición del modelo

Sea $X_1$ el marcador del equipo local y $X_2$ el marcador del visitante. Karlis & Ntzoufras (2003) postulan:

$$X_1 = Z_1 + Z_3, \qquad X_2 = Z_2 + Z_3$$

con $Z_1 \sim \text{Poisson}(\lambda_1)$, $Z_2 \sim \text{Poisson}(\lambda_2)$, $Z_3 \sim \text{Poisson}(\lambda_3)$ mutuamente independientes.

### Propiedades inducidas

| Cantidad | Expresión |
|---|---|
| $\mathbb{E}[X_1]$ | $\lambda_1 + \lambda_3$ |
| $\mathbb{E}[X_2]$ | $\lambda_2 + \lambda_3$ |
| $\text{Var}(X_1)$ | $\lambda_1 + \lambda_3$ |
| $\text{Var}(X_2)$ | $\lambda_2 + \lambda_3$ |
| $\text{Cov}(X_1, X_2)$ | $\lambda_3$ |

La componente común $Z_3$ captura la correlación entre marcadores: pace del partido, decisiones arbitrales, fatiga compartida del calendario, ritmo defensivo bidireccional. En NBA, $\lambda_3 > 0$ es habitual porque ambos equipos comparten el contexto del juego.

## 3. Parametrización por features

Las componentes individuales se conectan a las features mediante GLMs de Poisson con log-link:

$$\log(\mathbb{E}[X_1]) = \log(\lambda_1 + \lambda_3) = \beta_{0,h} + \mathbf{X}\boldsymbol{\beta}_h$$

$$\log(\mathbb{E}[X_2]) = \log(\lambda_2 + \lambda_3) = \beta_{0,a} + \mathbf{X}\boldsymbol{\beta}_a$$

Cada GLM se ajusta independientemente con `sklearn.linear_model.PoissonRegressor` (regularización L2 ligera, `alpha = 1e-3`). El pipeline interno es:

```
SimpleImputer(median) → StandardScaler → PoissonRegressor(log-link)
```

La componente común $\lambda_3$ se estima a partir de la covarianza muestral de los residuos en la escala original (estrategia `residual_cov`):

$$\hat{\lambda}_3 = \max\left(0, \min\left(0.95 \cdot \min_i(\hat{\mu}_{h,i}, \hat{\mu}_{a,i}),\ \overline{(X_1 - \hat{\mu}_h)(X_2 - \hat{\mu}_a)}\right)\right)$$

El clipping a `0.95 · min(μ_h, μ_a)` garantiza que $\lambda_1, \lambda_2 > 0$ por construcción.

## 4. Predicción de la probabilidad de victoria

$P(\text{home win}) = P(X_1 > X_2)$. Para escala NBA ($\lambda \approx 100$–$120$), sumar la PMF conjunta sobre $[60, 170]^2$ es prohibitivo en línea (12 100 evaluaciones por partido). Por ello se usa la **aproximación normal con corrección de continuidad** de 0.5:

$$D = X_1 - X_2,\quad \mathbb{E}[D] = \lambda_1 - \lambda_2,\quad \text{Var}(D) = \lambda_1 + \lambda_2 + 2\lambda_3 - 2\lambda_3 = \lambda_1 + \lambda_2$$

$$P(D > 0) \approx 1 - \Phi\!\left(\frac{0.5 - (\lambda_1 - \lambda_2)}{\sqrt{\lambda_1 + \lambda_2}}\right)$$

La justificación es el TLC: para $\lambda \gtrsim 25$ la $\text{Poisson}(\lambda)$ converge rápidamente a $\mathcal{N}(\lambda, \lambda)$. La corrección de 0.5 corrige el sesgo discreto $\to$ continuo y mejora la calibración en muestras pequeñas.

## 5. API pública

```python
from src.models.poisson_model import NBABivariatePoisson

model = NBABivariatePoisson(
    glm_params={"alpha": 1e-3, "max_iter": 500, "tol": 1e-6, "fit_intercept": True},
    lambda3_strategy="residual_cov",   # "zero" para Poisson independiente
)

model.fit(X, y_home_score, y_away_score, feature_names=feature_cols)

# Predicciones
model.predict_home_win_proba(X)   # P(home_win), shape (n,)
model.predict_proba(X)            # [[P(away), P(home)], ...], shape (n, 2)
model.predict(X)                  # 0/1, shape (n,)
model.predict_lambdas(X)          # dict con lambda1, lambda2, lambda3, mu_home, mu_away
model.predict_scores(X)           # (E[X1], E[X2]), shape (n,) cada uno
model.predict_score_diff(X)       # E[X1-X2] = λ1 - λ2
model.predict_total(X)            # E[X1+X2] = λ1 + λ2 + 2λ3
model.predict_margin(X)           # alias de predict_score_diff

# PMF exacta (uso académico — costoso)
model.joint_logpmf(x1, x2, λ1, λ2, λ3)
model.home_win_proba_exact(X, score_min=60, score_max=170)

# Persistencia
model.save("poisson.joblib")
NBABivariatePoisson.load("poisson.joblib")
```

## 6. Integración con el ensemble

`NBAEnsemble` v2.1.0 añade el Poisson como tercer base-learner. El meta-vector pasa de 2D a 3D:

| Versión | Meta-features |
|---|---|
| v1.6.0 | `[rf_proba, score_diff]` |
| **v2.1.0** | **`[rf_proba, score_diff, poisson_proba]`** |

El stacking sigue siendo OOF temporal con K=5 folds y calibración isotónica sobre las predicciones OOF, lo que evita data leakage tanto del meta-learner como del calibrador.

## 7. Limitaciones del modelo Bivariate Poisson en NBA

1. **Sub-dispersión asumida.** Bajo Poisson, $\text{Var}(X_i) = \mathbb{E}[X_i]$. La varianza real de los scores NBA suele ser ligeramente mayor (sobre-dispersión leve por garbage time, `blowouts`, ritmo variable). Esto no rompe el modelo, pero produce intervalos de confianza ligeramente apretados.
2. **Covarianza positiva forzada.** Como $\text{Cov}(X_1, X_2) = \lambda_3 \geq 0$, el modelo no puede representar partidos antagónicos en los que un equipo "controla el reloj" para deprimir el marcador del rival (correlación negativa).
3. **Independencia condicional de innings.** No modeliza dinámica intra-partido (cuartos, momentum runs).

Estas limitaciones se compensan en el ensemble: el RF y el XGBoost son no paramétricos y absorben las desviaciones del supuesto Poisson; el meta-learner aprende cuánto pesar cada señal.

## 8. Tests

- `ML/tests/test_poisson_model.py` — 16 tests unitarios (correctitud matemática, rango de salidas, persistencia, edge cases, normalización de la PMF, calidad predictiva).
- `ML/tests/test_ensemble_v2_1_0.py` — 4 smoke tests (`META_FEATURE_DIM=3`, entrenamiento end-to-end, `predict_full` con señales del Poisson, joblib roundtrip compatible con `prediction_service.py`).
- `ML/tests/benchmark_v2_1_0.py` — benchmark contra dataset sintético NBA-realista.

Ejecutar:

```bash
cd ML
python -m unittest tests.test_poisson_model -v
python -m unittest tests.test_ensemble_v2_1_0 -v
python tests/benchmark_v2_1_0.py
```

## 9. Próximos pasos

- Variante **Zero-Inflated Bivariate Poisson** si la sobre-dispersión empírica lo justifica.
- Variante **Bivariate Negative Binomial** (Famoye 2010) para modelar sobre-dispersión sin violar la estructura bivariante.
- $\lambda_3$ dependiente de features (e.g. `pace_diff`, `back_to_back`) en lugar de constante global.
