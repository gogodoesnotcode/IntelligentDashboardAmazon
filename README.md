# Munshot Project

This repository contains the following main modules:

## Modules

### 1. Scraper
Responsible for collecting product and review data from e-commerce sources (e.g., Amazon). The scraper module is implemented in Python and includes the following logic:
- Reads configuration from `config.py`.
- Uses `amazon_scraper.py` to fetch product and review data for various brands.
- Stores the scraped data as CSV files in the `data/raw/` directory, organized by brand and data type (products, reviews).
- Designed for extensibility to support additional e-commerce sources in the future.

### 2. Backend
*Documentation coming soon.*

### 3. Frontend
*Documentation coming soon.*

### 4. Agent
*Documentation coming soon.*

---

## Getting Started

1. Clone the repository.
2. Set up the Python environment for the scraper module.
3. Run the scraper using:
   ```bash
   python scraper/amazon_scraper.py
   ```
4. Data will be saved in the `data/raw/` directory.

Further documentation for backend, frontend, and agent modules will be added soon.
