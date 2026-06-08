"""
Modelo Bivariate Poisson (Karlis & Ntzoufras, 2003) para predicción NBA.

Modelo
------
    X1 = Z1 + Z3        (puntos del equipo local)
    X2 = Z2 + Z3        (puntos del equipo visitante)

donde Z1 ~ Poisson(λ1), Z2 ~ Poisson(λ2) y Z3 ~ Poisson(λ3) son independientes.
La componente común Z3 captura la correlación entre ambos marcadores
(p. ej. ritmo del partido, decisiones arbitrales, fatiga compartida).

Propiedades:
    E[X1] = λ1 + λ3        Var(X1) = λ1 + λ3
    E[X2] = λ2 + λ3        Var(X2) = λ2 + λ3
    Cov(X1, X2) = λ3       (siempre ≥ 0)

Parametrización por features
----------------------------
Cada λ es modelado mediante un GLM Poisson con log-link:

    log(λ1 + λ3) = β0_h + Xβ_h           # GLM home_score
    log(λ2 + λ3) = β0_a + Xβ_a           # GLM away_score
    λ3            = max(0, ĉov_residual)  # constante global ≥ 0

Es decir, los regresores Poisson estiman directamente las medias marginales
E[X1] y E[X2], y luego se descompone en (λ1, λ2, λ3) imponiendo que
λ_marginal = λ_individual + λ3 con λ3 común y constante.

Para garantizar λ1, λ2 > 0 se clipea λ3 a min(λ_h, λ_a) * 0.95.

Predicción de P(home_win)
-------------------------
P(home_win) = P(X1 > X2). Para NBA los marcadores son grandes (λ ≈ 100-120),
por lo que la aproximación normal con corrección de continuidad es precisa
y mucho más eficiente que sumar la PMF conjunta sobre [70, 160]^2:

    D = X1 - X2,   E[D] = λ1 - λ2,   Var(D) = λ1 + λ2 + 2λ3 - 2λ3 = λ1 + λ2
    Nota: Cov(X1, X2) = λ3, por lo tanto Var(X1-X2) = (λ1+λ3) + (λ2+λ3) - 2λ3
                                                      = λ1 + λ2.

    P(D > 0) ≈ 1 - Φ((0.5 - (λ1 - λ2)) / √(λ1 + λ2))    # con corrección de 0.5

La corrección de continuidad de 0.5 corrige el sesgo de aproximar una
distribución discreta con una continua y mejora la calibración en muestras
pequeñas.

Referencias
-----------
Karlis, D. & Ntzoufras, I. (2003). "Analysis of sports data by using
bivariate Poisson models". Journal of the Royal Statistical Society:
Series D (The Statistician), 52(3), 381-393.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm
from sklearn.linear_model import PoissonRegressor
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler


# Hiperparámetros por defecto del GLM Poisson
DEFAULT_GLM_PARAMS = {
    "alpha": 1e-3,        # regularización L2 ligera
    "max_iter": 500,
    "tol": 1e-6,
    "fit_intercept": True,
}

# Rango realista para clipear λ marginales NBA (puntos esperados por equipo)
LAMBDA_MIN = 60.0
LAMBDA_MAX = 160.0

# Fracción máxima del λ marginal mínimo que puede tomar λ3 (componente común).
# Vuelta a 0.95 en v2.1.2: el problema de overconfidence resultó ser
# arquitectónico (poisson_proba como meta-feature), no tanto λ3 inflado.
# El parche de v2.1.1 (cap 0.30 + shrinkage) se descarta para no introducir
# ajustes ad-hoc sin evidencia empírica de que ayuden tras la reformulación.
LAMBDA3_SAFETY_FACTOR = 0.95
LAMBDA3_SHRINKAGE = 1.0


class NBABivariatePoisson:
    """
    Modelo Bivariate Poisson para predicción simultánea de:
        - probabilidad de victoria local: P(home_win)
        - puntuación esperada local y visitante
        - margen y total esperados

    El modelo expone la misma interfaz que NBARandomForest / NBAXGBoost,
    de forma que pueda ser usado como tercer base-learner del NBAEnsemble.
    """

    def __init__(self, glm_params: dict | None = None,
                 lambda3_strategy: str = "residual_cov"):
        """
        Args:
            glm_params:        hiperparámetros para PoissonRegressor (alpha, ...)
            lambda3_strategy:  "residual_cov" → λ3 estimado de la covarianza
                               de los residuos (recomendado).
                               "zero" → λ3 = 0 (modelo Poisson independiente).
        """
        self.glm_params = glm_params or DEFAULT_GLM_PARAMS
        self.lambda3_strategy = lambda3_strategy

        self.home_pipeline: Pipeline | None = None
        self.away_pipeline: Pipeline | None = None
        self.lambda3_: float = 0.0
        self.feature_names: list[str] | None = None
        self.is_fitted: bool = False

    # ------------------------------------------------------------------
    # Construcción de pipelines
    # ------------------------------------------------------------------

    def _build_pipeline(self) -> Pipeline:
        """Imputer (median) → StandardScaler → PoissonRegressor (log-link)."""
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("glm", PoissonRegressor(**self.glm_params)),
        ])

    # ------------------------------------------------------------------
    # Entrenamiento
    # ------------------------------------------------------------------

    def fit(self, X, y_home: np.ndarray, y_away: np.ndarray,
            feature_names: list | None = None):
        """
        Ajusta dos GLMs Poisson independientes para home_score y away_score
        y luego estima la componente común λ3 desde la covarianza de los
        residuos.

        Args:
            X:             matriz de features
            y_home:        marcador real del equipo local (entero ≥ 0)
            y_away:        marcador real del equipo visitante (entero ≥ 0)
            feature_names: lista opcional de nombres
        """
        self.feature_names = feature_names

        y_home = np.asarray(y_home, dtype=float)
        y_away = np.asarray(y_away, dtype=float)

        if (y_home < 0).any() or (y_away < 0).any():
            raise ValueError("Los marcadores no pueden ser negativos.")

        self.home_pipeline = self._build_pipeline()
        self.away_pipeline = self._build_pipeline()

        self.home_pipeline.fit(X, y_home)
        self.away_pipeline.fit(X, y_away)

        # Estimación de λ3 (v2.1.1: shrinkage + cap conservador)
        if self.lambda3_strategy == "zero":
            self.lambda3_ = 0.0
        else:
            mu_home = np.clip(self.home_pipeline.predict(X), LAMBDA_MIN, LAMBDA_MAX)
            mu_away = np.clip(self.away_pipeline.predict(X), LAMBDA_MIN, LAMBDA_MAX)
            res_home = y_home - mu_home
            res_away = y_away - mu_away
            cov_res = float(np.mean(res_home * res_away))
            # Shrinkage para evitar covarianzas residuales infladas por outliers
            cov_res_shrunk = cov_res * LAMBDA3_SHRINKAGE
            # λ3 ∈ [0, 0.30 * min(μ_h, μ_a)] para mantener λ1, λ2 > 0 y
            # evitar que la varianza de D = X1-X2 se contraiga demasiado.
            mu_min = float(np.min(np.minimum(mu_home, mu_away)))
            lambda3_max = LAMBDA3_SAFETY_FACTOR * mu_min
            self.lambda3_ = float(np.clip(cov_res_shrunk, 0.0, lambda3_max))

        self.is_fitted = True
        return self

    # ------------------------------------------------------------------
    # Predicciones internas
    # ------------------------------------------------------------------

    def _check_fitted(self):
        if not self.is_fitted:
            raise RuntimeError(
                "NBABivariatePoisson no ha sido entrenado. "
                "Llamar a .fit() primero."
            )

    def predict_lambdas(self, X) -> dict:
        """
        Retorna {'lambda1': λ1, 'lambda2': λ2, 'lambda3': λ3,
                 'mu_home': λ1+λ3, 'mu_away': λ2+λ3}.

        Cada array tiene shape (n_samples,).
        """
        self._check_fitted()
        mu_home = np.clip(self.home_pipeline.predict(X), LAMBDA_MIN, LAMBDA_MAX)
        mu_away = np.clip(self.away_pipeline.predict(X), LAMBDA_MIN, LAMBDA_MAX)

        # λ3 efectivo por muestra: clipped a 0.95 * min(μ_h_i, μ_a_i) para
        # garantizar λ1_i, λ2_i > 0 incluso si la media marginal es baja.
        lambda3_per_sample = np.minimum(
            self.lambda3_,
            LAMBDA3_SAFETY_FACTOR * np.minimum(mu_home, mu_away)
        )
        lambda1 = mu_home - lambda3_per_sample
        lambda2 = mu_away - lambda3_per_sample

        return {
            "lambda1": lambda1,
            "lambda2": lambda2,
            "lambda3": lambda3_per_sample,
            "mu_home": mu_home,
            "mu_away": mu_away,
        }

    # ------------------------------------------------------------------
    # API pública (compatible con NBARandomForest / NBAXGBoost)
    # ------------------------------------------------------------------

    def predict_home_win_proba(self, X) -> np.ndarray:
        """
        P(X1 > X2) con aproximación normal y corrección de continuidad 0.5.

        D = X1 - X2 ~ aprox. Normal(λ1 - λ2, σ²)
            σ² = Var(X1) + Var(X2) - 2 Cov(X1, X2)
               = (λ1 + λ3) + (λ2 + λ3) - 2 λ3
               = λ1 + λ2

        P(D > 0) ≈ 1 - Φ((0.5 - (λ1 - λ2)) / σ)
        """
        lambdas = self.predict_lambdas(X)
        lambda1 = lambdas["lambda1"]
        lambda2 = lambdas["lambda2"]

        sigma = np.sqrt(np.clip(lambda1 + lambda2, 1e-9, None))
        mean_diff = lambda1 - lambda2
        z = (0.5 - mean_diff) / sigma
        proba = 1.0 - norm.cdf(z)
        # Clipping numérico para log-loss
        return np.clip(proba, 1e-6, 1.0 - 1e-6)

    def predict_proba(self, X) -> np.ndarray:
        """
        Retorna [[P(away_win), P(home_win)], ...] para compatibilidad con
        clasificadores sklearn.
        """
        p_home = self.predict_home_win_proba(X)
        return np.column_stack([1.0 - p_home, p_home])

    def predict(self, X) -> np.ndarray:
        """Clase predicha (0 = away gana, 1 = home gana)."""
        return (self.predict_home_win_proba(X) >= 0.5).astype(int)

    def predict_scores(self, X) -> tuple[np.ndarray, np.ndarray]:
        """Retorna (E[X1], E[X2]) clipeado a rango NBA."""
        lambdas = self.predict_lambdas(X)
        return lambdas["mu_home"], lambdas["mu_away"]

    def predict_score_diff(self, X) -> np.ndarray:
        """Retorna E[X1 - X2] = λ1 - λ2."""
        lambdas = self.predict_lambdas(X)
        return lambdas["lambda1"] - lambdas["lambda2"]

    def predict_total(self, X) -> np.ndarray:
        """Retorna E[X1 + X2] = λ1 + λ2 + 2λ3."""
        lambdas = self.predict_lambdas(X)
        return lambdas["lambda1"] + lambdas["lambda2"] + 2.0 * lambdas["lambda3"]

    def predict_margin(self, X) -> np.ndarray:
        """Alias de predict_score_diff: margen esperado (home - away)."""
        return self.predict_score_diff(X)

    # ------------------------------------------------------------------
    # PMF conjunta (uso académico / validación)
    # ------------------------------------------------------------------

    def joint_logpmf(self, x1: int, x2: int,
                     lambda1: float, lambda2: float, lambda3: float) -> float:
        """
        log P(X1=x1, X2=x2) bajo Bivariate Poisson.

            P(x1, x2) = e^{-(λ1+λ2+λ3)}
                        · (λ1^x1 / x1!) · (λ2^x2 / x2!)
                        · Σ_{k=0}^{min(x1,x2)} C(x1,k) C(x2,k) k! · (λ3 / (λ1 λ2))^k

        Retorna -inf si x1 < 0 o x2 < 0.

        Implementación numéricamente estable usando logaritmos.
        Útil para validación académica; para inferencia masiva se usa la
        aproximación normal en predict_home_win_proba.
        """
        from scipy.special import gammaln, logsumexp

        if x1 < 0 or x2 < 0:
            return float("-inf")

        lambda1 = max(lambda1, 1e-12)
        lambda2 = max(lambda2, 1e-12)
        lambda3 = max(lambda3, 0.0)

        base = (
            -(lambda1 + lambda2 + lambda3)
            + x1 * np.log(lambda1) - gammaln(x1 + 1)
            + x2 * np.log(lambda2) - gammaln(x2 + 1)
        )

        if lambda3 == 0.0:
            return float(base)

        kmax = int(min(x1, x2))
        ks = np.arange(kmax + 1)
        # log de C(x1,k) · C(x2,k) · k! · (λ3 / (λ1 λ2))^k
        log_terms = (
            gammaln(x1 + 1) - gammaln(ks + 1) - gammaln(x1 - ks + 1)
            + gammaln(x2 + 1) - gammaln(ks + 1) - gammaln(x2 - ks + 1)
            + gammaln(ks + 1)
            + ks * (np.log(lambda3) - np.log(lambda1) - np.log(lambda2))
        )
        return float(base + logsumexp(log_terms))

    def home_win_proba_exact(self, X, score_min: int = 60, score_max: int = 170) -> np.ndarray:
        """
        P(home_win) calculada exactamente sumando la PMF conjunta sobre
        [score_min, score_max]^2. Mucho más lento que la aproximación
        normal, expuesto sólo para verificación académica.

        Solo válido para X de pocas filas (típicamente n < 100).
        """
        self._check_fitted()
        lambdas = self.predict_lambdas(X)
        n = len(lambdas["lambda1"])
        out = np.zeros(n)

        for i in range(n):
            l1 = lambdas["lambda1"][i]
            l2 = lambdas["lambda2"][i]
            l3 = lambdas["lambda3"][i]
            log_p_grid = np.full((score_max - score_min + 1,
                                  score_max - score_min + 1), -np.inf)
            for x in range(score_min, score_max + 1):
                for y in range(score_min, score_max + 1):
                    log_p_grid[x - score_min, y - score_min] = self.joint_logpmf(
                        x, y, l1, l2, l3
                    )
            # Normalizar (la suma debería ser ≈ 1 si el rango es suficiente)
            from scipy.special import logsumexp
            log_norm = logsumexp(log_p_grid)
            p_grid = np.exp(log_p_grid - log_norm)

            # P(home > away) = suma triangular superior estricta
            mask_home_win = np.tri(p_grid.shape[0], p_grid.shape[1], k=-1).T.astype(bool)
            out[i] = float(p_grid[mask_home_win].sum())

        return out

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------

    def save(self, path: str):
        import joblib
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: str) -> "NBABivariatePoisson":
        import joblib
        return joblib.load(path)
