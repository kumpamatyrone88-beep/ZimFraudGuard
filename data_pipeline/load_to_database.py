import random
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from db_connection import get_connection

random.seed(42)
np.random.seed(42)


def get_accounts(conn):
    cursor = conn.cursor()
    cursor.execute("""
                   SELECT account_id, network, currency
                   FROM accounts
                   WHERE account_status = 'active'
                   """)
    accounts = cursor.fetchall()
    cursor.close()
    return accounts


def get_agents(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT agent_id FROM agents")
    agents = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return agents


def insert_devices(conn):
    print("📱 Inserting devices...")
    cursor = conn.cursor()
    cursor.execute("SELECT customer_id FROM customers")
    customer_ids = [row[0] for row in cursor.fetchall()]

    device_data = []
    for customer_id in customer_ids:
        num_devices = random.randint(1, 2)
        for _ in range(num_devices):
            device_data.append((
                customer_id,
                f"35{random.randint(100000000000000, 999999999999999)}",
                random.choice(['Samsung A15', 'Tecno Spark', 'Infinix Hot',
                               'Samsung A05', 'iPhone 11', 'Huawei Y9']),
                '2023-01-01',
                '2024-12-31',
                False
            ))

    execute_values(cursor, """
                           INSERT INTO devices
                               (customer_id, imei, device_model, first_seen, last_seen, is_flagged)
                           VALUES %s RETURNING device_id
                           """, device_data, page_size=100000)

    device_ids = [row[0] for row in cursor.fetchall()]
    conn.commit()
    cursor.close()
    print(f"   ✅ {len(device_ids):,} devices inserted")
    return device_ids


def insert_transactions_bulk(conn, df):
    print("💸 Inserting 100,000 transactions in bulk...")

    accounts = get_accounts(conn)
    agents = get_agents(conn)
    device_ids = insert_devices(conn)

    accounts_by_network = {}
    for acc in accounts:
        network = acc[1]
        if network not in accounts_by_network:
            accounts_by_network[network] = []
        accounts_by_network[network].append(acc)

    cursor = conn.cursor()
    tx_rows = []

    for _, row in df.iterrows():
        network = row['network']
        available = accounts_by_network.get(network, accounts)
        sender_acc = random.choice(available)
        receiver_acc = random.choice(available)

        while receiver_acc[0] == sender_acc[0] and len(available) > 1:
            receiver_acc = random.choice(available)

        device_id = random.choice(device_ids)
        agent_id = random.choice(agents) if row['channel'] == 'agent' else None

        tx_rows.append((
            sender_acc[0],
            receiver_acc[0],
            device_id,
            agent_id,
            float(row['amount']),
            row['currency'],
            row['transaction_type'],
            row['channel'],
            row['timestamp'],
            row['reference_number'],
            'completed'
        ))

    print("   ⚡ Bulk inserting transactions...")
    execute_values(cursor, """
                           INSERT INTO transactions (sender_account_id, receiver_account_id,
                                                     device_id, agent_id, amount, currency,
                                                     transaction_type, channel,
                                                     transaction_timestamp, reference_number, status)
                           VALUES %s RETURNING transaction_id
                           """, tx_rows, page_size=100000)

    transaction_ids = [row[0] for row in cursor.fetchall()]
    conn.commit()
    print(f"   ✅ {len(transaction_ids):,} transactions inserted")

    print("   ⚡ Bulk inserting fraud labels...")
    label_rows = [
        (
            transaction_ids[i],
            bool(df.iloc[i]['is_fraud']),
            df.iloc[i]['fraud_type'],
            'synthetic'
        )
        for i in range(len(transaction_ids))
    ]

    execute_values(cursor, """
                           INSERT INTO fraud_labels
                               (transaction_id, is_fraud, fraud_type, source)
                           VALUES %s
                           """, label_rows, page_size=100000)

    conn.commit()
    cursor.close()
    print(f"   ✅ {len(label_rows):,} fraud labels inserted")


def main():
    print("🚀 ZimFraudGuard — Bulk Data Loader\n")
    conn = get_connection()
    df = pd.read_csv('transactions_raw.csv')
    insert_transactions_bulk(conn, df)
    conn.close()
    print("\n🏆 ZimFraudGuard database is fully loaded!")


if __name__ == "__main__":
    main()