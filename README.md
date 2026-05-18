# ZimFraudGuard

An end-to-end mobile money fraud detection pipeline calibrated to the Zimbabwean financial ecosystem. This project integrates automated data ingestion, relational database warehousing, predictive machine learning models, statistical hypothesis testing, and business intelligence.

## 🏗️ System Architecture
* **Data Engineering & Warehousing:** A relational PostgreSQL database architecture storing synthetic transactional streams calibrated to POTRAZ market share metrics. Optimized data ingestion using batch-loading protocols (`psycopg2.extras.execute_values`).
* **Machine Learning Pipelines:** Dual-model fraud prediction engine utilizing Scikit-Learn. Features include custom engineering flags (SIM swap tracking, localized risk scoring, temporal features). Includes a high-volume validation pipeline benchmarked against the 6.3M row global PaySim dataset.
* **Statistical Inference:** Decoupled data pipeline utilizing R for data extraction, descriptive analysis, and significance testing (Two-sample T-Tests, Chi-Square tests, and ANOVA) to validate fraud distribution properties.
* **Business Intelligence:** Interactive Power BI analytical layer tracking historical volume trends, high-risk geographic hotspots, and fraud vector performance.

## 📂 Repository Structure
* `/data_pipeline` - Database schema setup, connection handlers, and bulk loading orchestration utilities.
* `/machine_learning` - Feature engineering pipelines, baseline models, and global dataset validation scripts.
* `/statistical_analysis` - R execution scripts for database connectivity, statistical hypothesis testing, and exploratory visual plots.
* `/dashboard` - Core interactive Power BI template resource mapping system tracking metrics.

## ⚙️ Local Setup Inbound Configuration
1. Clone the repository to your environment.
2. Install dependencies: `pip install -r requirements.txt` (or install pandas, numpy, scikit-learn, psycopg2, sqlalchemy, python-dotenv).
3. Create a local `.env` file based on the keys outlined in `.env.example` and supply your database credentials.
4. Execute the pipeline scripts within `/data_pipeline` to load data, then run scripts in `/machine_learning` and `/statistical_analysis` for modeling and reporting.