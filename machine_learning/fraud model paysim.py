import warnings
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings('ignore')


def engineer_features(df):
    print("\n Engineering features...")

    df['balance_error_orig'] = (
        df['newbalanceOrig'] - df['oldbalanceOrg'] + df['amount']
    )
    df['balance_error_dest'] = (
        df['newbalanceDest'] - df['oldbalanceDest'] - df['amount']
    )

    df['orig_account_drained'] = (
        (df['oldbalanceOrg'] > 0) & (df['newbalanceOrig'] == 0)
    ).astype(int)

    df['is_large_transaction'] = (
        df['amount'] > df['amount'].quantile(0.95)
    ).astype(int)

    df['dest_was_empty'] = (df['oldbalanceDest'] == 0).astype(int)
    df['hour'] = df['step'] % 24
    df['is_peak_hour'] = df['hour'].isin([0, 1, 2, 3, 4, 22, 23]).astype(int)

    le = LabelEncoder()
    df['type_encoded'] = le.fit_transform(df['type'])

    print("    Features engineered")
    return df


def prepare_features(df):
    feature_cols = [
        'amount',
        'oldbalanceOrg',
        'newbalanceOrig',
        'oldbalanceDest',
        'newbalanceDest',
        'balance_error_orig',
        'balance_error_dest',
        'orig_account_drained',
        'is_large_transaction',
        'dest_was_empty',
        'hour',
        'is_peak_hour',
        'type_encoded',
    ]

    X = df[feature_cols]
    y = df['isFraud']
    return X, y


def train_models(X_train, X_test, y_train, y_test):
    results = {}

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

    print(f"    AUC Score: {lr_auc:.4f}")
    print(classification_report(y_test, lr_preds, target_names=['Legitimate', 'Fraud']))
    results['logistic_regression'] = {
        'model': lr, 'auc': lr_auc
    }

    print("\n🌲 Training Random Forest...")
    rf = RandomForestClassifier(
        n_estimators=100,
        class_weight='balanced',
        max_depth=10,
        min_samples_leaf=10,
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)
    rf_preds = rf.predict(X_test)
    rf_probs = rf.predict_proba(X_test)[:, 1]
    rf_auc   = roc_auc_score(y_test, rf_probs)

    print(f"    AUC Score: {rf_auc:.4f}")
    print(classification_report(y_test, rf_preds, target_names=['Legitimate', 'Fraud']))
    results['random_forest'] = {
        'model': rf, 'auc': rf_auc
    }

    return results


def feature_importance(rf_model, feature_cols):
    print("\n Top Fraud Detection Features:")
    importances = pd.Series(
        rf_model.feature_importances_,
        index=feature_cols
    ).sort_values(ascending=False)

    for feat, score in importances.items():
        bar = '█' * int(score * 100)
        print(f"   {feat:<25} {score:.4f}  {bar}")


def main():
    print("🛡️  ZimFraudGuard — PaySim Fraud Detection\n")

    print("📦 Loading PaySim dataset...")
    df = pd.read_csv('PS_20174392719_1491204439457_log.csv')

    print("Columns found:")
    print(df.columns.tolist())
    print("\nFirst 2 rows:")
    print(df.head(2))

    df = engineer_features(df)
    X, y = prepare_features(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    print(f"\n Training set : {len(X_train):,} transactions")
    print(f" Test set     : {len(X_test):,} transactions")
    print(f" Fraud in test: {y_test.sum():,} cases")

    results = train_models(X_train, X_test, y_train, y_test)

    feature_importance(
        results['random_forest']['model'],
        X.columns.tolist()
    )

    print("\n Model Comparison:")
    print(f"   Logistic Regression AUC : {results['logistic_regression']['auc']:.4f}")
    print(f"   Random Forest AUC       : {results['random_forest']['auc']:.4f}")


if __name__ == "__main__":
    main()