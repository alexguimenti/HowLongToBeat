# HowLongToBeat

<h1 align="center">
<br>
  <img src="https://cdn6.aptoide.com/imgs/2/f/9/2f90e2d8e2eee0e3acb085b2e1fe6c71_icon.png" alt="Game Data Exporter" width="120">
<br>
<br>
HowLongToBeat Data Enricher
</h1>

<p align="center">This script enriches your game collection CSV with data from HowLongToBeat, including completion times and review scores.</p>

<hr />

## Features

- 🐍 **Python** - Core logic
- 🧾 **CSV Read/Write** - Data handling
- ⚙️ **Asyncio** - Efficient API calls
- 🌐 **HowLongToBeat API** - Data source via `howlongtobeatpy`

## Getting Started

1. Ensure you have Python installed on your system.
2. Install the required dependencies using pip:
    ```bash
    pip install asyncio howlongtobeatpy
    ```
3. Prepare a `games.csv` file in the same directory with at least a `Game` column.

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

3. The script will process each game, searching for the best match on HowLongToBeat (requiring >90% similarity).
4. An updated file named `games_updated.csv` will be created with the fetched data.

<hr />

## Important

- The script uses a similarity threshold of 0.90 to ensure data accuracy.
- If a game is not found or has low similarity, it will be skipped.

<hr />

## CSV Structure

The script expects and produces CSV files with the following columns:

- **Game**: The title of the game (used for searching).
- **Platform**: The gaming platform.
- **Year**: Release year (updated by script).
- **Genre**: Game genre.
- **Time to Beat**: Average time to complete the main story (updated by script).
- **Score**: HowLongToBeat review score (updated by script).
- **Status**: Your personal status (e.g., Backlog, Beaten).

You can open the resulting `games_updated.csv` with Excel, Google Sheets, or any text editor.
