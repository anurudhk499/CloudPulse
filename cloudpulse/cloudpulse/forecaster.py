"""Load forecasting: predict load[t + boot_steps] from load[:t] (+ clock features).
Training uses ONLY the first 70% of the trace (time split, no shuffling, no leakage)."""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

LAGS = 12


def make_features(load, boot, step_min, start_ts):
    s = pd.Series(np.asarray(load, dtype=float))
    X = pd.DataFrame({f"lag{k}": s.shift(k + 1) for k in range(LAGS)})  # lag0 = load[t-1]
    X["ma3"] = X[["lag0", "lag1", "lag2"]].mean(axis=1)
    X["ma12"] = X[[f"lag{k}" for k in range(LAGS)]].mean(axis=1)
    X["trend"] = X["lag0"] - X["lag3"]
    idx = np.arange(len(s)) + boot  # clock features of the TARGET time (known in advance)
    minutes = (start_ts.dayofweek * 1440 + start_ts.hour * 60 + start_ts.minute) + idx * step_min
    tod = (minutes % 1440) / 1440
    X["tod_sin"], X["tod_cos"] = np.sin(2 * np.pi * tod), np.cos(2 * np.pi * tod)
    X["weekend"] = (((minutes // 1440) % 7) >= 5).astype(int)
    y = s.shift(-boot)
    return X, y


class Forecasters:
    def __init__(self, base_load, start_ts, step_min, boot, split, seed=42):
        self.boot, self.step_min, self.start_ts, self.split = boot, step_min, start_ts, split
        X, y = make_features(base_load, boot, step_min, start_ts)
        self.train_idx = np.arange(LAGS, split - boot)  # every target lies inside the train period
        Xt, yt = X.iloc[self.train_idx], y.iloc[self.train_idx]
        self.rf = RandomForestRegressor(n_estimators=150, min_samples_leaf=3,
                                        random_state=seed, n_jobs=-1).fit(Xt, yt)
        self.ridge = make_pipeline(StandardScaler(), Ridge(alpha=1.0)).fit(Xt, yt)

    def predict_rf(self, load):
        X, _ = make_features(load, self.boot, self.step_min, self.start_ts)
        preds = np.full(len(load), np.nan)
        ok = X.notna().all(axis=1).values
        preds[ok] = self.rf.predict(X[ok])
        return preds

    def evaluate(self, load):
        """MAE / RMSE / R2 on the TEST segment only, for each forecaster."""
        X, y = make_features(load, self.boot, self.step_min, self.start_ts)
        rows = np.arange(self.split, len(load) - self.boot)
        Xe, ye = X.iloc[rows], y.iloc[rows].values
        cands = {
            "Last value (naive)": Xe["lag0"].values,
            "Moving average (3)": Xe["ma3"].values,
            "Ridge regression": self.ridge.predict(Xe),
            "Random Forest": self.rf.predict(Xe),
        }
        return [{"model": k,
                 "mae": round(float(mean_absolute_error(ye, p)), 1),
                 "rmse": round(float(np.sqrt(mean_squared_error(ye, p))), 1),
                 "r2": round(float(r2_score(ye, p)), 3)} for k, p in cands.items()]
