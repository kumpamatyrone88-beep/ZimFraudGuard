library(RPostgres)
library(DBI)
library(ggplot2)
library(dplyr)
library(tidyr)
library(scales)

# 1. Connect to PostgreSQL
cat("Connecting to ZimFraudGuard database...\n")

conn <- dbConnect(
  RPostgres::Postgres(),
  dbname   = "ZIMFRAUDGUARD",
  host     = "localhost",
  port     = 5432,
  user     = "postgres",
  password = "YOUR_DATABASE_PASSWORD_HERE" 
)

cat("Connected successfully!\n\n")

# 2. Load Data
cat("Loading transaction data...\n")

query <- "
  SELECT
    t.transaction_id,
    t.amount,
    t.currency,
    t.transaction_type,
    t.channel,
    EXTRACT(HOUR  FROM t.transaction_timestamp) AS hour,
    EXTRACT(DOW   FROM t.transaction_timestamp) AS day_of_week,
    EXTRACT(MONTH FROM t.transaction_timestamp) AS month,
    a.network,
    c.kyc_level,
    c.sim_swap_count,
    l.province,
    l.urban_rural,
    l.risk_score,
    fl.is_fraud,
    fl.fraud_type
  FROM transactions t
  JOIN accounts      a  ON t.sender_account_id = a.account_id
  JOIN customers     c  ON a.customer_id        = c.customer_id
  JOIN locations     l  ON c.location_id        = l.location_id
  JOIN fraud_labels  fl ON t.transaction_id     = fl.transaction_id
"

df <- dbGetQuery(conn, query)
cat(sprintf("Loaded %s transactions\n\n", format(nrow(df), big.mark=",")))

# 3. Fraud Summary Statistics
cat("==================================================\n")
cat("FRAUD SUMMARY STATISTICS\n")
cat("==================================================\n")

fraud_summary <- df %>%
  group_by(is_fraud) %>%
  summarise(
    count      = n(),
    avg_amount = round(mean(amount), 2),
    med_amount = round(median(amount), 2),
    max_amount = round(max(amount), 2),
    .groups    = "drop"
  )
print(fraud_summary)

# 4. Hypothesis Test 1: Means
cat("\n")
cat("==================================================\n")
cat("HYPOTHESIS TEST 1: Fraud vs Legitimate Transaction Amounts\n")
cat("==================================================\n")

fraud_amounts  <- df$amount[df$is_fraud == TRUE]
legit_amounts  <- df$amount[df$is_fraud == FALSE]

t_result <- t.test(fraud_amounts, legit_amounts)
print(t_result)

if (t_result$p.value < 0.05) {
  cat("REJECT H0 — Fraud amounts are significantly different\n")
} else {
  cat("FAIL TO REJECT H0 — No significant difference\n")
}

# 5. Hypothesis Test 2: Distribution
cat("\n")
cat("==================================================\n")
cat("HYPOTHESIS TEST 2: Fraud Rate in Peak vs Normal Hours\n")
cat("==================================================\n")

df$is_peak_hour <- df$hour %in= c(12, 13, 18, 19, 20, 21, 22, 23)

peak_table <- table(df$is_peak_hour, df$is_fraud)
print(peak_table)

chi_result <- chisq.test(peak_table)
print(chi_result)

if (chi_result$p.value < 0.05) {
  cat("REJECT H0 — Fraud significantly higher in peak hours\n")
} else {
  cat("FAIL TO REJECT H0\n")
}

# 6. Fraud Rate by Province
cat("\n")
cat("==================================================\n")
cat("FRAUD RATE BY PROVINCE\n")
cat("==================================================\n")

province_fraud <- df %>%
  group_by(province) %>%
  summarise(
    total_transactions = n(),
    fraud_cases        = sum(is_fraud),
    fraud_rate         = round(mean(is_fraud) * 100, 2),
    avg_fraud_amount   = round(mean(amount[is_fraud == TRUE]), 2),
    .groups            = "drop"
  ) %>%
  arrange(desc(fraud_rate))

print(province_fraud)

# 7. ANOVA
cat("\n")
cat("==================================================\n")
cat("ANOVA: Transaction Amount by Fraud Type\n")
cat("==================================================\n")

fraud_only <- df %>% filter(is_fraud == TRUE)

anova_result <- aov(amount ~ fraud_type, data = fraud_only)
print(summary(anova_result))

if (summary(anova_result)[[1]]$`Pr(>F)`[1] < 0.05) {
  cat("REJECT H0 — Fraud types have significantly different amounts\n")
} else {
  cat("FAIL TO REJECT H0\n")
}

# 8. Fraud by Network
cat("\n")
cat("==================================================\n")
cat("FRAUD RATE BY NETWORK\n")
cat("==================================================\n")

network_fraud <- df %>%
  group_by(network) %>%
  summarise(
    total      = n(),
    fraud      = sum(is_fraud),
    fraud_rate = round(mean(is_fraud) * 100, 2),
    .groups    = "drop"
  ) %>%
  arrange(desc(fraud_rate))

print(network_fraud)

# 9. Visualisations
cat("\n Generating visualisations...\n")

hourly_fraud <- df %>%
  group_by(hour) %>%
  summarise(
    fraud_rate = mean(is_fraud) * 100,
    .groups    = "drop"
  )

p1 <- ggplot(hourly_fraud, aes(x = hour, y = fraud_rate)) +
  geom_col(aes(fill = fraud_rate), show.legend = FALSE) +
  scale_fill_gradient(low = "#2ecc71", high = "#e74c3c") +
  labs(
    title    = "ZimFraudGuard — Fraud Rate by Hour of Day",
    subtitle = "Source: Synthetic data calibrated to RBZ 2024 & POTRAZ Q2 2025",
    x        = "Hour of Day",
    y        = "Fraud Rate (%)"
  ) +
  theme_minimal()

print(p1)

p2 <- ggplot(province_fraud, 
             aes(x = reorder(province, fraud_rate), 
                 y = fraud_rate, fill = fraud_rate)) +
  geom_col(show.legend = FALSE) +
  scale_fill_gradient(low = "#3498db", high = "#e74c3c") +
  coord_flip() +
  labs(
    title    = "ZimFraudGuard — Fraud Rate by Province",
    subtitle = "Source: Synthetic data calibrated to RBZ 2024",
    x        = "Province",
    y        = "Fraud Rate (%)"
  ) +
  theme_minimal()

print(p2)

p3 <- ggplot(df %>% sample_n(5000),
             aes(x = amount, fill = is_fraud)) +
  geom_histogram(bins = 50, alpha = 0.7,
                 position = "identity") +
  scale_fill_manual(values  = c("#2ecc71", "#e74c3c"),
                    labels  = c("Legitimate", "Fraud"),
                    name    = "Transaction Type") +
  scale_x_continuous(limits = c(0, 500)) +
  labs(
    title    = "ZimFraudGuard — Amount Distribution",
    subtitle = "Fraud vs Legitimate Transactions",
    x        = "Amount (USD)",
    y        = "Count"
  ) +
  theme_minimal()

print(p3)

# 10. Close Connection
dbDisconnect(conn)
cat("\n Analysis complete — database connection closed\n")