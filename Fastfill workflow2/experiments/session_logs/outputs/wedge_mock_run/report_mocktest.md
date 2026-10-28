# LM-assisted weakness discovery — verdict report

episodes: 655, overall SR 51.6%. candidates so far: 6, accepted: 2.

## round 0 — `feature_geodesic_squared` — **ACCEPTED**
hypothesis: Squared shortest-path distance amplifies the long-range difficulty.

```json
{
 "coverage": {
  "coverage": 1.0,
  "errors": {}
 },
 "redundancy": {
  "max_abs_spearman": 0.0,
  "vs": null
 },
 "predictive": {
  "train": {
   "sr_low_tertile": 66.9,
   "sr_high_tertile": 32.7,
   "gap_pp": 34.2,
   "z": 5.99,
   "p": 0.0,
   "n_lo": 154,
   "n_hi": 153
  },
  "holdout": {
   "gap_pp": 40.4,
   "n_lo": 74,
   "n_hi": 57
  }
 },
 "incremental": {
  "auc_library": 0.5,
  "auc_with_candidate": 0.6802,
  "delta_auc": 0.1802
 }
}
```

## round 0 — `feature_phantom_field` — **REJECTED**
hypothesis: Window count in the target room reduces visual clutter.

reason: unknown field / code crashed (KeyError: 'numWindows')

```json
{
 "coverage": {
  "coverage": 0.0,
  "reason": "unknown field / code crashed (KeyError: 'numWindows')"
 }
}
```

## round 0 — `feature_loops_forever` — **REJECTED**
hypothesis: Iterative refinement of difficulty score.

reason: code failed to execute (timeout)

```json
{
 "coverage": {
  "coverage": 0.0,
  "reason": "code failed to execute (timeout)"
 }
}
```

## round 0 — `feature_always_one` — **REJECTED**
hypothesis: Every episode happens in a house.

reason: constant feature

```json
{
 "coverage": {
  "coverage": 1.0,
  "errors": {},
  "reason": "constant feature"
 }
}
```

## round 0 — `feature_target_room_relative_size` — **REJECTED**
hypothesis: Small target room relative to the whole house makes the target easy to miss.

reason: AUC gain insufficient (-0.0042)

```json
{
 "coverage": {
  "coverage": 1.0,
  "errors": {}
 },
 "redundancy": {
  "max_abs_spearman": -0.249,
  "vs": "feature_geodesic_squared"
 },
 "predictive": {
  "train": {
   "sr_low_tertile": 36.6,
   "sr_high_tertile": 62.7,
   "gap_pp": -26.1,
   "z": -4.57,
   "p": 0.0,
   "n_lo": 153,
   "n_hi": 153
  },
  "holdout": {
   "gap_pp": -13.7,
   "n_lo": 49,
   "n_hi": 83
  }
 },
 "incremental": {
  "auc_library": 0.6802,
  "auc_with_candidate": 0.676,
  "delta_auc": -0.0042,
  "reason": "AUC gain insufficient (-0.0042)"
 }
}
```

## round 0 — `feature_search_burden` — **ACCEPTED**
hypothesis: Meters of path the agent must cover before the target can first be seen.

```json
{
 "coverage": {
  "coverage": 0.957,
  "errors": {
   "nan/inf": 28
  }
 },
 "redundancy": {
  "max_abs_spearman": 0.534,
  "vs": "feature_geodesic_squared"
 },
 "predictive": {
  "train": {
   "sr_low_tertile": 64.8,
   "sr_high_tertile": 24.7,
   "gap_pp": 40.2,
   "z": 8.06,
   "p": 0.0,
   "n_lo": 290,
   "n_hi": 154
  },
  "holdout": {
   "gap_pp": 28.4,
   "n_lo": 129,
   "n_hi": 64
  }
 },
 "incremental": {
  "auc_library": 0.6802,
  "auc_with_candidate": 0.7449,
  "delta_auc": 0.0647
 }
}
```

