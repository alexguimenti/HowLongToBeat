# HowLongToBeat Data Enricher

<h1 align="center">
<br>
  <img src="https://cdn6.aptoide.com/imgs/2/f/9/2f90e2d8e2eee0e3acb085b2e1fe6c71_icon.png" alt="HowLongToBeat Data Enricher" width="120">
<br>
<br>
HowLongToBeat Data Enricher
</h1>

<p align="center">An optimized, cost-effective Python tool to enrich your game collection with metadata from HowLongToBeat and automated genre classification using OpenAI's GPT-4o-mini.</p>

<hr />

## 🚀 Key Features

- 🐍 **Modern Python** - Refactored with classes, type hints, and asynchronous logic.
- 💰 **Cost Optimized** - Implements **LLM Batching** (processing 20 games per prompt) and **Local Caching** to reduce OpenAI token usage by up to 90%.
- 📊 **Usage Tracking** - Provides a detailed cost summary in USD and token count at the end of every run.
- ⚙️ **Smart Processing** - 
  - **Selective Enrichment**: Only populates "Unknown" for rows currently being processed, preserving the rest of your CSV.
  - **Pico 8 Logic**: Automatically recognizes Pico 8 games and skips HLTB searches (focusing only on genre classification).
  - **Deduplication**: Automatically removes duplicate entries (same Game + Platform) before processing.
- 🌐 **Robust APIs** - Uses `howlongtobeatpy` for playtimes/scores/IDs and `openai` (gpt-4o-mini) for curated genre classification.
- 🛡️ **Data Normalization** - All "Time to Beat" values are rounded to the nearest **0.25** increment (e.g., 3.50, 4.25).

## 🛠️ Configuration

Customize the script behavior via the `Config` class in `script.py`:

- `MAX_GAMES_TO_PROCESS`: Limit items per run (default: 20).
- `OVERWRITE_INPUT`: Toggle between updating `games.csv` or creating a new file.
- `SIMILARITY_THRESHOLD`: Currently set to `0.85` for better HLTB matching.
- `GENRE_BATCH_SIZE`: Number of games sent to AI in a single batch (default: 20).

## 📦 Getting Started

1. **Install Dependencies**:
    ```bash
    pip install asyncio howlongtobeatpy openai python-dotenv
    ```
2. **Environment Setup**:
   Create a `.env` file with your OpenAI key:
    ```env
    OPENAI_API_KEY=your_api_key_here
    ```
3. **CSV Preparation**:
   Ensure `games.csv` exists with at least these columns: `Game, Platform, Year, Genre, Game Id, Time to Beat, Score, Status`.

## 📖 Usage

1. Run the script:
    ```bash
    python script.py
    ```
2. The script will:
    - Clean up duplicate rows.
    - Fetch genres in efficient batches.
    - Gather HLTB data concurrently.
    - Display a financial and token usage summary.

## 🗂️ CSV Structure

| Column | Description |
| :--- | :--- |
| **Game** | Title of the game (Search key). |
| **Platform** | Gaming system (helps AI classification). |
| **Year** | Release year (from HLTB). |
| **Genre** | Classified from a curated list of 22 genres. |
| **Game Id** | Official HowLongToBeat unique identifier. |
| **Time to Beat** | Main story completion time, rounded to 0.25. |
| **Score** | HLTB community review score (0-100). |
| **Status** | Personal backlog/beaten status. |

<hr />

## ⚖️ Economy & Accuracy

- **Model**: Uses `gpt-4o-mini`, the most cost-efficient model available.
- **Batches**: Instructions are sent once per batch, dramatically reducing overhead tokens.
- **Similarity**: Requires a ≥85% match on HLTB to ensure data quality.
