# HowLongToBeat

<h1 align="center">
<br>
  <img src="https://cdn6.aptoide.com/imgs/2/f/9/2f90e2d8e2eee0e3acb085b2e1fe6c71_icon.png" alt="Game Data Exporter" width="120">
<br>
<br>
HowLongToBeat Data Enricher
</h1>

<p align="center">This script enriches your game collection CSV with data from HowLongToBeat and classifies genres using OpenAI's GPT-4o-mini.</p>

<hr />

## Features

- 🐍 **Python** - Core logic
- 🧾 **CSV Read/Write** - Data handling
- ⚙️ **Asyncio** - Efficient parallel API calls (HLTB + OpenAI)
- 🌐 **HowLongToBeat API** - Fetch completion times and scores
- 🤖 **OpenAI API** - Automatic genre classification based on a curated list
- 🛡️ **Data Validation** - Automatically fills missing information with `"Unknown"`

## Getting Started

1. Ensure you have Python installed on your system.
2. Install the required dependencies using pip:
    ```bash
    pip install asyncio howlongtobeatpy openai python-dotenv
    ```
3. Create a `.env` file in the project root and add your OpenAI API key:
    ```env
    OPENAI_API_KEY=your_api_key_here
    ```
4. Prepare a `games.csv` file in the same directory with at least a `Game` column.

## Usage

1. Place your games list in `games.csv`. The file should follow this structure:
    ```csv
    Game,Platform,Year,Genre,Time to Beat,Score,Status
    ActRaiser,SNES,,,,,Backlog
    ```

2. Run the script:
    ```bash
    python script.py
    ```

3. The script will:
    - Search for the best match on HowLongToBeat (requiring >90% similarity).
    - Use OpenAI to determine the best-fitting genre from a predefined list (Action, RPG, Metroidvania, etc.).
    - Fill any missing fields (Year, Genre, Time, Score, Platform) with `"Unknown"`.
4. An updated file named `games_updated.csv` will be created with the fetched data.

<hr />

## Important

- **Data Integrity**: If a game is not found or the HLTB similarity is low, the script preserves existing data or marks it as `"Unknown"`.
- **OpenAI Constraints**: Genre classification is restricted to a specific list of 22 genres to ensure database consistency.
- **Async Execution**: Both APIs are called simultaneously to significantly reduce processing time.

<hr />

## CSV Structure

The script expects and produces CSV files with the following columns:

- **Game**: The title of the game (primary search key).
- **Platform**: The gaming platform (helps OpenAI classification).
- **Year**: Release year (fetched from HLTB).
- **Genre**: Game genre (classified by OpenAI).
- **Time to Beat**: Average time to complete the main story (fetched from HLTB).
- **Score**: HowLongToBeat community review score (fetched from HLTB).
- **Status**: Your personal status (e.g., Backlog, Beaten).

You can open the resulting `games_updated.csv` with Excel, Google Sheets, or any spreadsheet software.
