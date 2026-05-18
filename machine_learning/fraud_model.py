import pandas as pd
import numpy as np
from db_connection import get_engine
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (classification_report,
                             roc_auc_score,
                             confusion_matrix)
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings('ignore')

def load_data():
    """Load transactions with fraud labels from PostgreSQL"""
    print("📦 Loading data from PostgreSQL...")
    engine = get_engine()

    query = """
        SELECT
            t.transaction_id,
            t.amount,
            t.currency,
            t.transaction_type,
            t.channel,
            t.status,
            EXTRACT(HOUR  FROM t.transaction_timestamp) AS hour,
            EXTRACT(DOW   FROM t.transaction_timestamp) AS day_of_week,
            EXTRACT(MONTH FROM t.transaction_timestamp) AS month,
            a_sender.network                            AS network,
            c_sender.kyc_level                          AS kyc_level,
            c_sender.sim_swap_count                     AS sim_swap_count,
            d.is_flagged                                AS device_flagged,
            l.risk_score                                AS location_risk,
            l.urban_rural                               AS urban_rural,
            fl.is_fraud
        FROM transactions t
        JOIN accounts  a_sender  ON t.sender_account_id  = a_sender.account_id
        JOIN customers c_sender  ON a_sender.customer_id = c_sender.customer_id
        JOIN locations l         ON c_sender.location_id = l.location_id
        LEFT JOIN devices d      ON t.device_id          = d.device_id
        JOIN fraud_labels fl     ON t.transaction_id     = fl.transaction_id
    """

    df = pd.read_sql(query, engine)
    print(f"   ✅ Loaded {len(df):,} transactions")
    print(f"   ✅ Fraud cases: {df['is_fraud'].sum():,}")
    print(f"   ✅ Fraud rate:  {df['is_fraud'].mean()*100:.2f}%")
    return df

def engineer_features(df):
    """Create features for the ML model"""
    print("\n🔧 Engineering features...")

    # Weekend flag — fraud spikes on weekends
    df['is_weekend'] = df['day_of_week'].isin([0, 6]).astype(int)

    # SIM swap risk flag
    df['sim_swap_risk'] = (df['sim_swap_count'] > 0).astype(int)

    # Encode categorical columns
    le = LabelEncoder()
    df['currency_encoded']          = le.fit_transform(df['currency'])
    df['transaction_type_encoded']  = le.fit_transform(df['transaction_type'])
    df['channel_encoded']           = le.fit_transform(df['channel'])
    df['network_encoded']           = le.fit_transform(df['network'])
    df['urban_rural_encoded']       = le.fit_transform(df['urban_rural'])
    df['device_flagged_encoded']    = df['device_flagged'].astype(int)

    print("   ✅ Features engineered")
    return df

def prepare_features(df):
    """Select final feature columns"""
    feature_cols = [
        'amount',
        'hour',
        'day_of_week',
        'month',
        'kyc_level',
        'sim_swap_count',
        'location_risk',
        'is_weekend',
        'sim_swap_risk',
        'currency_encoded',
        'transaction_type_encoded',
        'channel_encoded',
        'network_encoded',
        'urban_rural_encoded',
        'device_flagged_encoded',
    ]

    X = df[feature_cols]
    y = df['is_fraud'].astype(int)
    return X, y

def train_models(X_train, X_test, y_train, y_test):
    """Train Logistic Regression and Random Forest"""

    results = {}

    # ── Model 1: Logistic Regression ───────────────────────────
    print("\n🤖 Training Logistic Regression...")
    lr = LogisticRegression(
        class_weight='balanced',
        max_iter=1000,
        random_state=42
    )
    lr.fit(X_train, y_train)
    lr_preds = lr.predict(X_test)
    lr_probs = lr.predict_proba(X_test)[:, 1]
    lr_auc   = roc_auc_score(y_test, lr_probs)

    print(f"   ✅ AUC Score: {lr_auc:.4f}")
    print(classification_report(y_test, lr_preds,
          target_names=['Legitimate', 'Fraud']))
    results['logistic_regression'] = {
        'model': lr, 'auc': lr_auc, 'probs': lr_probs
    }

    # ── Model 2: Random Forest ──────────────────────────────────
    print("\n🌲 Training Random Forest...")
    rf = RandomForestClassifier(
        n_estimators=100,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)
    rf_preds = rf.predict(X_test)
    rf_probs = rf.predict_proba(X_test)[:, 1]
    rf_auc   = roc_auc_score(y_test, rf_probs)

    print(f"   ✅ AUC Score: {rf_auc:.4f}")
    print(classification_report(y_test, rf_preds,
          target_names=['Legitimate', 'Fraud']))
    results['random_forest'] = {
        'model': rf, 'auc': rf_auc, 'probs': rf_probs
    }

    return results

def feature_importance(rf_model, feature_cols):
    """Print top fraud detection features"""
    print("\n📊 Top Fraud Detection Features:")
    importances = pd.Series(
        rf_model.feature_importances_,
        index=feature_cols
    ).sort_values(ascending=False)

    for feat, score in importances.items():
        bar = '█' * int(score * 200)
        print(f"   {feat:<30} {score:.4f}  {bar}")

def main():
    print("🛡️  ZimFraudGuard — Fraud Detection Model\n")

    # Load and prepare data
    df       = load_data()
    df       = engineer_features(df)
    X, y     = prepare_features(df)

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n📊 Training set : {len(X_train):,} transactions")
    print(f"📊 Test set     : {len(X_test):,} transactions")

    # Train models
    results = train_models(X_train, X_test, y_train, y_test)

    # Feature importance from Random Forest
    feature_cols = X.columns.tolist()
    feature_importance(
        results['random_forest']['model'],
        feature_cols
    )

    # Final comparison
    print("\n🏆 Model Comparison:")
    print(f"   Logistic Regression AUC : "
          f"{results['logistic_regression']['auc']:.4f}")
    print(f"   Random Forest AUC       : "
          f"{results['random_forest']['auc']:.4f}")

if __name__ == "__main__":
    main()