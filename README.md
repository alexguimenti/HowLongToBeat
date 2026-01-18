# HowLongToBeat & Genre Enricher

<h1 align="center">
<br>
  <img src="https://cdn6.aptoide.com/imgs/2/f/9/2f90e2d8e2eee0e3acb085b2e1fe6c71_icon.png" alt="HowLongToBeat Data Enricher" width="120">
<br>
<br>
Video Game Data Enricher
</h1>

<p align="center">An advanced Python tool that enriches your game collection CSV with data from <b>HowLongToBeat</b> and classifies genres using <b>OpenAI's GPT-4o-mini</b> with token-saving optimizations.</p>

<hr />

## 🚀 Features

- 🐍 **Python 3.10+** - Built with modern asynchronous logic.
- ⚡ **Asyncio & Concurrency** - High-speed parallel processing using semaphores to respect API limits.
- 🤖 **Smart AI Genre Classification** - Uses OpenAI's `gpt-4o-mini` to classify games into a curated list of 22 genres.
- 💎 **Token Optimization (Cost-Saving)**:
    - **Batching**: Sends up to 20 games in a single LLM prompt, reducing instruction overhead.
    - **Caching**: Local in-memory cache to avoid redundant API calls for duplicate titles across different platforms.
- 🌐 **HowLongToBeat Integration** - Fetches "Main Story" completion times, review scores, and unique HLTB Game IDs.
- 🧹 **Auto-Cleanup**:
    - **Deduplication**: Automatically removes duplicate entries based on Game Name and Platform.
    - **Smart Skipping**: Automatically skips platforms like **Pico 8** for HLTB searches (as they aren't listed there), saving time and API calls.
- 📊 **Cost Tracking** - Detailed report of token usage and estimated USD cost at the end of every run.
- 🛡️ **Data Normalization**:
    - Rounds "Time to Beat" to the nearest **0.25 increment** (e.g., 3.50, 4.25).
    - Selective "Unknown" filling: Only rows being processed are normalized, preserving your original file structure for the rest.

## 🛠️ Getting Started

1. **Install Dependencies**:
    ```bash
    pip install asyncio howlongtobeatpy openai python-dotenv
    ```
2. **Setup API Key**:
   Create a `.env` file in the project root:
    ```env
    OPENAI_API_KEY=your_api_key_here
    ```
3. **Prepare CSV**:
   Ensure you have a `games.csv` file with at least a `Game` and `Platform` column.

## ⚙️ Configuration

The script is highly customizable via the `Config` class in `script.py`:

- `OVERWRITE_INPUT`: Update `games.csv` directly or create a new file.
- `MAX_GAMES_TO_PROCESS`: Limit the number of games per run (perfect for managing API costs).
- `MAX_CONCURRENT_GAMES`: Number of parallel workers (default: 5).
- `SIMILARITY_THRESHOLD`: How strictly to match HLTB names (default: 0.85).
- `GENRE_BATCH_SIZE`: How many games to send to AI at once (default: 20).

## 📖 Usage

1. Place your list in `games.csv`.
2. Run the script:
    ```bash
    python script.py
    ```
3. The script will:
    - Clean duplicate rows.
    - Identify missing data.
    - Process genres in cost-optimized batches.
    - Fetch HLTB data asynchronously.
    - Show an **OpenAI Cost Summary** once finished.

## 📋 CSV Structure

The script works with the following columns:

| Column | Description |
| :--- | :--- |
| **Game** | Title of the game (primary key) |
| **Platform** | Game system (used for AI context) |
| **Year** | Release year |
| **Genre** | Curated genre from AI classification |
| **Game Id** | Official HowLongToBeat ID |
| **Time to Beat** | Completion time (rounded to 0.25) |
| **Score** | Community score (0-100) |
| **Status** | Your personal status (e.g., Backlog, Beaten) |

<hr />

<p align="center"><i>Made with ❤️ by Antigravity</i></p>
