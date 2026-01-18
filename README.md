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
- 🤖 **OpenAI API** - Automatic genre classification

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
    - Use OpenAI to determine the best-fitting genre from a predefined list.
4. An updated file named `games_updated.csv` will be created with the fetched data.

<hr />

## Important

- **Similarity**: The script uses a similarity threshold of 0.90 for HLTB to ensure data accuracy.
- **API Costs**: Genres are processed via OpenAI. Ensure your API key is valid and has credits.
- **Predefined Genres**: OpenAI is constrained to a specific list of genres (e.g., Action, RPG, Metroidvania, etc.) to keep your database consistent.

<hr />

## CSV Structure

The script expects and produces CSV files with the following columns:

- **Game**: The title of the game (used for searching).
- **Platform**: The gaming platform (helps OpenAI classification).
- **Year**: Release year (updated by HLTB).
- **Genre**: Game genre (updated by OpenAI).
- **Time to Beat**: Average time to complete the main story (updated by HLTB).
- **Score**: HowLongToBeat review score (updated by HLTB).
- **Status**: Your personal status (e.g., Backlog, Beaten).

You can open the resulting `games_updated.csv` with Excel, Google Sheets, or any text editor.
