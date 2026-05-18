import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import random
from db_connection import get_connection

fake = Faker()
random.seed(42)
np.random.seed(42)

# ── Real POTRAZ Q2 2025 market shares ──────────────────────────
NETWORK_WEIGHTS = {
    'EcoCash':  0.7323,
    'OneMoney': 0.2478,
    'Telecel':  0.0199
}

# ── Real Zimbabwe provinces with risk scores from our DB ────────
PROVINCES = [
    ('Harare',             7.80, 'urban'),
    ('Bulawayo',           6.20, 'urban'),
    ('Manicaland',         5.40, 'urban'),
    ('Mashonaland East',   4.90, 'urban'),
    ('Mashonaland West',   4.70, 'urban'),
    ('Midlands',           5.10, 'urban'),
    ('Masvingo',           4.30, 'urban'),
    ('Matabeleland North', 3.80, 'rural'),
    ('Matabeleland South', 5.60, 'rural'),
    ('Mashonaland Central',3.50, 'rural'),
]

# ── Transaction types and their fraud probability ───────────────
TRANSACTION_TYPES = {
    'send_money':       0.35,
    'cash_out':         0.25,
    'cash_in':          0.15,
    'bill_payment':     0.15,
    'merchant_payment': 0.10,
}

# ── Fraud rates by type — calibrated to RBZ 2024 medium risk ───
FRAUD_RATES = {
    'send_money':       0.03,
    'cash_out':         0.04,
    'cash_in':          0.01,
    'bill_payment':     0.005,
    'merchant_payment': 0.008,
}

# ── Peak fraud hours — Zimbabwe specific ───────────────────────
# Fraud spikes: lunch hour, evening, late night
FRAUD_PEAK_HOURS = [12, 13, 18, 19, 20, 21, 22, 23]
NORMAL_HOURS     = list(range(7, 12)) + [14, 15, 16, 17]

def generate_phone_number():
    """Generate realistic Zimbabwe mobile numbers"""
    prefixes = ['077', '078', '071', '073', '072']
    prefix = random.choices(
        prefixes,
        weights=[0.45, 0.30, 0.15, 0.05, 0.05]
    )[0]
    return prefix + str(random.randint(1000000, 9999999))

def generate_amount(transaction_type, is_fraud):
    """
    Generate realistic transaction amounts
    Calibrated to Zimbabwe mobile money patterns
    """
    if is_fraud:
        # Fraud transactions cluster around round numbers
        # and often just below detection thresholds
        if transaction_type == 'send_money':
            return round(random.uniform(200, 999), 2)
        elif transaction_type == 'cash_out':
            return round(random.uniform(300, 1500), 2)
        else:
            return round(random.uniform(50, 500), 2)
    else:
        # Normal transactions — right-skewed distribution
        # Most are small, few are large
        if transaction_type == 'send_money':
            return round(np.random.exponential(scale=45), 2)
        elif transaction_type == 'cash_out':
            return round(np.random.exponential(scale=60), 2)
        elif transaction_type == 'cash_in':
            return round(np.random.exponential(scale=80), 2)
        elif transaction_type == 'bill_payment':
            return round(random.uniform(5, 150), 2)
        else:
            return round(np.random.exponential(scale=25), 2)

def generate_timestamp(is_fraud):

    # Random date in 2024
    start_date = datetime(2024, 1, 1)
    random_days = random.randint(0, 364)
    base_date   = start_date + timedelta(days=random_days)

    if is_fraud:
        hour   = random.choice(FRAUD_PEAK_HOURS)
    else:
        hour   = random.choice(NORMAL_HOURS)

    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    return base_date.replace(hour=hour, minute=minute, second=second)

def assign_fraud_type(transaction_type):

    fraud_map = {
        'send_money':       ['wrong_number_scam', 'account_takeover'],
        'cash_out':         ['sim_swap', 'account_takeover', 'pin_phishing'],
        'cash_in':          ['agent_fraud'],
        'bill_payment':     ['pin_phishing', 'account_takeover'],
        'merchant_payment': ['account_takeover', 'pin_phishing'],
    }
    return random.choice(fraud_map[transaction_type])

def generate_transactions(n=100000):

    print(f" Generating {n:,} transactions...")

    transactions = []

    for i in range(n):
        # Pick transaction type
        tx_type = random.choices(
            list(TRANSACTION_TYPES.keys()),
            weights=list(TRANSACTION_TYPES.values())
        )[0]

        # Determine if fraud
        is_fraud = random.random() < FRAUD_RATES[tx_type]

        # Pick network — weighted by real POTRAZ market share
        network = random.choices(
            list(NETWORK_WEIGHTS.keys()),
            weights=list(NETWORK_WEIGHTS.values())
        )[0]

        # Pick currency — 80% USD, 20% ZiG (from RBZ 2024)
        currency = random.choices(
            ['USD', 'ZiG'],
            weights=[0.80, 0.20]
        )[0]

        # Pick province
        province_data = random.choices(
            PROVINCES,
            weights=[p[1] for p in PROVINCES]  # weighted by risk score
        )[0]

        # Generate transaction
        tx = {
            'transaction_index': i + 1,
            'transaction_type':  tx_type,
            'network':           network,
            'currency':          currency,
            'amount':            generate_amount(tx_type, is_fraud),
            'timestamp':         generate_timestamp(is_fraud),
            'province':          province_data[0],
            'urban_rural':       province_data[2],
            'channel':           random.choices(
                                     ['USSD', 'app', 'agent'],
                                     weights=[0.55, 0.30, 0.15]
                                 )[0],
            'sender_phone':      generate_phone_number(),
            'receiver_phone':    generate_phone_number(),
            'is_fraud':          is_fraud,
            'fraud_type':        assign_fraud_type(tx_type) if is_fraud else 'none',
            'reference_number':  f"ZFG{2024}{str(i+1).zfill(8)}",
        }
        transactions.append(tx)

        # Progress update every 10,000
        if (i + 1) % 10000 == 0:
            print(f"    {i+1:,} transactions generated...")

    df = pd.DataFrame(transactions)
    print(f"\n Generation complete!")
    print(f"   Total transactions : {len(df):,}")
    print(f"   Fraud transactions : {df['is_fraud'].sum():,}")
    print(f"   Fraud rate         : {df['is_fraud'].mean()*100:.2f}%")
    print(f"\n Fraud by type:")
    print(df[df['is_fraud']==True]['fraud_type'].value_counts())
    print(f"\n Transactions by network:")
    print(df['network'].value_counts())
    return df

if __name__ == "__main__":
    df = generate_transactions(100000)
    # Save to CSV for inspection
    df.to_csv('transactions_raw.csv', index=False)
    print(f"\n Saved to transactions_raw.csv")