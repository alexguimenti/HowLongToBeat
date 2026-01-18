import asyncio
import csv
import os
from dotenv import load_dotenv
from howlongtobeatpy import HowLongToBeat
from openai import AsyncOpenAI

# Load environment variables
load_dotenv()

# Configuration
OVERWRITE_INPUT = True  # Set to True to update the input file directly
INPUT_CSV = "games.csv"
OUTPUT_CSV = INPUT_CSV if OVERWRITE_INPUT else "games_updated.csv"
MAX_GAMES_TO_PROCESS = 10  # Limit the number of games to update per run. Set to None for no limit.

# Initialize API clients
hltb = HowLongToBeat()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Limit the number of concurrent games being processed
# 5 is a safe number to avoid rate limits and keep logs readable
MAX_CONCURRENT_GAMES = 5
semaphore = asyncio.Semaphore(MAX_CONCURRENT_GAMES)

async def get_genre(game_name, platform):
    """Fetches the game genre using OpenAI API."""
    try:
        completion = await client.chat.completions.create(
            model="o4-mini",
            messages=[
                {"role": "system", "content": '''
You are a video game database expert. Your sole purpose is to classify video games into specific genres.

When the user provides a "Game Title - Platform", you must output ONLY the genre name from the following allowed list:
- Action
- Action Adventure
- Action Platformer
- Action RPG
- Adventure
- Beat 'em up
- Fighting
- Metroidvania
- Mini-game
- Pinball
- Platformer
- Puzzle
- Puzzle Platformer
- Racing
- RPG
- Run and Gun
- Shoot 'em up
- Shooter
- Sports
- Strategy
- Survival Horror
- Visual Novel

Constraints:
1. NO conversational filler (e.g., do not say "The genre is..." or "Sure!").
2. NO punctuation at the end of the response.
3. If a game fits multiple categories, choose the most defining one.
4. Output must be in English.
                '''},
                {"role": "user", "content": f"{game_name} - {platform}"}
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"\nError fetching genre for {game_name}: {e}")
        return "Unknown"

async def process_single_game(game, index, total_games):
    """Processes a single game instance with concurrency control."""
    async with semaphore:
        # Initialize default values if empty or normalize existing
        for field in ["Year", "Genre", "Time to Beat", "Score", "Platform"]:
            val = str(game.get(field, "")).strip()
            if not val or val in ["", "Unknown", "None"]:
                game[field] = "Unknown"
            elif field == "Time to Beat":
                try:
                    # Normalize existing numeric times to nearest 0.25
                    time_val = float(val)
                    rounded_time = round(time_val * 4) / 4
                    game[field] = f"{rounded_time:.2f}"
                except ValueError:
                    pass

        game_name = game["Game"]
        platform = game["Platform"]
        
        # Determine if we actually need to fetch data from APIs
        needs_hltb = any(game[f] == "Unknown" for f in ["Year", "Time to Beat", "Score"])
        needs_genre = game["Genre"] == "Unknown"

        if not needs_hltb and not needs_genre:
            return # Already fully processed (including normalization)

        # Parallelize HLTB and OpenAI calls for this specific game
        hltb_task = hltb.async_search(game_name) if needs_hltb else asyncio.sleep(0, None)
        genre_task = get_genre(game_name, platform) if needs_genre else asyncio.sleep(0, game["Genre"])
        
        try:
            results_list, genre = await asyncio.gather(hltb_task, genre_task)
            
            if needs_genre:
                game["Genre"] = genre if genre else "Unknown"

            if needs_hltb:
                if results_list and len(results_list) > 0:
                    best_element = max(results_list, key=lambda element: element.similarity)
                    if best_element.similarity > 0.90:
                        game["Score"] = str(best_element.review_score) if best_element.review_score else "Unknown"
                        game["Year"] = str(best_element.release_world) if best_element.release_world else "Unknown"
                        
                        # Round fetched Time to Beat to the nearest 0.25
                        if best_element.main_story:
                            try:
                                time_val = float(best_element.main_story)
                                rounded_time = round(time_val * 4) / 4
                                game["Time to Beat"] = f"{rounded_time:.2f}"
                            except ValueError:
                                game["Time to Beat"] = "Unknown"
                        else:
                            game["Time to Beat"] = "Unknown"
                            
                        print(f"[{index}/{total_games}] {game_name}: Updated! (Sim: {best_element.similarity:.2f} | Genre: {game['Genre']})")
                    else:
                        print(f"[{index}/{total_games}] {game_name}: Skipped HLTB (Low Sim: {best_element.similarity:.2f} | Genre: {game['Genre']})")
                else:
                    print(f"[{index}/{total_games}] {game_name}: HLTB Not found (Genre: {game['Genre']})")
            else:
                print(f"[{index}/{total_games}] {game_name}: Genre updated to {game['Genre']} (HLTB already present)")

        except Exception as e:
            print(f"[{index}/{total_games}] Error processing {game_name}: {e}")

async def process_games(input_file, output_file):
    # 1. Read the CSV file
    all_games = []
    try:
        with open(input_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            all_games = list(reader)
    except FileNotFoundError:
        print(f"Error: The file '{input_file}' was not found.")
        return

    # 2. Filter games that need processing (have at least one missing/Unknown field)
    games_to_process = []
    for game in all_games:
        # Check if any important field is missing or marked as Unknown/empty
        is_missing_data = any(
            not game.get(f) or game[f].strip() in ["", "Unknown", "None"] 
            for f in ["Year", "Genre", "Time to Beat", "Score"]
        )
        if is_missing_data:
            games_to_process.append(game)

    # 3. Apply the limit
    if MAX_GAMES_TO_PROCESS is not None:
        games_to_process = games_to_process[:MAX_GAMES_TO_PROCESS]

    total_to_process = len(games_to_process)
    if total_to_process == 0:
        print("No games need processing (all fields are already filled).")
        return

    print(f"Found {len(all_games)} total games. Processing {total_to_process} games with missing data...")

    # 4. Create tasks for the filtered games
    tasks = [process_single_game(game, i, total_to_process) for i, game in enumerate(games_to_process, start=1)]
    
    # 5. Run all tasks concurrently
    await asyncio.gather(*tasks)

    # 6. Save results (all_games contains both the updated and the skipped ones)
    fieldnames = ["Game", "Platform", "Year", "Genre", "Time to Beat", "Score", "Status"]
    try:
        with open(output_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_games)
        print(f"\nSuccess! File '{output_file}' created/updated.")
    except IOError:
        print("\nError: Could not save the CSV file.")

if __name__ == "__main__":
    asyncio.run(process_games(INPUT_CSV, OUTPUT_CSV))
