# HowLongToBeat

<h1 align="center">
<br>
  <img src="https://cdn6.aptoide.com/imgs/2/f/9/2f90e2d8e2eee0e3acb085b2e1fe6c71_icon.png" alt="Game Data Exporter" width="120">
<br>
<br>
HowLongToBeat
</h1>

<p align="center">This script allows the user to export game data to a CSV file.</p>

<hr />

## Features

Applied Technologies

- 🐍 **Python**
- 🧾 **CSV**
- ⚙️ **Asyncio**
- 🌐 **HowLongToBeat API**

## Getting Started

1. Ensure you have Python installed on your system.
2. Install the required dependencies using pip:
    ```bash
    pip install asyncio csv howlongtobeatpy
    ```
3. Insert your list of games into the `games_data` variable in the script.

## Example Usage

1. Open the script file and insert your list of games in the `games_data` variable. Here is an example:

    ```python
    games_data = {
        "Games": [
            {
                "Game Title": "Daze Before Christmas",
                "Platform": "SNES",
                "Year": 1994,
                "Genre": "Platform"
            },
            {
                "Game Title": "Alisia Dragoon",
                "Platform": "Mega Drive",
                "Year": 1992,
                "Genre": "Action"
            },
            # Add more games as needed
        ]
    }
    ```

2. Run the script:
    ```bash
    python game_data_exporter.py
    ```

3. The script will process the games and create a CSV file named `games_data.csv` with the additional game information.

<hr />

## Important

Make sure the `games_data` variable is correctly formatted as shown in the example.

<hr />

## Example CSV File

After running the script, you will get a CSV file with the following columns:

- Game Title
- Platform
- Year
- Genre
- Game ID
- Main Story

You can open this CSV file with any spreadsheet software like Excel.
